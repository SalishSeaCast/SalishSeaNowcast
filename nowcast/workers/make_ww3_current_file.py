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

# SPDX-License-Identifier: Apache-2.0


"""Salish Sea WaveWatch3 forecast worker that produces the hourly
ocean currents forcing file for a prelim-forecast or forecast run
"""
import logging
import os
import shlex
import subprocess
from pathlib import Path

import arrow
import xarray
from nemo_nowcast import NowcastWorker
from salishsea_tools import viz_tools

NAME = "make_ww3_current_file"
logger = logging.getLogger(NAME)


def main():
    """For command-line usage see:

    :command:`python -m nowcast.workers.make_ww3_current_file --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "host_name", help="Name of the host to create the currents file on"
    )
    worker.cli.add_argument(
        "run_type",
        choices={"forecast2", "forecast", "nowcast"},
        help="""
        Type of run to create the currents file for:
        'forecast2' means preliminary forecast run (after NEMO forecast2 run),
        'forecast' means updated forecast run (after NEMO forecast run),
        'nowcast' means updated 1 day only (for hindcast runs)
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Start date of run to create the currents file for.",
    )
    worker.run(make_ww3_current_file, success, failure)


def success(parsed_args):
    logger.info(
        f"wwatch3 currents forcing file created "
        f"on {parsed_args.host_name} "
        f'for {parsed_args.run_date.format("YYYY-MM-DD")} '
        f"{parsed_args.run_type} run"
    )
    msg_type = f"success {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    logger.critical(
        f"wwatch3 currents forcing file creation failed "
        f"on {parsed_args.host_name} "
        f'for {parsed_args.run_date.format("YYYY-MM-DD")} '
        f"{parsed_args.run_type} run"
    )
    msg_type = f"failure {parsed_args.run_type}"
    return msg_type


def make_ww3_current_file(parsed_args, config, *args):
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    ymd = run_date.format("YYYY-MM-DD")
    logger.info(f"Creating wwatch3 currents forcing file for {ymd} {run_type} run")
    host_config = config["run"]["enabled hosts"][host_name]
    grid_dir = Path(config["wave forecasts"]["grid dir"])
    mesh_mask = os.fspath(grid_dir / config["run types"]["nowcast"]["mesh mask"])
    nemo_dir = Path(host_config["run types"]["nowcast"]["results"]).parent
    nemo_file_tmpl = config["wave forecasts"]["NEMO file template"]
    dest_dir = Path(config["wave forecasts"]["run prep dir"], "current")
    filepath_tmpl = config["wave forecasts"]["current file template"]
    nc_filepath = dest_dir / filepath_tmpl.format(yyyymmdd=run_date.format("YYYYMMDD"))
    if run_type in {"nowcast", "forecast"}:
        datasets = _calc_nowcast_datasets(run_date, nemo_dir, nemo_file_tmpl)
    if run_type == "forecast":
        datasets.update(_calc_forecast_datasets(run_date, nemo_dir, nemo_file_tmpl))
    if run_type == "forecast2":
        datasets = _calc_forecast2_datasets(
            run_date, nemo_dir, nemo_file_tmpl, dest_dir
        )
    drop_vars = {
         'gphiu', 'vmask', 'gdept_0', 'gdepw_0', 'umask', 'gphif', 'e3v_0', 'time_counter',
         'isfdraft', 'glamu', 'e1f', 'vmaskutil', 'mbathy', 'e2t', 'e2u', 'e3u_0', 'ff', 'gdept_1d',
         'gphit', 'e3w_0', 'e1u', 'e1t', 'e2v', 'fmaskutil', 'tmaskutil', 'gdepv', 'misf', 'gphiv',
         'e3t_1d', 'fmask', 'tmask', 'e3t_0', 'gdepw_1d', 'gdepu', 'glamt', 'glamf',
         'e3w_1d', 'e1v', 'umaskutil', 'glamv', 'e2f',
    }
    with xarray.open_dataset(mesh_mask, drop_variables=drop_vars, engine="h5netcdf") as grid:
        lats = grid.nav_lat[1:, 1:]
        lons = grid.nav_lon[1:, 1:] + 360
        logger.debug(f"lats and lons from: {mesh_mask}")
    drop_vars = {
        "area",
        "bounds_lon",
        "bounds_lat",
        "bounds_nav_lon",
        "bounds_nav_lat",
        "depthu_bounds",
        "depthv_bounds",
        "time_centered",
        "time_centered_bounds",
        "time_counter_bounds",
    }
    chunks = {
        "u": {
            "time_counter": 1,
            "depthu": 40,
            "y": 898,
            "x": 398,
        },
        "v": {
            "time_counter": 1,
            "depthv": 40,
            "y": 898,
            "x": 398,
        },
    }
    with xarray.open_mfdataset(
        datasets["u"],
        chunks=chunks["u"],
        compat="override",
        coords="minimal",
        data_vars="minimal",
        drop_variables=drop_vars,
        engine="h5netcdf",
    ) as u_nemo:
        logger.debug(f'u velocities from {datasets["u"]}')
        with xarray.open_mfdataset(
            datasets["v"],
            chunks=chunks["v"],
            compat="override",
            coords="minimal",
            data_vars="minimal",
            drop_variables=drop_vars,
            engine="h5netcdf",
        ) as v_nemo:
            logger.debug(f'v velocities from {datasets["v"]}')
            u_unstaggered, v_unstaggered = viz_tools.unstagger(
                u_nemo.vozocrtx.isel(depthu=0), v_nemo.vomecrty.isel(depthv=0)
            )
            del u_unstaggered.coords["depthu"]
            del v_unstaggered.coords["depthv"]
            logger.debug("unstaggered velocity components on to mesh mask lats/lons")
            u_current, v_current = viz_tools.rotate_vel(u_unstaggered, v_unstaggered)
            logger.debug("rotated velocity components north/south alignment")
            ds = _create_dataset(
                u_current.time_counter, lats, lons, u_current, v_current, datasets
            )
            logger.debug("created currents dataset")
            dask_scheduler = {
                "scheduler": "processes",
                "max_workers": 8,
            }
            ds.compute(**dask_scheduler)
            ds.to_netcdf(nc_filepath, engine="netcdf4")
    logger.debug(f"stored currents forcing file: {nc_filepath}")
    checklist = {
        run_type: os.fspath(nc_filepath),
        "run date": run_date.format("YYYY-MM-DD"),
    }
    return checklist


