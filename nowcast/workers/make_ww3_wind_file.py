#  Copyright 2013 – present by the SalishSeaCast Project contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Salish Sea WaveWatch3 forecast worker that produces the hourly wind forcing
file for a prelim-forecast or forecast run
"""
import logging
import os
from pathlib import Path

import arrow
import xarray
from nemo_nowcast import NowcastWorker

NAME = "make_ww3_wind_file"
logger = logging.getLogger(NAME)


def main():
    """For command-line usage see:

    :command:`python -m nowcast.workers.make_ww3_wind_file --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "host_name", help="Name of the host to create the wind file on"
    )
    worker.cli.add_argument(
        "run_type",
        choices={"forecast2", "forecast", "nowcast"},
        help="""
        Type of run to create wind file for:
        'forecast2' means preliminary forecast run (after NEMO forecast2 run),
        'forecast' means updated forecast run (after NEMO forecast run),
        'nowcast' means updated 1 day only (for hindcast runs)
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Start date of run to create the wind file for.",
    )
    worker.run(make_ww3_wind_file, success, failure)
    return worker


def success(parsed_args):
    logger.info(
        f"wwatch3 wind forcing file created "
        f"on {parsed_args.host_name} "
        f'for {parsed_args.run_date.format("YYYY-MM-DD")} '
        f"{parsed_args.run_type} run"
    )
    msg_type = f"success {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    logger.critical(
        f"wwatch3 wind forcing file creation failed "
        f"on {parsed_args.host_name} "
        f'for {parsed_args.run_date.format("YYYY-MM-DD")} '
        f"{parsed_args.run_type} run"
    )
    msg_type = f"failure {parsed_args.run_type}"
    return msg_type


def make_ww3_wind_file(parsed_args, config, *args):
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    ymd = run_date.format("YYYY-MM-DD")
    logger.info(f"Creating wwatch3 wind forcing file for {ymd} {run_type} run")
    host_config = config["run"]["enabled hosts"][host_name]
    hrdps_dir = Path(host_config["forcing"]["weather dir"])
    hrdps_file_tmpl = config["weather"]["file template"]
    datasets = []
    if run_type in {"nowcast", "forecast"}:
        hrdps_file = hrdps_dir / hrdps_file_tmpl.format(run_date.datetime)
        datasets.append(hrdps_file)
        logger.debug(f"dataset: {hrdps_file}")
    if run_type == "forecast":
        day_range = arrow.Arrow.range(
            "day", run_date.shift(days=+1), run_date.shift(days=+2)
        )
        for day in day_range:
            hrdps_file = (hrdps_dir / "fcst") / hrdps_file_tmpl.format(day.datetime)
            datasets.append(hrdps_file)
            logger.debug(f"dataset: {hrdps_file}")
    if run_type == "forecast2":
        day_range = arrow.Arrow.range("day", run_date, run_date.shift(days=+2))
        for day in day_range:
            hrdps_file = (hrdps_dir / "fcst") / hrdps_file_tmpl.format(day.datetime)
            datasets.append(hrdps_file)
            logger.debug(f"dataset: {hrdps_file}")
    dest_dir = Path(config["wave forecasts"]["run prep dir"], "wind")
    filepath_tmpl = config["wave forecasts"]["wind file template"]
    nc_filepath = dest_dir / filepath_tmpl.format(yyyymmdd=run_date.format("YYYYMMDD"))
    drop_vars = {
        "LHTFL_surface",
        "PRATE_surface",
        "RH_2maboveground",
        "atmpres",
        "precip",
        "qair",
        "solar",
        "tair",
        "therm_rad",
        "u_wind",
        "v_wind",
    }
    with xarray.open_dataset(
        datasets[0], drop_variables=drop_vars, engine="h5netcdf"
    ) as lats_lons:
        lats = lats_lons.nav_lat
        lons = lats_lons.nav_lon
        logger.debug(f"lats and lons from: {datasets[0]}")
    drop_vars = drop_vars.union(
        {
            "nav_lon",
            "nav_lat",
        }
    )
    drop_vars = drop_vars.difference({"u_wind", "v_wind"})
    chunks = {
        "time_counter": 24,
        "y": 230,
        "x": 190,
    }
    with xarray.open_mfdataset(
        datasets,
        chunks=chunks,
        compat="override",
        coords="minimal",
        data_vars="minimal",
        drop_variables=drop_vars,
        engine="h5netcdf",
    ) as hrdps:
        ds = _create_dataset(
            hrdps.time_counter, lats, lons, hrdps.u_wind, hrdps.v_wind, datasets
        )
        logger.debug("created winds dataset")
        dask_scheduler = {
            "scheduler": "processes",
            "max_workers": 8,
        }
        ds.compute(**dask_scheduler)
        # write using netcdf4 because wwatch3 doesn't like files generated by h5netcdf
        ds.to_netcdf(nc_filepath, engine="netcdf4")
    logger.debug(f"stored wind forcing file: {nc_filepath}")
    checklist = {run_type: os.fspath(nc_filepath)}
    return checklist


def _create_dataset(time, lats, lons, u_wind, v_wind, datasets):
    now = arrow.now()
    ds = xarray.Dataset(
        data_vars={
            "u_wind": u_wind.rename({"time_counter": "time"}),
            "v_wind": v_wind.rename({"time_counter": "time"}),
        },
        coords={
            "time": time.rename("time").rename({"time_counter": "time"}),
            "latitude": lats,
            "longitude": lons,
        },
        attrs={
            "creation_date": str(now),
            "history": f'[{now.format("YYYY-MM-DD HH:mm:ss")}] '
            f"created by SalishSeaNowcast make_ww3_wind_file worker",
            "source": f"ECCC HRDPS via UBC SalishSeaCast NEMO forcing datasets: "
            f"{[os.fspath(dataset) for dataset in datasets]}",
        },
    )
    try:
        # Datasets from pre-23feb23 HRDPS west atmospheric forcing files
        # have wind component coordinates attributes that we don't need,
        # so delete them
        del ds.u_wind.attrs["coordinates"]
        del ds.v_wind.attrs["coordinates"]
    except KeyError:
        # Datasets from 23feb23 onward HRDPS continental atmospheric forcing files
        # don't have wind component coordinates attributes, and that's okay
        pass
    return ds


if __name__ == "__main__":
    main()  # pragma: no cover
