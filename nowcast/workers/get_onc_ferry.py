# Copyright 2013-2017 The Salish Sea MEOPAR Contributors
# and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Salish Sea nowcast worker that downloads data for a specified UTC day from
an ONC BC Ferries measurement platform.

The data are filtered to include only values for which qaqcFlag == 1
(meaning that all of ONC's automated QA/QC tests were passed).
After filtering the data are aggregated into 1 minute bins.
The aggregation functions are mean, standard deviation, and sample count.

The data are stored as a netCDF-4/HDF5 file that is accessible via
https://salishsea.eos.ubc.ca/erddap/tabledap/.

Development notebook:
http://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/analysis-doug/raw/tip/notebooks/ONC-Ferry-DataToERDDAP.ipynb
"""
import logging
import os
from types import SimpleNamespace

import arrow
from nemo_nowcast import NowcastWorker, WorkerError
import numpy
import requests
from salishsea_tools import data_tools
from salishsea_tools.places import PLACES
import xarray

NAME = 'get_onc_ferry'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.get_onc_ferry -h`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'ferry_platform',
        choices={'TWDP'},
        help='Name of the ONC ferry platform to download data for.',
    )
    worker.cli.add_date_option(
        '--data-date',
        default=arrow.now().floor('day').replace(days=-1),
        help='UTC date to get ONC ferry data for.'
    )
    worker.run(get_onc_ferry, success, failure)


def success(parsed_args):
    ymd = parsed_args.data_date.format('YYYY-MM-DD')
    logger.info(
        f'{ymd} ONC {parsed_args.ferry_platform} ferry data file created',
        extra={
            'data_date': ymd,
            'ferry_platform': parsed_args.ferry_platform,
        }
    )
    msg_type = f'success {parsed_args.ferry_platform}'
    return msg_type


def failure(parsed_args):
    ymd = parsed_args.data_date.format('YYYY-MM-DD')
    logger.critical(
        f'{ymd} ONC {parsed_args.ferry_platform} ferry data file creation '
        f'failed',
        extra={
            'data_date': ymd,
            'ferry_platform': parsed_args.ferry_platform,
        }
    )
    msg_type = 'failure'
    return msg_type


def get_onc_ferry(parsed_args, config, *args):
    ymd = parsed_args.data_date.format('YYYY-MM-DD')
    ferry_platform = parsed_args.ferry_platform
    ferries = {
        'TWDP': {
            'devices': [
                {
                    'category': 'TSG',
                    # Use '' to get all sensors because an API bug prevents
                    # inclusion of 'conducivity' in sensors string
                    'sensors': '',
                },
                {
                    'category': 'OXYSENSOR',
                    'sensors': 'oxygen_saturation,oxygen_corrected',
                },
                {
                    'category': 'TURBCHLFL',
                    'sensors': 'cdom_fluorescence,chlorophyll,turbidity',
                },
                {
                    'category': 'CO2SENSOR',
                    'sensors': 'partial_pressure,co2',
                }
            ]
        }
    }
    ferry_config = (
        config['observations']['ferry data']['ferries'][ferry_platform])
    location_config = ferry_config['location']
    devices_config = ferry_config['devices']
    data_arrays = SimpleNamespace()
    # nav_data = _get_nav_data(ferry_platform, ymd, location_config)
    # (
    #     data_arrays.lons, data_arrays.lats, data_arrays.on_crossing_mask,
    #     data_arrays.crossing_numbers,
    # ) = _calc_location_arrays(nav_data, location_config)

    tsg_data = _get_water_data(ferry_platform, 'TSG', ymd, devices_config)
    print(tsg_data)
    o2_data = _get_water_data(ferry_platform, 'OXYSENSOR', ymd, devices_config)
    print(o2_data)


    # dataset = _create_dataset(
    #     data_arrays, ferry_platform, ferry_config, location_config)

    # print(dataset)

    # for device in ferries[parsed_args.ferry_platform]['devices']:
    #     logger.info(
    #         f'requesting ONC {parsed_args.ferry_platform} {device} data for '
    #         f'{ymd}',
    #         extra={
    #             'data_date': ymd,
    #             'ferry_platform': parsed_args.ferry_platform})
    #     onc_data = data_tools.get_onc_data(
    #         'scalardata', 'getByStation', token,
    #         station=parsed_args.ferry_platform,
    #         device_category=device['category'],
    #         sensors=device['sensors'],
    #         dateFrom=date_from,
    #     )


def _get_water_data(ferry_platform, device_category, ymd, devices_config):
    sensors = '' if device_category == 'TSG' else ','.join(
        devices_config[device_category]['sensors'].values())
    logger.info(
        f'requesting ONC {ferry_platform} {device_category} data for {ymd}',
        extra={
            'data_date': ymd,
            'ferry_platform': ferry_platform,
            'device_category': device_category,
        }
    )
    try:
        onc_data = data_tools.get_onc_data(
            'scalardata',
            'getByStation',
            os.environ['ONC_USER_TOKEN'],
            station=ferry_platform,
            deviceCategory=device_category,
            sensors=sensors,
            dateFrom=(data_tools.onc_datetime(f'{ymd} 00:00', 'utc')),
        )
    except requests.HTTPError as e:
        msg = (
            f'request for ONC {ferry_platform} {device_category} data '
            f'for {ymd} failed: {e}')
        logger.error(msg,
                     extra={
                         'data_date': ymd,
                         'ferry_platform': ferry_platform,
                         'device_category': device_category,
                     }
                     )
        raise WorkerError(msg)
    device_data = data_tools.onc_json_to_dataset(onc_data)
    logger.debug(
        f'ONC {ferry_platform} {device_category} data for {ymd} '
        f'received and parsed',
        extra={
            'data_date': ymd,
            'ferry_platform': ferry_platform,
            'device_category': device_category,
        }
    )
    return device_data


def _get_nav_data(ferry_platform, ymd, location_config):
    station = location_config['station']
    device_category = location_config['device category']
    sensors = ','.join(location_config['sensors'])
    logger.info(
        f'requesting ONC {station} {device_category} data for {ymd}',
        extra={
            'data_date': ymd,
            'ferry_platform': ferry_platform,
            'device_category': device_category,
        }
    )
    try:
        onc_data = data_tools.get_onc_data(
            'scalardata',
            'getByStation',
            os.environ['ONC_USER_TOKEN'],
            station=station,
            deviceCategory=device_category,
            sensors=sensors,
            dateFrom=(data_tools.onc_datetime(f'{ymd} 00:00', 'utc')),
        )
    except requests.HTTPError as e:
        msg = (
            f'request for ONC {station} {device_category} data for {ymd} '
            f'failed: {e}')
        logger.error(msg,
            extra={
                'data_date': ymd,
                'ferry_platform': ferry_platform,
                'device_category': device_category,
            }
        )
        raise WorkerError(msg)
    nav_data = data_tools.onc_json_to_dataset(onc_data)
    logger.debug(
        f'ONC {station} {device_category} data for {ymd} received and parsed',
        extra={
            'data_date': ymd,
            'ferry_platform': ferry_platform,
            'device_category': device_category,
        }
    )
    return nav_data


def _calc_location_arrays(nav_data, location_config):
    lons = (
        nav_data.longitude.resample('1Min', 'sampleTime', how='mean').rename({
            'sampleTime': 'time'
        })
    )
    lats = (
        nav_data.latitude.resample('1Min', 'sampleTime', how='mean').rename({
            'sampleTime': 'time'
        })
    )
    terminals = [
        SimpleNamespace(
            lon=PLACES[terminal]['lon lat'][0],
            lat=PLACES[terminal]['lon lat'][1],
            radius=PLACES[terminal]['in berth radius'],
        ) for terminal in location_config['terminals']
    ]
    on_crossing_mask = _on_crossing(lons, lats, terminals)
    crossing_numbers = _calc_crossing_numbers(on_crossing_mask)
    return lons, lats, on_crossing_mask, crossing_numbers


def _on_crossing(lons, lats, terminals):
    in_berth = numpy.logical_or(
        numpy.logical_and(
            numpy.logical_and(
                lons > (terminals[0].lon - terminals[0].radius),
                lons < (terminals[0].lon + terminals[0].radius)
            ),
            numpy.logical_and(
                lats > (terminals[0].lat - terminals[0].radius),
                lats < (terminals[0].lat + terminals[0].radius)
            )
        ),
        numpy.logical_and(
            numpy.logical_and(
                lons > (terminals[1].lon - terminals[1].radius),
                lons < (terminals[1].lon + terminals[1].radius)
            ),
            numpy.logical_and(
                lats > (terminals[1].lat - terminals[1].radius),
                lats < (terminals[1].lat + terminals[1].radius)
            )
        )
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
        name='crossing_number',
        data=crossing_numbers,
        coords={
            'time': on_crossing_mask.time.values,
        },
        dims='time',
    )


def _create_dataset(data_arrays, ferry_platform, ferry_config, location_config):
    metadata = {
        'lons': {
            'name': 'longitude',
            'ioos category': 'location',
            'standard name': 'longitude',
            'long name': 'Longitude',
            'units': 'degree_east',
            'ONC_data_product_url':
                f'http://dmas.uvic.ca/DataSearch'
                f'?location={location_config["station"]}'
                f'&deviceCategory={location_config["device category"]}'
        },
        'lats': {
            'name': 'latitude',
            'ioos category': 'location',
            'standard name': 'latitude',
            'long name': 'Latitude',
            'units': 'degree_north',
            'ONC_data_product_url':
                f'http://dmas.uvic.ca/DataSearch'
                f'?location={location_config["station"]}'
                f'&deviceCategory={location_config["device category"]}'
        },
        'on_crossing_mask': {
            'name': 'on_crossing_mask',
            'ioos category': 'identifier',
            'standard name': 'on_crossing_mask',
            'long name': 'On Crossing',
            'flag_values': '0, 1',
            'flag_meanings': 'in berth, on crossing',
            'ONC_data_product_url':
                f'http://dmas.uvic.ca/DataSearch?location={ferry_platform}'
        },
        'crossing_numbers': {
            'name': 'crossing_number',
            'ioos category': 'identifier',
            'standard name': 'crossing_number',
            'long name': 'Crossing Number',
            'flag_values': '0.0, 1.0, 2.0, ...',
            'flag_meanings': 'UTC day crossing number',
            'comment':
                'The first and last crossings of a UTC day are typically '
                'incomplete because the ferry operates in the Pacific '
                'time zone. '
                'To obtain a complete dataset for the 1st crossing of the '
                'UTC day, '
                'concatenate the crossing_number==0 observations to the '
                'crossing_number==n observation from the previous day, '
                'where n is max(crossing_number). '
                'The number of crossings per day varies throughout the year.',
            'ONC_data_product_url':
                f'http://dmas.uvic.ca/DataSearch?location={ferry_platform}'
        }
    }
    aggregation_attrs = {
        'aggregation_operation': 'mean',
        'aggregation_interval': 60,
        'aggregation_interval_units': 'seconds',
    }
    data_vars = {}
    for var, array in data_arrays.__dict__.items():
        data_vars[var] = xarray.DataArray(
            name=metadata[var]['name'],
            data=array,
            attrs={
                'ioos_category': metadata[var]['ioos category'],
                'standard_name': metadata[var]['standard name'],
                'long_name': metadata[var]['long name'],
            }
        )
        for attr in ('units', 'flag_values', 'flag_meaning', 'comment'):
            if attr in metadata[var]:
                data_vars[var].attrs[attr] = metadata[var][attr]
        data_vars[var].attrs.update(aggregation_attrs)
        data_vars[var].attrs['ONC_stationCode'] = (
            f'{location_config["station"]}')
        data_vars[var].attrs[var] = metadata[var]['ONC_data_product_url']
    now = arrow.now().format('YYYY-MM-DD HH:mm:ss')
    dataset = xarray.Dataset(
        data_vars=data_vars,
        coords={
            'time': data_arrays.lons.time.values,
        },
        attrs={
            'history': f"""{now} Download raw data from ONC scalardata API.
{now} Filter to exclude data with qaqcFlag != 1.
{now} Resample data to 1 minute intervals using mean, standard deviation and 
count as aggregation functions.
{now} Store as netCDF4 file.
""",
            'ferry_route_name': ferry_config['route name'],
            'ONC_stationDescription': ferry_config['ONC station description'],
        },
    )
    return dataset


if __name__ == '__main__':
    main()  # pragma: no cover
