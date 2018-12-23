#  Copyright 2013-2018 The Salish Sea MEOPAR contributors
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
"""SalishSeaCast worker that processes VFPA HADCP observations from the 2nd Narrows Rail Bridge
for a specified UTC day from CSV files into a monthly netCDF file.

The observations are stored as a collection of netCDF-4/HDF5 files that is accessible via
https://salishsea.eos.ubc.ca/erddap/info/ubcVFPA2ndNarrowsCurrent2sV1/index.html.

Development notebook:
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/analysis-doug/raw/default/notebooks/2ndNarrowsHADPCtoERDDAP.ipynb
"""
import logging
import os

import numpy
import pandas
from pathlib import Path

import arrow
import xarray
from moad_tools.places import PLACES
from nemo_nowcast import NowcastWorker

NAME = "get_vfpa_hadcp"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.get_vfpa_hadcp --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_date_option(
        "--data-date",
        default=arrow.now().floor("day"),
        help="UTC date to get VFPA HADPC data for.",
    )
    worker.run(get_vfpa_hadcp, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f'VFPA HADCP observations added to {parsed_args.data_date.format("YYYY-MM")} netcdf file'
    )
    return "success"


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f'Addition of VFPA HADCP observations to {parsed_args.data_date.format("YYYY-MM")} '
        f"netcdf file failed"
    )
    return "failure"


