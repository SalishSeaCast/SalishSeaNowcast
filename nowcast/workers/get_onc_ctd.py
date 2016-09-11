# Copyright 2013-2016 The Salish Sea MEOPAR contributors
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

"""Salish Sea nowcast worker that downloads CTD temperature and salinity data
for a specified UTC day from an ONC Strait of Georgia node.

The data are filtered to include only values for which qaqcFlag == 1
(meaning that all of ONC's automated QA/QC tests were passed).
After filtering the data are aggregated into 15 minute bins.
The aggregation functions are mean, standard deviation, and sample count.

The data are stored as a netCDF-4/HDF5 file that is accessible via
https://salishsea.eos.ubc.ca/erddap/tabledap/.

Development notebook:
http://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/analysis-doug/raw/tip/notebooks/ONC-CTD-DataToERDDAP.ipynb
"""
import logging
import os
from pathlib import Path

import arrow
import xarray

from salishsea_tools import data_tools
from salishsea_tools.places import PLACES

from nowcast import lib
from nowcast.nowcast_worker import NowcastWorker

worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.get_onc_ctd -h`
    """
    worker = NowcastWorker(worker_name, description=__doc__)
    salishsea_yesterday = arrow.utcnow().floor('day').replace(days=-1)
    worker.arg_parser.add_argument(
        'onc_station', choices={'SCVIP', 'SEVIP'},
        help='Name of the ONC node station to download data for.',
    )
    worker.arg_parser.add_argument(
        '--data-date', type=lib.arrow_date,
        default=salishsea_yesterday,
        help='''
        UTC date to get ONC node CTD data for; use YYYY-MM-DD format.
        Defaults to {}.
        '''.format(salishsea_yesterday.format('YYYY-MM-DD')),
    )
    worker.run(get_onc_ctd, success, failure)


def success(parsed_args):
    ymd = parsed_args.data_date.format('YYYY-MM-DD')
    logger.info(
        '{date} ONC {station} CTD T&S file created'
        .format(date=ymd, station=parsed_args.onc_station),
        extra={'data_date': ymd, 'onc_station': parsed_args.onc_station})
    msg_type = 'success {.onc_station}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    ymd = parsed_args.data_date.format('YYYY-MM-DD')
    logger.critical(
        '{date} ONC {station} CTD T&S file creation failed'
        .format(date=ymd, station=parsed_args.onc_station),
        extra={'data_date': ymd, 'onc_station': parsed_args.onc_station})
    msg_type = 'failure'
    return msg_type


def get_onc_ctd(parsed_args, config, *args):
    ymd = parsed_args.data_date.format('YYYY-MM-DD')
    logger.info(
        'requesting ONC {0.onc_station} CTD T&S data for {date}'
        .format(parsed_args, date=ymd),
        extra={'data_date': ymd, 'onc_station': parsed_args.onc_station})
    TOKEN = os.environ['ONC_USER_TOKEN']
    onc_data = data_tools.get_onc_data(
        'scalardata', 'getByStation', TOKEN,
        station=parsed_args.onc_station,
        deviceCategory='CTD',
        sensors='salinity,temperature',
        dateFrom=data_tools.onc_datetime('{} 00:00'.format(ymd), 'utc'),
    )
    ctd_data = data_tools.onc_json_to_dataset(onc_data)
    logger.debug(
        'ONC {0.onc_station} CTD T&S data for {date} received and parsed'
        .format(parsed_args, date=ymd),
        extra={'data_date': ymd, 'onc_station': parsed_args.onc_station})
    logger.debug(
        'filtering ONC {0.onc_station} salinity data for {date} '
        'to exlude qaqcFlag!=1'
        .format(parsed_args, date=ymd),
        extra={'data_date': ymd, 'onc_station': parsed_args.onc_station})
    salinity = _qaqc_filter(ctd_data, 'salinity')
    logger.debug(
        'filtering ONC {0.onc_station} temperature data for {date} '
        'to exlude qaqcFlag!=1'
        .format(parsed_args, date=ymd),
        extra={'data_date': ymd, 'onc_station': parsed_args.onc_station})
    temperature = _qaqc_filter(ctd_data, 'temperature')
    logger.debug(
        'creating ONC {0.onc_station} CTD T&S dataset for {date}'
        .format(parsed_args, date=ymd),
        extra={'data_date': ymd, 'onc_station': parsed_args.onc_station})
    ds = _create_dataset(parsed_args.onc_station, salinity, temperature)
    dest_dir = Path(config['observations']['ctd data']['dest dir'])
    filepath_tmpl = config['observations']['ctd data']['filepath template']
    nc_filepath = dest_dir/filepath_tmpl.format(
        station=parsed_args.onc_station,
        yyyymmdd=parsed_args.data_date.format('YYYYMMDD'))
    logger.debug(
        'storing ONC {0.onc_station} CTD T&S dataset for {date} as {file}'
        .format(parsed_args, date=ymd, file=nc_filepath),
        extra={'data_date': ymd, 'onc_station': parsed_args.onc_station})
    ds.to_netcdf(
        nc_filepath.as_posix(),
        encoding={'time': {'units': 'minutes since 1970-01-01 00:00'}})
    checklist = {parsed_args.onc_station: nc_filepath.as_posix()}
    return checklist


def _qaqc_filter(ctd_data, var):
    qaqc_mask = ctd_data.data_vars[var].attrs['qaqcFlag'] == 1
    filtered_var = xarray.DataArray(
        name=var,
        data=ctd_data.salinity[qaqc_mask].values,
        coords={'time': ctd_data.data_vars[var].sampleTime[qaqc_mask].values},
    )
    return filtered_var


def _create_dataset(onc_station, salinity, temperature):
    def count(values, axis):
        return values.size
    metadata = {
        'SCVIP': {
            'place_name': 'Central node',
            'ONC_station': 'Central',
            'ONC_stationDescription':
                'Pacific, Salish Sea, Strait of Georgia, Central, '
                'Strait of Georgia VENUS Instrument Platform',
        }
        'SEVIP': {
            'place_name': 'East node',
            'ONC_station': 'East',
            'ONC_stationDescription':
                'Pacific, Salish Sea, Strait of Georgia, East, '
                'Strait of Georgia VENUS Instrument Platform',
        }
    }
    ds = xarray.Dataset(
        data_vars={
            'salinity': xarray.DataArray(
                name='salinity',
                data=salinity.resample('15Min', 'time', how='mean'),
                attrs={
                    'ioos_category': 'Salinity',
                    'standard_name': 'sea_water_reference_salinity',
                    'long_name': 'reference salinity',
                    'units': 'g/kg',
                    'aggregation_operation': 'mean',
                    'aggregation_interval': 15 * 60,
                    'aggregation_interval_units': 'seconds',
                },
            ),
            'salinity_std_dev': xarray.DataArray(
                name='salinity_std_dev',
                data=salinity.resample('15Min', 'time', how='std'),
                attrs={
                    'ioos_category': 'Salinity',
                    'standard_name':
                        'sea_water_reference_salinity_standard_deviation',
                    'long_name': 'reference salinity standard deviation',
                    'units': 'g/kg',
                    'aggregation_operation': 'standard deviation',
                    'aggregation_interval': 15 * 60,
                    'aggregation_interval_units': 'seconds',
                },
            ),
            'salinity_sample_count': xarray.DataArray(
                name='salinity_sample_count',
                data=salinity.resample('15Min', 'time', how=count),
                attrs={
                    'standard_name':
                        'sea_water_reference_salinity_sample_count',
                    'long_name': 'reference salinity sample count',
                    'aggregation_operation': 'count',
                    'aggregation_interval': 15 * 60,
                    'aggregation_interval_units': 'seconds',
                },
            ),
            'temperature': xarray.DataArray(
                name='temperature',
                data=temperature.resample('15Min', 'time', how='mean'),
                attrs={
                    'ioos_category': 'Temperature',
                    'standard_name': 'sea_water_temperature',
                    'long_name': 'temperature',
                    'units': 'degrees_Celcius',
                    'aggregation_operation': 'mean',
                    'aggregation_interval': 15 * 60,
                    'aggregation_interval_units': 'seconds',
                },
            ),
            'temperature_std_dev': xarray.DataArray(
                name='temperature_std_dev',
                data=temperature.resample('15Min', 'time', how='std'),
                attrs={
                    'ioos_category': 'Temperature',
                    'standard_name': 'sea_water_temperature_standard_deviation',
                    'long_name': 'temperature standard deviation',
                    'units': 'degrees_Celcius',
                    'aggregation_operation': 'standard deviation',
                    'aggregation_interval': 15 * 60,
                    'aggregation_interval_units': 'seconds',
                },
            ),
            'temperature_sample_count': xarray.DataArray(
                name='temperature_sample_count',
                data=temperature.resample('15Min', 'time', how=count),
                attrs={
                    'standard_name': 'sea_water_temperature_sample_count',
                    'long_name': 'temperature sample count',
                    'aggregation_operation': 'count',
                    'aggregation_interval': 15 * 60,
                    'aggregation_interval_units': 'seconds',
                },
            ),
        },
        coords={
            'depth': PLACES[metadata[onc_station]['place_name']]['depth'],
            'longitude':
                PLACES[metadata[onc_station]['place_name']]['lon lat'][0],
            'latitude':
                PLACES[metadata[onc_station]['place_name']]['lon lat'][1],
        },
        attrs={
            'history': """
    {0} Download raw data from ONC scalardata API.
    {0} Filter to exclude data with qaqcFlag != 1.
    {0} Resample data to 15 minute intervals using mean, standard deviation
    and count as aggregation functions.
    {0} Store as netCDF4 file.
            """.format(arrow.now().format('YYYY-MM-DD HH:mm:ss')),
            'ONC_station': metadata[onc_station]['ONC_station'],
            'ONC_stationCode': onc_station,
            'ONC_stationDescription':
                metadata[onc_station]['ONC_stationDescription'],
            'ONC_data_product_url':
                'http://dmas.uvic.ca/DataSearch?location={station}'
                '&deviceCategory=CTD'.format(station=onc_station),
        },
    )
    return ds


if __name__ == '__main__':
    main()  # pragma: no cover
