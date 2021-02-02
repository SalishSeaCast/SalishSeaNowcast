#  Copyright 2013-2021 The Salish Sea MEOPAR contributors
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
"""Salish Sea nowcast worker that downloads CTD temperature and salinity data
for a specified UTC day from an ONC Strait of Georgia node.

The data are filtered to include only values for which qaqcFlag == 1
(meaning that all of ONC's automated QA/QC tests were passed).
After filtering the data are aggregated into 15 minute bins.
The aggregation functions are mean, standard deviation, and sample count.

The data are stored as a netCDF-4/HDF5 file that is accessible via
https://salishsea.eos.ubc.ca/erddap/tabledap/index.html?page=1&itemsPerPage=1000.

Development notebook:
https://nbviewer.jupyter.org/github/SalishSeaCast/analysis-doug/blob/master/notebooks/ONC-CTD-DataToERDDAP.ipynb
"""
import logging
import os
from pathlib import Path

import arrow
import numpy
import xarray
from nemo_nowcast import NowcastWorker, WorkerError
from salishsea_tools import data_tools
from salishsea_tools.places import PLACES

NAME = "get_onc_ctd"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.get_onc_ctd -h`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "onc_station",
        choices={"SCVIP", "SEVIP", "USDDL"},
        help="Name of the ONC node station to download data for.",
    )
    worker.cli.add_date_option(
        "--data-date",
        default=arrow.utcnow().floor("day").shift(days=-1),
        help="UTC date to get ONC node CTD data for.",
    )
    worker.run(get_onc_ctd, success, failure)


def success(parsed_args):
    ymd = parsed_args.data_date.format("YYYY-MM-DD")
    logger.info(f"{ymd} ONC {parsed_args.onc_station} CTD T&S file created")
    msg_type = f"success {parsed_args.onc_station}"
    return msg_type


def failure(parsed_args):
    ymd = parsed_args.data_date.format("YYYY-MM-DD")
    logger.critical(f"{ymd} ONC {parsed_args.onc_station} CTD T&S file creation failed")
    msg_type = "failure"
    return msg_type


def get_onc_ctd(parsed_args, config, *args):
    ymd = parsed_args.data_date.format("YYYY-MM-DD")
    logger.info(f"requesting ONC {parsed_args.onc_station} CTD T&S data for {ymd}")
    TOKEN = os.environ["ONC_USER_TOKEN"]
    onc_data = data_tools.get_onc_data(
        "scalardata",
        "getByStation",
        TOKEN,
        station=parsed_args.onc_station,
        deviceCategory="CTD",
        sensors="salinity,temperature",
        dateFrom=data_tools.onc_datetime(f"{ymd} 00:00", "utc"),
    )
    try:
        ctd_data = data_tools.onc_json_to_dataset(onc_data)
    except TypeError:
        logger.error(f"No ONC {parsed_args.onc_station} CTD T&S data for {ymd}")
        raise WorkerError
    logger.debug(
        f"ONC {parsed_args.onc_station} CTD T&S data for {ymd} received and parsed"
    )
    logger.debug(
        f"filtering ONC {parsed_args.onc_station} temperature data for {ymd} "
        f"to exlude qaqcFlag!=1"
    )
    temperature = _qaqc_filter(ctd_data, "temperature")
    logger.debug(
        f"filtering ONC {parsed_args.onc_station} salinity data for {ymd} "
        f"to exlude qaqcFlag!=1"
    )
    salinity = _qaqc_filter(ctd_data, "salinity")
    logger.debug(f"creating ONC {parsed_args.onc_station} CTD T&S dataset for {ymd}")
    ds = _create_dataset(parsed_args.onc_station, temperature, salinity)
    dest_dir = Path(config["observations"]["ctd data"]["dest dir"])
    filepath_tmpl = config["observations"]["ctd data"]["filepath template"]
    nc_filepath = dest_dir / filepath_tmpl.format(
        station=parsed_args.onc_station,
        yyyymmdd=parsed_args.data_date.format("YYYYMMDD"),
    )
    logger.debug(
        f"storing ONC {parsed_args.onc_station} CTD T&S dataset "
        f"for {ymd} as {nc_filepath}"
    )
    encoding = {
        var: {"dtype": "int64", "_FillValue": 0}
        for var in ds.data_vars
        if var.endswith("sample_count")
    }
    encoding["time"] = {"units": "minutes since 1970-01-01 00:00"}
    ds.to_netcdf(os.fspath(nc_filepath), encoding=encoding, unlimited_dims=("time",))
    checklist = {parsed_args.onc_station: os.fspath(nc_filepath)}
    return checklist


def _qaqc_filter(ctd_data, var):
    qaqc_mask = ctd_data.data_vars[var].attrs["qaqcFlag"] == 1
    filtered_var = xarray.DataArray(
        name=var,
        data=ctd_data.data_vars[var][qaqc_mask].values,
        coords={"time": ctd_data.data_vars[var].sampleTime[qaqc_mask].values},
        dims="time",
    )
    return filtered_var


def _create_dataset(onc_station, temperature, salinity):
    def count(values, axis):
        return values.size

    metadata = {
        "SCVIP": {
            "place_name": "Central node",
            "ONC_station": "Central",
            "ONC_stationDescription": "Pacific, Salish Sea, Strait of Georgia, Central, "
            "Strait of Georgia VENUS Instrument Platform",
        },
        "SEVIP": {
            "place_name": "East node",
            "ONC_station": "East",
            "ONC_stationDescription": "Pacific, Salish Sea, Strait of Georgia, East, "
            "Strait of Georgia VENUS Instrument Platform",
        },
        "USDDL": {
            "place_name": "Delta DDL node",
            "ONC_station": "Delta Upper Slope DDL",
            "ONC_stationDescription": "Pacific, Salish Sea, Strait of Georgia, Delta, Upper Slope, "
            "Delta Dynamics Laboratory",
        },
    }
    try:
        temperature_mean = temperature.resample(time="15Min").mean()
        temperature_std_dev = temperature.resample(time="15Min").std()
        temperature_sample_count = temperature.resample(time="15Min").count()
    except IndexError:
        # If the temperature data is messing no dataset can be created
        raise WorkerError(f"no {onc_station} temperate data; no dataset created")
    try:
        salinity_mean = salinity.resample(time="15Min").mean()
        salinity_std_dev = salinity.resample(time="15Min").std()
        salinity_sample_count = salinity.resample(time="15Min").count()
    except IndexError:
        logger.warning(f"no {onc_station} salinity data")
        salinity_mean = temperature_mean.copy()
        salinity_mean.name = "salinity"
        salinity_mean.data = numpy.full_like(temperature_mean, numpy.nan)
        salinity_std_dev = temperature_std_dev.copy()
        salinity_std_dev.name = "salinity_std_dev"
        salinity_std_dev.data = numpy.full_like(temperature_std_dev, numpy.nan)
        salinity_sample_count = temperature_sample_count.copy()
        salinity_sample_count.name = "salinity_sample_count"
        salinity_sample_count.data = numpy.zeros_like(temperature_sample_count)
    ds = xarray.Dataset(
        data_vars={
            "temperature": xarray.DataArray(
                name="temperature",
                data=temperature_mean,
                attrs={
                    "ioos_category": "Temperature",
                    "standard_name": "sea_water_temperature",
                    "long_name": "temperature",
                    "units": "degrees_Celcius",
                    "aggregation_operation": "mean",
                    "aggregation_interval": 15 * 60,
                    "aggregation_interval_units": "seconds",
                },
            ),
            "temperature_std_dev": xarray.DataArray(
                name="temperature_std_dev",
                data=temperature_std_dev,
                attrs={
                    "ioos_category": "Temperature",
                    "standard_name": "sea_water_temperature_standard_deviation",
                    "long_name": "temperature standard deviation",
                    "units": "degrees_Celcius",
                    "aggregation_operation": "standard deviation",
                    "aggregation_interval": 15 * 60,
                    "aggregation_interval_units": "seconds",
                },
            ),
            "temperature_sample_count": xarray.DataArray(
                name="temperature_sample_count",
                data=temperature_sample_count,
                attrs={
                    "standard_name": "sea_water_temperature_sample_count",
                    "long_name": "temperature sample count",
                    "aggregation_operation": "count",
                    "aggregation_interval": 15 * 60,
                    "aggregation_interval_units": "seconds",
                },
            ),
            "salinity": xarray.DataArray(
                name="salinity",
                data=salinity_mean,
                attrs={
                    "ioos_category": "Salinity",
                    "standard_name": "sea_water_reference_salinity",
                    "long_name": "reference salinity",
                    "units": "g/kg",
                    "aggregation_operation": "mean",
                    "aggregation_interval": 15 * 60,
                    "aggregation_interval_units": "seconds",
                },
            ),
            "salinity_std_dev": xarray.DataArray(
                name="salinity_std_dev",
                data=salinity_std_dev,
                attrs={
                    "ioos_category": "Salinity",
                    "standard_name": "sea_water_reference_salinity_standard_deviation",
                    "long_name": "reference salinity standard deviation",
                    "units": "g/kg",
                    "aggregation_operation": "standard deviation",
                    "aggregation_interval": 15 * 60,
                    "aggregation_interval_units": "seconds",
                },
            ),
            "salinity_sample_count": xarray.DataArray(
                name="salinity_sample_count",
                data=salinity_sample_count,
                attrs={
                    "standard_name": "sea_water_reference_salinity_sample_count",
                    "long_name": "reference salinity sample count",
                    "aggregation_operation": "count",
                    "aggregation_interval": 15 * 60,
                    "aggregation_interval_units": "seconds",
                },
            ),
        },
        coords={
            "depth": PLACES[metadata[onc_station]["place_name"]]["depth"],
            "longitude": PLACES[metadata[onc_station]["place_name"]]["lon lat"][0],
            "latitude": PLACES[metadata[onc_station]["place_name"]]["lon lat"][1],
        },
        attrs={
            "history": f"""
    [arrow.now().format('YYYY-MM-DD HH:mm:ss')] Download raw data from ONC
    scalardata API.
    [arrow.now().format('YYYY-MM-DD HH:mm:ss')] Filter to exclude data with
    qaqcFlag != 1.
    [arrow.now().format('YYYY-MM-DD HH:mm:ss')] Resample data to 15 minute
    intervals using mean, standard deviation and count as aggregation functions.
    [arrow.now().format('YYYY-MM-DD HH:mm:ss')] Store as netCDF4 file.
            """,
            "ONC_station": metadata[onc_station]["ONC_station"],
            "ONC_stationCode": onc_station,
            "ONC_stationDescription": metadata[onc_station]["ONC_stationDescription"],
            "ONC_data_product_url": f"http://dmas.uvic.ca/DataSearch?location={onc_station}"
            f"&deviceCategory=CTD",
        },
    )
    return ds


if __name__ == "__main__":
    main()  # pragma: no cover