def get_vfpa_hadcp(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    data_date = parsed_args.data_date
    place = PLACES["2nd Narrows Rail Bridge"]
    logger.info(
        f"processing VFPA HADCP data from 2nd Narrows Rail Bridge for "
        f"{data_date.format('YYYY-MM-DD')}"
    )
    csv_dir = Path(config["observations"]["hadcp data"]["csv dir"])
    dest_dir = Path(config["observations"]["hadcp data"]["dest dir"])
    filepath_tmpl = config["observations"]["hadcp data"]["filepath template"]
    nc_filepath = dest_dir / filepath_tmpl.format(
        yyyymm=parsed_args.data_date.format("YYYYMM")
    )
    # Process 1st hour to create new month netcdf file, or extend existing one
    try:
        ds = _make_hour_dataset(csv_dir, data_date, place)
        if not nc_filepath.exists():
            action = "created"
            _write_netcdf(ds, nc_filepath)
            logger.info(f"created {nc_filepath}")
        else:
            action = "extended"
            with xarray.open_dataset(nc_filepath) as stored_ds:
                extended_ds = xarray.concat((stored_ds, ds), dim="time")
            _write_netcdf(extended_ds, nc_filepath)
            logger.debug(
                f"extended {nc_filepath} with {data_date.format('YYYY-MM-DD HH:mm')} hour"
            )
    except ValueError:
        # Skip missing hour
        action = "missing data"
        logger.debug(f"no data for {data_date.format('YYYY-MM-DD HH:mm')} hour")
        pass
    # Process remaining day hours to extend netcdf file
    end_hr = (
        data_date.shift(days=+1)
        if data_date.shift(days=+1) < arrow.utcnow()
        else arrow.utcnow().floor("hour")
    )
    hr_range = arrow.Arrow.range(
        "hour", start=data_date.shift(hours=+1), end=end_hr.shift(hours=-1)
    )
    for hr in hr_range:
        try:
            with xarray.open_dataset(nc_filepath) as stored_ds:
                ds = _make_hour_dataset(csv_dir, hr, place)
                extended_ds = xarray.concat((stored_ds, ds), dim="time")
        except (ValueError, FileNotFoundError):
            # Skip missing hour
            logger.debug(f"no data for {hr.format('YYYY-MM-DD HH:mm')} hour")
            continue
        _write_netcdf(extended_ds, nc_filepath)
        logger.debug(
            f"extended {nc_filepath} with {hr.format('YYYY-MM-DD HH:mm')} hour"
        )
    checklist = {
        action: os.fspath(nc_filepath),
        "UTC date": data_date.format("YYYY-MM-DD"),
    }
    logger.info(
        f"added VFPA HADCP data from 2nd Narrows Rail Bridge for "
        f"{data_date.format('YYYY-MM-DD')} to {nc_filepath}"
    )
    return checklist


def _make_hour_dataset(csv_dir, utc_start_hr, place):
    """
    :param :py:class:`pathlib.Path` csv_dir:
    :param :py.class:`arrow.Arrow` utc_start_hr:
    :param dict place:

    :rtype: :py.class:`xarray.Dataset`
    """
    csv_datetime_fmt = "YYYYMMDDTHHmmss"
    utc_offset = utc_start_hr.to("local").utcoffset()
    csv_filename = (
        f"{utc_start_hr.format(csv_datetime_fmt)}Z-"
        f"{utc_start_hr.shift(hours=+1).format(csv_datetime_fmt)}Z.csv"
    )
    ds = _csv_to_dataset(csv_dir / csv_filename, place)
    logger.debug("transformed csv data into xarray.Dataset")
    ds["time"] -= pandas.to_timedelta(utc_offset)
    ds["time"].attrs["cf_role"] = "timeseries_id"
    ds["time"].attrs["comment"] = "time values are UTC"
    ds.coords["longitude"], ds.coords["latitude"] = place["lon lat"]
    var_attrs = {
        "speed": {
            "name": "speed",
            "units": "m/s",
            "ioos_category": "currents",
            "standard_name": "sea_water_speed",
            "long_name": "Current Speed",
        },
        "direction": {
            "name": "direction",
            "units": "degree",
            "ioos_category": "currents",
            "standard_name": "direction_of_sea_water_velocity",
            "long_name": "Current To Direction",
        },
        "longitude": {
            "name": "longitude",
            "units": "degrees_east",
            "ioos_category": "location",
            "standard_name": "longitude",
            "long_name": "Longitude",
        },
        "latitude": {
            "name": "latitude",
            "units": "degrees_north",
            "ioos_category": "location",
            "standard_name": "latitude",
            "long_name": "Latitude",
        },
    }
    for var in var_attrs:
        ds[var].attrs = var_attrs[var]
    ds.attrs = {
        "cdm_data_type": "TimeSeries",
        "cdm_timeseries_variables": "speed, direction",
        "institution": "UCB EOAS & DFO IOS",
        "institution_fullname": (
            "Earth, Ocean & Atmospheric Sciences, University of British Columbia, "
            "Fisheries and Oceans Canada, Institute of Ocean Sciences"
        ),
        "license": (
            "The Salish Sea MEOPAR observation datasets are copyright 2013-2018 by the "
            "Salish Sea MEOPAR Project Contributors, The University of British Columbia, "
            "and the Vancouver Fraser Port Authority. "
            "They are licensed under the Apache License, Version 2.0. "
            "https://www.apache.org/licenses/LICENSE-2.0. "
            "Raw instrument data on which this dataset is based were provided by "
            "Vancouver Fraser Port Authority."
        ),
        "title": "VFPA, Vancouver Harbour, 2nd Narrows Rail Bridge, Current, 2sec, v1",
        "summary": (
            "VFPA, Vancouver Harbour, 2nd Narrows Rail Bridge, Current, 2sec, v1 "
            "Current data from Vancouver Fraser Port Authority (VFPA) horizontal "
            "acoustic doppler current profiler (HADCP) instrument located at the 2nd "
            "Narrows Rail Bridge. The time values are UTC. "
            "v1: current speed and direction variables"
        ),
        "source": "Hourly AIS email feed created by DFO IOS.",
    }
    return ds


def _csv_to_dataset(csv_file, place):
    """
    :param :py:class:`pathlib.Path` csv_file:
    :param dict place:

    :rtype: :py.class:`xarray.Dataset`
    """
    try:
        df = pandas.read_csv(csv_file, skiprows=3)
        logger.debug(f"read {csv_file}")
    except FileNotFoundError:
        logger.warning(f"file not found: {csv_file}")
        raise
    df = df.loc[df.MMSI == place["stn number"]].drop_duplicates().set_index("Time")
    df = df.dropna(axis="columns", how="all")
    for col in ["Name", "MMSI", "Air Temp.", "Water Temp.", "Water Level"]:
        try:
            df = df.drop([col], axis="columns")
        except KeyError:
            pass
    df.index = pandas.to_datetime(df.index, format="%d/%m/%Y %H:%M")
    df.index.name = "time"
    df.columns = ("speed", "direction")
    return xarray.Dataset.from_dataframe(df)


def _write_netcdf(ds, nc_filepath):
    """
    :param :py.class:`xarray.Dataset` ds:
    :param :py:class:`pathlib.Path` nc_filepath:
    """
    encoding = {
        "speed": {"dtype": "int16", "scale_factor": 0.1, "_FillValue": -9999},
        "direction": {"dtype": "int16", "scale_factor": 0.1, "_FillValue": -9999},
        "time": {"dtype": "float", "units": "seconds since 1970-01-01T00:00:00Z"},
    }
    # Drop repeated times because some csv files contain hh:00 to hh+1:00
    # instead of ending at hh:58
    _, index = numpy.unique(ds.time.values, return_index=True)
    ds = ds.isel(time=index)
    ds.to_netcdf(nc_filepath, mode="w", encoding=encoding, unlimited_dims=("time",))


if __name__ == "__main__":
    main()  # pragma: no cover