def _calc_nowcast_datasets(run_date, nemo_dir, nemo_file_tmpl):
    datasets = {"u": [], "v": []}
    dmy = run_date.format("DDMMMYY").lower()
    s_yyyymmdd = e_yyyymmdd = run_date.format("YYYYMMDD")
    for grid in datasets:
        nowcast_file = (
            nemo_dir
            / Path("nowcast", dmy)
            / nemo_file_tmpl.format(
                s_yyyymmdd=s_yyyymmdd, e_yyyymmdd=e_yyyymmdd, grid=grid.upper()
            )
        )
        datasets[grid].append(nowcast_file)
        logger.debug(f"{grid} dataset: {nowcast_file}")
    return datasets


def _calc_forecast_datasets(run_date, nemo_dir, nemo_file_tmpl):
    datasets = {"u": [], "v": []}
    dmy = run_date.format("DDMMMYY").lower()
    s_yyyymmdd = e_yyyymmdd = run_date.format("YYYYMMDD")
    for grid in datasets:
        nowcast_file = (
            nemo_dir
            / Path("nowcast", dmy)
            / nemo_file_tmpl.format(
                s_yyyymmdd=s_yyyymmdd, e_yyyymmdd=e_yyyymmdd, grid=grid.upper()
            )
        )
        datasets[grid].append(nowcast_file)
        logger.debug(f"{grid} dataset: {nowcast_file}")
    s_yyyymmdd = run_date.shift(days=+1).format("YYYYMMDD")
    e_yyyymmdd = run_date.shift(days=+2).format("YYYYMMDD")
    for grid in datasets:
        forecast_file = (
            nemo_dir
            / Path("forecast", dmy)
            / nemo_file_tmpl.format(
                s_yyyymmdd=s_yyyymmdd, e_yyyymmdd=e_yyyymmdd, grid=grid.upper()
            )
        )
        datasets[grid].append(forecast_file)
        logger.debug(f"{grid} dataset: {forecast_file}")
    return datasets


def _calc_forecast2_datasets(run_date, nemo_dir, nemo_file_tmpl, dest_dir):
    datasets = {"u": [], "v": []}
    dmy = run_date.shift(days=-1).format("DDMMMYY").lower()
    s_yyyymmdd = run_date.format("YYYYMMDD")
    e_yyyymmdd = run_date.shift(days=+1).format("YYYYMMDD")
    for grid in datasets:
        forecast_file = (
            nemo_dir
            / Path("forecast", dmy)
            / nemo_file_tmpl.format(
                s_yyyymmdd=s_yyyymmdd, e_yyyymmdd=e_yyyymmdd, grid=grid.upper()
            )
        )
        forecast_file_24h = dest_dir / nemo_file_tmpl.format(
            s_yyyymmdd=s_yyyymmdd, e_yyyymmdd=s_yyyymmdd, grid=grid.upper()
        )
        cmd = (
            f"/usr/bin/ncks -d time_counter,0,23 "
            f"{forecast_file} {forecast_file_24h}"
        )
        logger.debug(f"running {cmd} in subprocess")
        subprocess.run(shlex.split(cmd))
        logger.debug(f"extracted 1st 24h of {forecast_file} to {forecast_file_24h}")
        datasets[grid].append(forecast_file_24h)
        logger.debug(f"{grid} dataset: {forecast_file_24h}")
    s_yyyymmdd = run_date.shift(days=+1).format("YYYYMMDD")
    e_yyyymmdd = run_date.shift(days=+2).format("YYYYMMDD")
    for grid in datasets:
        forecast2_file = (
            nemo_dir
            / Path("forecast2", dmy)
            / nemo_file_tmpl.format(
                s_yyyymmdd=s_yyyymmdd, e_yyyymmdd=e_yyyymmdd, grid=grid.upper()
            )
        )
        datasets[grid].append(forecast2_file)
        logger.debug(f"{grid} dataset: {forecast2_file}")
    return datasets


def _create_dataset(time, lats, lons, u_current, v_current, datasets):
    now = arrow.now()
    ds = xarray.Dataset(
        data_vars={
            "u_current": u_current.rename({"time_counter": "time"}),
            "v_current": v_current.rename({"time_counter": "time"}),
        },
        coords={
            "time": time.rename("time").rename({"time_counter": "time"}),
            "latitude": lats,
            "longitude": lons,
        },
        attrs={
            "creation_date": str(now),
            "history": f'[{now.format("YYYY-MM-DD HH:mm:ss")}] '
            f"created by SalishSeaNowcast "
            f"make_ww3_current_file worker",
            "source": f"UBC SalishSeaCast NEMO results datasets: {datasets}",
        },
    )
    return ds


if __name__ == "__main__":
    main()
