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
"""SalishSeaCast worker that downloads data for a specified UTC day from an ONC BC Ferries
measurement platform.

The data are filtered to include only values for which qaqcFlag == 1
(meaning that all of ONC's automated QA/QC tests were passed).
After filtering the data are aggregated into 1 minute bins.
The aggregation functions are mean, standard deviation, and sample count.

The data are stored as a netCDF-4/HDF5 file that is accessible via
https://salishsea.eos.ubc.ca/erddap/tabledap/index.html?page=1&itemsPerPage=1000.

Development notebook:
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/analysis-doug/raw/tip/notebooks/ONC-Ferry-DataToERDDAP.ipynb
"""
import logging
import os
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

import arrow
import numpy
import requests
import xarray
from nemo_nowcast import NowcastWorker, WorkerError
from salishsea_tools import data_tools
from salishsea_tools.places import PLACES

NAME = "get_onc_ferry"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.get_onc_ferry -h`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "ferry_platform",
        choices={"TWDP"},
        help="Name of the ONC ferry platform to download data for.",
    )
    worker.cli.add_date_option(
        "--data-date",
        default=arrow.now().floor("day").shift(days=-1),
        help="UTC date to get ONC ferry data for.",
    )
    worker.run(get_onc_ferry, success, failure)
    return worker


def success(parsed_args):
    ymd = parsed_args.data_date.format("YYYY-MM-DD")
    logger.info(f"{ymd} ONC {parsed_args.ferry_platform} ferry data file created")
    msg_type = f"success {parsed_args.ferry_platform}"
    return msg_type


def failure(parsed_args):
    ymd = parsed_args.data_date.format("YYYY-MM-DD")
    logger.critical(
        f"{ymd} ONC {parsed_args.ferry_platform} ferry data file creation failed"
    )
    msg_type = f"failure {parsed_args.ferry_platform}"
    return msg_type


def get_onc_ferry(parsed_args, config, *args):
    ymd = parsed_args.data_date.format("YYYY-MM-DD")
    ferry_platform = parsed_args.ferry_platform
    ferry_config = config["observations"]["ferry data"]["ferries"][ferry_platform]
    location_config = ferry_config["location"]
    devices_config = ferry_config["devices"]
    data_arrays = SimpleNamespace()
    try:
        nav_data = _get_nav_data(ferry_platform, ymd, location_config)
    except TypeError:
        logger.error(f"No nav data for {ferry_platform} so no dataset for {ymd}")
        raise WorkerError
    (
        data_arrays.longitude,
        data_arrays.latitude,
        data_arrays.on_crossing_mask,
        data_arrays.crossing_number,
    ) = _calc_location_arrays(nav_data, location_config)
    for device in devices_config:
        device_data = _get_water_data(ferry_platform, device, ymd, devices_config)
        sensor_data_arrays = _qaqc_filter(
            ferry_platform, device, device_data, ymd, devices_config
        )
        for i, sensor in enumerate(devices_config[device]["sensors"]):
            setattr(data_arrays, sensor, sensor_data_arrays[i])
    dataset = _create_dataset(
        data_arrays, ferry_platform, ferry_config, location_config, ymd
    )
    dest_dir = Path(config["observations"]["ferry data"]["dest dir"])
    filepath_tmpl = ferry_config["filepath template"]
    nc_filepath = dest_dir / filepath_tmpl.format(
        ferry_platform=ferry_platform, yyyymmdd=parsed_args.data_date.format("YYYYMMDD")
    )
    logger.debug(f"storing ONC {ferry_platform} dataset for {ymd} as {nc_filepath}")
    encoding = {
        var: {"dtype": "int32", "_FillValue": 0}
        for var in dataset.data_vars
        if var.endswith("sample_count")
    }
    encoding["time"] = {"units": "minutes since 1970-01-01 00:00"}
    dataset.to_netcdf(
        os.fspath(nc_filepath), encoding=encoding, unlimited_dims=("time",)
    )
    checklist = {ferry_platform: os.fspath(nc_filepath)}


def _get_nav_data(ferry_platform, ymd, location_config):
    for station in location_config["stations"]:
        device_category = location_config["device category"]
        sensors = ",".join(location_config["sensors"])
        logger.info(f"requesting ONC {station} {device_category} data for {ymd}")
        try:
            onc_data = data_tools.get_onc_data(
                "scalardata",
                "getByStation",
                os.environ["ONC_USER_TOKEN"],
                station=station,
                deviceCategory=device_category,
                sensors=sensors,
                dateFrom=(data_tools.onc_datetime(f"{ymd} 00:00", "utc")),
            )
        except requests.HTTPError as e:
            msg = (
                f"request for ONC {station} {device_category} data for {ymd} "
                f"failed: {e}"
            )
            logger.error(msg)
            raise WorkerError(msg)
        try:
            nav_data = data_tools.onc_json_to_dataset(onc_data)
            logger.debug(
                f"ONC {station} {device_category} data for {ymd} received and parsed"
            )
            return nav_data
        except TypeError:
            # Invalid data from NAV device, so try the next one
            continue
    msg = (
        f"no valid nav data found from ONC ferry nav station devices "
        f'{location_config["stations"]} for {ymd} '
    )
    logger.error(msg)
    raise WorkerError(msg)


def _calc_location_arrays(nav_data, location_config):
    lons = (nav_data.longitude.resample(sampleTime="1Min").mean()).rename(
        {"sampleTime": "time"}
    )
    lons.attrs["units"] = "degree_east"
    lons.attrs["station"] = nav_data.attrs["station"]
    lats = (nav_data.latitude.resample(sampleTime="1Min").mean()).rename(
        {"sampleTime": "time"}
    )
    lats.attrs["units"] = "degree_north"
    lats.attrs["station"] = nav_data.attrs["station"]
    terminals = [
        SimpleNamespace(
            lon=PLACES[terminal]["lon lat"][0],
            lat=PLACES[terminal]["lon lat"][1],
            radius=PLACES[terminal]["in berth radius"],
        )
        for terminal in location_config["terminals"]
    ]
    on_crossing_mask = _on_crossing(lons, lats, terminals)
    crossing_numbers = _calc_crossing_numbers(on_crossing_mask)
    return lons, lats, on_crossing_mask, crossing_numbers


def _on_crossing(lons, lats, terminals):
    in_berth = numpy.logical_or(
        numpy.logical_and(
            numpy.logical_and(
                lons > (terminals[0].lon - terminals[0].radius),
                lons < (terminals[0].lon + terminals[0].radius),
            ),
            numpy.logical_and(
                lats > (terminals[0].lat - terminals[0].radius),
                lats < (terminals[0].lat + terminals[0].radius),
            ),
        ),
        numpy.logical_and(
            numpy.logical_and(
                lons > (terminals[1].lon - terminals[1].radius),
                lons < (terminals[1].lon + terminals[1].radius),
            ),
            numpy.logical_and(
                lats > (terminals[1].lat - terminals[1].radius),
                lats < (terminals[1].lat + terminals[1].radius),
            ),
        ),
    )
    return numpy.logical_not(in_berth)


def _calc_crossing_numbers(on_crossing_mask):
    crossing_numbers = numpy.empty_like(on_crossing_mask, dtype=float)
    crossing_number = 0
    crossing_numbers[0] = 0 if on_crossing_mask[0] else numpy.nan
    for minute in range(1, crossing_numbers.size):
        if not on_crossing_mask[minute - 1] and on_crossing_mask[minute]:
            crossing_number += 1
        if on_crossing_mask[minute]:
            crossing_numbers[minute] = crossing_number
        else:
            crossing_numbers[minute] = numpy.nan
    return xarray.DataArray(
        name="crossing_number",
        data=crossing_numbers,
        coords={"time": on_crossing_mask.time.values},
        dims="time",
    )


def _get_water_data(ferry_platform, device_category, ymd, devices_config):
    sensors = ",".join(devices_config[device_category]["sensors"].values())
    logger.info(f"requesting ONC {ferry_platform} {device_category} data for {ymd}")
    try:
        onc_data = data_tools.get_onc_data(
            "scalardata",
            "getByStation",
            os.environ["ONC_USER_TOKEN"],
            station=ferry_platform,
            deviceCategory=device_category,
            sensors=sensors,
            dateFrom=(data_tools.onc_datetime(f"{ymd} 00:00", "utc")),
        )
    except requests.HTTPError as e:
        if e.response.status_code == 504:
            return _empty_device_data(ferry_platform, device_category, ymd, sensors)
        else:
            logger.error(
                f"request for ONC {ferry_platform} {device_category} data "
                f"for {ymd} failed: {e}"
            )
            raise WorkerError
    try:
        device_data = data_tools.onc_json_to_dataset(onc_data)
    except TypeError:
        return _empty_device_data(ferry_platform, device_category, ymd, sensors)
    logger.debug(
        f"ONC {ferry_platform} {device_category} data for {ymd} received and parsed"
    )
    return device_data


def _empty_device_data(ferry_platform, device_category, ymd, sensors):
    # Response from ONC contains no sensor data, so return an
    # empty DataArray
    logger.warning(
        f"No ONC {ferry_platform} {device_category} data for {ymd}; "
        f"substituting empty dataset"
    )
    onc_units = {
        "temperature": "C",
        "conductivity": "S/m",
        "salinity": "g/kg",
        "oxygen_saturation": "percent",
        "oxygen_corrected": "ml/l",
        "cdom_fluorescence": "ppb",
        "chlorophyll": "ug/l",
        "turbidity": "NTU",
        "partial_pressure": "pCO2 uatm",
        "co2": "umol/mol",
        "air_temperature": "C",
        "REL_HUMIDITY": "%",
        "barometric_pressure": "hPa",
        "solar_radiation": "W/m^2",
        "downward_radiation": "W/m^2",
    }
    data_arrays = {
        sensor: xarray.DataArray(
            name=sensor,
            data=numpy.array([], dtype=float),
            coords={"sampleTime": numpy.array([], dtype="datetime64[ns]")},
            dims="sampleTime",
            attrs={
                "qaqcFlag": numpy.array([], dtype=numpy.int64),
                "unitOfMeasure": onc_units[sensor],
            },
        )
        for sensor in sensors.split(",")
    }
    return xarray.Dataset(data_arrays)


def _qaqc_filter(ferry_platform, device, device_data, ymd, devices_config):
    cf_units_mapping = {"C": "degrees_Celcius"}
    sensor_data_arrays = []
    for sensor, onc_sensor in devices_config[device]["sensors"].items():
        logger.debug(
            f"filtering ONC {ferry_platform} {device} {onc_sensor} data "
            f"for {ymd} to exlude qaqcFlag!=1"
        )
        onc_data = getattr(device_data, onc_sensor)
        not_nan_mask = numpy.logical_not(numpy.isnan(onc_data.values))
        sensor_qaqc_mask = onc_data.attrs["qaqcFlag"] <= 1
        try:
            cf_units = cf_units_mapping[onc_data.unitOfMeasure]
        except KeyError:
            cf_units = onc_data.unitOfMeasure
        sensor_data_arrays.append(
            xarray.DataArray(
                name=sensor,
                data=onc_data[not_nan_mask][sensor_qaqc_mask].values,
                coords={
                    "time": onc_data.sampleTime[not_nan_mask][sensor_qaqc_mask].values
                },
                dims="time",
                attrs={"device_category": device, "units": cf_units},
            )
        )
    return sensor_data_arrays


def _create_dataset(data_arrays, ferry_platform, ferry_config, location_config, ymd):
    location_vars = {"longitude", "latitude", "on_crossing_mask", "crossing_number"}

    def count(values, axis):
        return 0 if numpy.all(numpy.isnan(values)) else int(values.size)

    data_vars = {}
    for var, array in data_arrays.__dict__.items():
        if var in location_vars:
            data_vars[var] = _create_dataarray(
                var, array, ferry_platform, location_config
            )
        else:
            try:
                data_array = array.resample(time="1Min").mean()
            except IndexError:
                # array is empty, meaning there are no observations with
                # qaqcFlag!=1, so substitute a DataArray full of NaNs
                logger.warning(
                    f"ONC {ferry_platform} {array.device_category} "
                    f"{array.name} data for {ymd} contains no qaqcFlag==1 "
                    f"values; substituting NaNs"
                )
                nan_values = numpy.empty_like(data_vars["longitude"].values)
                nan_values[:] = numpy.nan
                array = xarray.DataArray(
                    name=array.name,
                    data=nan_values,
                    coords={"time": data_vars["longitude"].time},
                    dims="time",
                    attrs=array.attrs,
                )
                data_array = array.resample(time="1Min").mean()
            data_array.attrs = array.attrs
            data_vars[var] = _create_dataarray(
                var, data_array, ferry_platform, location_config
            )
            std_dev_var = f"{var}_std_dev"
            std_dev_array = array.resample(time="1Min").std()
            std_dev_array.attrs = array.attrs
            data_vars[std_dev_var] = _create_dataarray(
                std_dev_var, std_dev_array, ferry_platform, location_config
            )
            sample_count_var = f"{var}_sample_count"
            sample_count_array = array.resample(time="1Min").count()
            sample_count_array.attrs = array.attrs
            del sample_count_array.attrs["units"]
            data_vars[sample_count_var] = _create_dataarray(
                sample_count_var, sample_count_array, ferry_platform, location_config
            )
    now = arrow.now().format("YYYY-MM-DD HH:mm:ss")
    dataset = xarray.Dataset(
        data_vars=data_vars,
        coords={"time": data_arrays.longitude.time.values},
        attrs={
            "history": f"""{now} Download raw data from ONC scalardata API.
{now} Filter to exclude data with qaqcFlag != 1.
{now} Resample data to 1 minute intervals using mean, standard deviation and
count as aggregation functions.
{now} Store as netCDF4 file.
""",
            "ferry_route_name": ferry_config["route name"],
            "ONC_stationDescription": ferry_config["ONC station description"],
        },
    )
    return dataset


def _create_dataarray(var, array, ferry_platform, location_config):
    metadata = {
        "longitude": {
            "name": "longitude",
            "ioos category": "location",
            "standard name": "longitude",
            "long name": "Longitude",
            "ONC_data_product_url": f"http://dmas.uvic.ca/DataSearch"
            f'?deviceCategory={location_config["device category"]}',
        },
        "latitude": {
            "name": "latitude",
            "ioos category": "location",
            "standard name": "latitude",
            "long name": "Latitude",
            "ONC_data_product_url": f"http://dmas.uvic.ca/DataSearch"
            f'?deviceCategory={location_config["device category"]}',
        },
        "on_crossing_mask": {
            "name": "on_crossing_mask",
            "ioos category": "identifier",
            "standard name": "on_crossing_mask",
            "long name": "On Crossing",
            "flag_values": "0, 1",
            "flag_meanings": "in berth, on crossing",
            "ONC_data_product_url": f"http://dmas.uvic.ca/DataSearch?location={ferry_platform}",
        },
        "crossing_number": {
            "name": "crossing_number",
            "ioos category": "identifier",
            "standard name": "crossing_number",
            "long name": "Crossing Number",
            "flag_values": "0.0, 1.0, 2.0, ...",
            "flag_meanings": "UTC day crossing number",
            "comment": "The first and last crossings of a UTC day are typically "
            "incomplete because the ferry operates in the Pacific "
            "time zone. "
            "To obtain a complete dataset for the 1st crossing of the "
            "UTC day, "
            "concatenate the crossing_number==0 observations to the "
            "crossing_number==n observation from the previous day, "
            "where n is max(crossing_number). "
            "The number of crossings per day varies throughout the year.",
            "ONC_data_product_url": f"http://dmas.uvic.ca/DataSearch?location={ferry_platform}",
        },
        "temperature": {
            "name": "temperature",
            "ioos category": "temperature",
            "standard name": "sea_water_temperature",
            "long name": "temperature",
        },
        "temperature_std_dev": {
            "name": "temperature_std_dev",
            "ioos category": "temperature",
            "standard name": "sea_water_temperature_standard_deviation",
            "long name": "temperature standard deviation",
        },
        "temperature_sample_count": {
            "name": "temperature_sample_count",
            "ioos category": "temperature",
            "standard name": "sea_water_temperature_sample_count",
            "long name": "temperature sample count",
        },
        "conductivity": {
            "name": "conductivity",
            "ioos category": "salinity",
            "standard name": "sea_water_electical_conductivity",
            "long name": "conductivity",
        },
        "conductivity_std_dev": {
            "name": "conductivity_std_dev",
            "ioos category": "salinity",
            "standard name": "sea_water_electical_conductivity_standard_deviation",
            "long name": "conductivity standard deviation",
        },
        "conductivity_sample_count": {
            "name": "conductivity_sample_count",
            "ioos category": "salinity",
            "standard name": "sea_water_electical_conductivity_sample_count",
            "long name": "conductivity sample count",
        },
        "salinity": {
            "name": "salinity",
            "ioos category": "salinity",
            "standard name": "sea_water_reference_salinity",
            "long name": "reference salinity",
        },
        "salinity_std_dev": {
            "name": "salinity_std_dev",
            "ioos category": "salinity",
            "standard name": "sea_water_reference_salinity_standard_deviation",
            "long name": "reference salinity standard deviation",
        },
        "salinity_sample_count": {
            "name": "salinity_sample_count",
            "ioos category": "salinity",
            "standard name": "sea_water_reference_salinity_sample_count",
            "long name": "reference salinity sample count",
        },
        "o2_saturation": {
            "name": "o2_saturation",
            "ioos category": "dissolved_o2",
            "standard name": "percent_saturation_of_oxygen_in_sea_water",
            "long name": "O2 saturation",
        },
        "o2_saturation_std_dev": {
            "name": "o2_saturation_std_dev",
            "ioos category": "dissolved_o2",
            "standard name": "percent_saturation_of_oxygen_in_sea_water_standard_deviation",
            "long name": "O2 saturation standard deviation",
        },
        "o2_saturation_sample_count": {
            "name": "o2_saturation_sample_count",
            "ioos category": "dissolved_o2",
            "standard name": "percent_saturation_of_oxygen_in_sea_water_sample_count",
            "long name": "O2 saturation sample count",
        },
        "o2_concentration_corrected": {
            "name": "o2_concentration_corrected",
            "ioos category": "dissolved_o2",
            "standard name": "volume_fraction_of_oxygen_in_sea_water",
            "long name": "corrected O2 concentration",
        },
        "o2_concentration_corrected_std_dev": {
            "name": "o2_concentration_corrected_std_dev",
            "ioos category": "dissolved_o2",
            "standard name": "volume_fraction_of_oxygen_in_sea_water_standard_deviation",
            "long name": "corrected O2 concentration standard deviation",
        },
        "o2_concentration_corrected_sample_count": {
            "name": "o2_concentration_corrected_sample_count",
            "ioos category": "dissolved_o2",
            "standard name": "volume_fraction_of_oxygen_in_sea_water_sample_count",
            "long name": "corrected O2 concentration sample count",
        },
        "o2_temperature": {
            "name": "o2_temperature",
            "ioos category": "dissolved_o2",
            "standard name": "temperature_of_sensor_for_oxygen_in_sea_water",
            "long name": "O2 sensor temperature",
        },
        "o2_temperature_std_dev": {
            "name": "o2_temperature_std_dev",
            "ioos category": "dissolved_o2",
            "standard name": "temperature_of_sensor_for_oxygen_in_sea_water_standard_deviation",
            "long name": "O2 sensor temperature standard deviation",
        },
        "o2_temperature_sample_count": {
            "name": "o2_temperature_sample_count",
            "ioos category": "dissolved_o2",
            "standard name": "temperature_of_sensor_for_oxygen_in_sea_water_sample_count",
            "long name": "O2 sensor temperature sample count",
        },
        "cdom_fluorescence": {
            "name": "cdom_fluorescence",
            "ioos category": "optical properties",
            "standard name": "mass_fraction_of_cdom_fluorescence_in_sea_water",
            "long name": "CDOM fluorescence mass fraction",
        },
        "cdom_fluorescence_std_dev": {
            "name": "cdom_fluorescence_std_dev",
            "ioos category": "optical properties",
            "standard name": "mass_fraction_of_cdom_fluorescence_in_sea_water_standard_deviation",
            "long name": "CDOM fluorescence standard deviation",
        },
        "cdom_fluorescence_sample_count": {
            "name": "cdom_fluorescence_sample_count",
            "ioos category": "optical properties",
            "standard name": "mass_fraction_of_cdom_fluorescence_in_sea_water_sample_count",
            "long name": "CDOM fluorescence sample count",
        },
        "chlorophyll": {
            "name": "chlorophyll",
            "ioos category": "optical properties",
            "standard name": "mass_fraction_of_chlorophyll_in_sea_water",
            "long name": "chlorophyll concentration",
        },
        "chlorophyll_std_dev": {
            "name": "chlorophyll_std_dev",
            "ioos category": "optical properties",
            "standard name": "mass_fraction_of_chlorophyll_in_sea_water_standard_deviation",
            "long name": "chlorophyll concentration standard deviation",
        },
        "chlorophyll_sample_count": {
            "name": "chlorophyll_sample_count",
            "ioos category": "optical properties",
            "standard name": "mass_fraction_of_chlorophyll_in_sea_water_sample_count",
            "long name": "chlorophyll concentration sample count",
        },
        "turbidity": {
            "name": "turbidity",
            "ioos category": "optical properties",
            "standard name": "sea_water_turbidity",
            "long name": "turbidity ",
        },
        "turbidity_std_dev": {
            "name": "turbidity_std_dev",
            "ioos category": "optical properties",
            "standard name": "sea_water_turbidity_standard_deviation",
            "long name": "turbidity standard deviation",
        },
        "turbidity_sample_count": {
            "name": "turbidity_sample_count",
            "ioos category": "optical properties",
            "standard name": "sea_water_turbidity_sample_count",
            "long name": "turbidity sample count",
        },
        "co2_partial_pressure": {
            "name": "co2_partial_pressure",
            "ioos category": "CO2",
            "standard name": "surface_partial_pressure_of_carbon_dioxide_in_sea_water",
            "long name": "CO2 partial pressure ",
        },
        "co2_partial_pressure_std_dev": {
            "name": "co2_partial_pressure_std_dev",
            "ioos category": "CO2",
            "standard name": "surface_partial_pressure_of_carbon_dioxide_in_sea_water_standard_deviation",
            "long name": "CO2 partial pressure standard deviation",
        },
        "co2_partial_pressure_sample_count": {
            "name": "co2_partial_pressure_sample_count",
            "ioos category": "CO2",
            "standard name": "surface_partial_pressure_of_carbon_dioxide_in_sea_water_sample_count",
            "long name": "CO2 partial pressure sample count",
        },
        "co2_concentration_linearized": {
            "name": "co2_concentration_linearized",
            "ioos category": "CO2",
            "standard name": "mole_fraction_of_carbon_dioxide_in_sea_water",
            "long name": "CO2 partial pressure ",
        },
        "co2_concentration_linearized_std_dev": {
            "name": "co2_concentration_linearized_std_dev",
            "ioos category": "CO2",
            "standard name": "mole_fraction_of_carbon_dioxide_in_sea_water_standard_deviation",
            "long name": "CO2 partial pressure standard deviation",
        },
        "co2_concentration_linearized_sample_count": {
            "name": "co2_concentration_linearized_sample_count",
            "ioos category": "CO2",
            "standard name": "mole_fraction_of_carbon_dioxide_in_sea_water_sample_count",
            "long name": "CO2 partial pressure sample count",
        },
        "air_temperature": {
            "name": "air_temperature",
            "ioos category": "meteorology",
            "standard name": "air_temperature",
            "long name": "air temperature",
        },
        "air_temperature_std_dev": {
            "name": "air_temperature_std_dev",
            "ioos category": "meteorology",
            "standard name": "air_temperature_standard_deviations",
            "long name": "air temperature standard deviation",
        },
        "air_temperature_sample_count": {
            "name": "air_temperature_sample_count",
            "ioos category": "meteorology",
            "standard name": "air_temperature_sample_count",
            "long name": "air temperature sample count",
        },
        "relative_humidity": {
            "name": "relative_humidity",
            "ioos category": "meteorology",
            "standard name": "relative_humidity",
            "long name": "relative humidity",
        },
        "relative_humidity_std_dev": {
            "name": "relative_humidity_std_dev",
            "ioos category": "meteorology",
            "standard name": "relative_humidity_standard_deviation",
            "long name": "relative humidity standard deviation",
        },
        "relative_humidity_sample_count": {
            "name": "relative_humidity_sample_count",
            "ioos category": "meteorology",
            "standard name": "relative_humidity_sample_count",
            "long name": "relative humidity sample count",
        },
        "barometric_pressure": {
            "name": "barometric_pressure",
            "ioos category": "pressure",
            "standard name": "surface_air_pressure",
            "long name": "barometric pressure",
        },
        "barometric_pressure_std_dev": {
            "name": "barometric_pressure_std_dev",
            "ioos category": "pressure",
            "standard name": "surface_air_pressure_standard_deviation",
            "long name": "barometric pressure standard deviation",
        },
        "barometric_pressure_sample_count": {
            "name": "barometric_pressure_sample_count",
            "ioos category": "pressure",
            "standard name": "surface_air_pressure_sample_count",
            "long name": "barometric pressure sample count",
        },
        "solar_radiation": {
            "name": "solar_radiation",
            "ioos category": "Meteorology",
            "standard name": "surface_downwelling_shortwave_flux_in_air",
            "long name": "solar radiation",
        },
        "solar_radiation_std_dev": {
            "name": "solar_radiation_std_dev",
            "ioos category": "Meteorology",
            "standard name": "surface_downwelling_shortwave_flux_in_air_standard_deviation",
            "long name": "solar radiation standard deviation",
        },
        "solar_radiation_sample_count": {
            "name": "solar_radiation_sample_count",
            "ioos category": "Meteorology",
            "standard name": "surface_downwelling_shortwave_flux_in_air_sample_count",
            "long name": "solar radiation sample count",
        },
        "longwave_radiation": {
            "name": "longwave_radiation",
            "ioos category": "Meteorology",
            "standard name": "surface_downwelling_longwave_flux_in_air",
            "long name": "longwave radiation",
        },
        "longwave_radiation_std_dev": {
            "name": "longwave_radiation_std_dev",
            "ioos category": "Meteorology",
            "standard name": "surface_downwelling_longwave_flux_in_air_standard_deviation",
            "long name": "longwave radiation standard deviation",
        },
        "longwave_radiation_sample_count": {
            "name": "longwave_radiation_sample_count",
            "ioos category": "Meteorology",
            "standard name": "surface_downwelling_longwave_flux_in_air_sample_count",
            "long name": "longwave radiation sample count",
        },
    }
    aggregation_attrs = {
        "aggregation_operation": "mean",
        "aggregation_interval": 60,
        "aggregation_interval_units": "seconds",
    }
    dataset_array = xarray.DataArray(
        name=metadata[var]["name"],
        data=array,
        attrs={
            "ioos_category": metadata[var]["ioos category"],
            "standard_name": metadata[var]["standard name"],
            "long_name": metadata[var]["long name"],
        },
    )
    with suppress(AttributeError):
        dataset_array.attrs["units"] = array.units
    for attr in {"flag_values", "flag_meanings", "comment"}:
        if attr in metadata[var]:
            dataset_array.attrs[attr] = metadata[var][attr]
    dataset_array.attrs.update(aggregation_attrs)
    location_vars = {"longitude", "latitude", "on_crossing_mask", "crossing_number"}
    dataset_array.attrs["ONC_stationCode"] = f"{ferry_platform}"
    try:
        dataset_array.attrs["ONC_data_product_url"] = metadata[var][
            "ONC_data_product_url"
        ]
        if var in ("longitude", "latitude"):
            dataset_array.attrs["ONC_stationCode"] = array.attrs["station"]
            dataset_array.attrs[
                "ONC_data_product_url"
            ] += f'&location={array.attrs["station"]}'
    except KeyError:
        dataset_array.attrs["ONC_data_product_url"] = (
            f"http://dmas.uvic.ca/DataSearch?location={ferry_platform}"
            f"&deviceCategory={array.device_category}"
        )
    return dataset_array


if __name__ == "__main__":
    main()  # pragma: no cover
