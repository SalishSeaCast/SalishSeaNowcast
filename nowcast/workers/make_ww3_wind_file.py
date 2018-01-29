# Copyright 2013-2018 The Salish Sea MEOPAR contributors
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
"""Salish Sea WaveWatch3 forecast worker that produces the hourly wind forcing
file for a prelim-forecast or forecast run 
"""
import logging
import os
from pathlib import Path

import arrow
import xarray
from nemo_nowcast import NowcastWorker

NAME = 'make_ww3_wind_file'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_ww3_wind_file --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name', help='Name of the host to create the wind file on'
    )
    worker.cli.add_argument(
        'run_type',
        choices={'forecast2', 'forecast'},
        help='''
        Type of run to create wind file for:
        'forecast2' means preliminary forecast run (after NEMO forecast2 run),
        'forecast' means updated forecast run (after NEMO forecast run)
        ''',
    )
    worker.cli.add_date_option(
        '--run-date',
        default=arrow.now().floor('day'),
        help='Start date of run to create the wind file for.'
    )
    worker.run(make_ww3_wind_file, success, failure)


def success(parsed_args):
    logger.info(
        f'wwatch3 wind forcing file created '
        f'on {parsed_args.host_name} '
        f'for {parsed_args.run_date.format("YYYY-MM-DD")} '
        f'{parsed_args.run_type} run',
        extra={
            'run_type': parsed_args.run_type,
            'run_date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = f'success {parsed_args.run_type}'
    return msg_type


def failure(parsed_args):
    logger.critical(
        f'wwatch3 wind forcing file creation failed '
        f'on {parsed_args.host_name} '
        f'for {parsed_args.run_date.format("YYYY-MM-DD")} '
        f'{parsed_args.run_type} run',
        extra={
            'run_type': parsed_args.run_type,
            'run_date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = f'failure {parsed_args.run_type}'
    return msg_type


def make_ww3_wind_file(parsed_args, config, *args):
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    ymd = run_date.format('YYYY-MM-DD')
    logger.info(f'Creating wwatch3 wind forcing file for {ymd} {run_type} run')
    host_config = config['run']['enabled hosts'][host_name]
    hrdps_dir = Path(host_config['forcing']['weather dir'])
    hrdps_file_tmpl = config['weather']['file template']
    datasets = []
    if run_type == 'forecast':
        hrdps_file = hrdps_dir / hrdps_file_tmpl.format(run_date.datetime)
        datasets.append(os.fspath(hrdps_file))
        logger.debug(f'dataset: {hrdps_file}')
        day_range = arrow.Arrow.range(
            'day', run_date.replace(days=+1), run_date.replace(days=+2)
        )
        for day in day_range:
            hrdps_file = ((hrdps_dir / 'fcst') /
                          hrdps_file_tmpl.format(day.datetime))
            datasets.append(os.fspath(hrdps_file))
            logger.debug(f'dataset: {hrdps_file}')
    else:
        day_range = arrow.Arrow.range(
            'day', run_date, run_date.replace(days=+2)
        )
        for day in day_range:
            hrdps_file = ((hrdps_dir / 'fcst') /
                          hrdps_file_tmpl.format(day.datetime))
            datasets.append(os.fspath(hrdps_file))
            logger.debug(f'dataset: {hrdps_file}')
    dest_dir = Path(config['wave forecasts']['run prep dir'], 'wind')
    filepath_tmpl = config['wave forecasts']['wind file template']
    nc_filepath = (
        dest_dir / filepath_tmpl.format(yyyymmdd=run_date.format('YYYYMMDD'))
    )
    with xarray.open_dataset(datasets[0]) as lats_lons:
        lats = lats_lons.nav_lat
        lons = lats_lons.nav_lon
        logger.debug(f'lats and lons from: {datasets[0]}')
        with xarray.open_mfdataset(datasets) as hrdps:
            ds = _create_dataset(
                hrdps.time_counter, lats, lons, hrdps.u_wind, hrdps.v_wind,
                datasets
            )
            ds.to_netcdf(os.fspath(nc_filepath))
    logger.debug(f'stored wind forcing file: {nc_filepath}')
    checklist = {run_type: os.fspath(nc_filepath)}
    return checklist


def _create_dataset(time, lats, lons, u_wind, v_wind, datasets):
    now = arrow.now()
    ds = xarray.Dataset(
        data_vars={
            'u_wind': u_wind.rename({
                'time_counter': 'time'
            }),
            'v_wind': v_wind.rename({
                'time_counter': 'time'
            }),
        },
        coords={
            'time': time.rename('time').rename({
                'time_counter': 'time'
            }),
            'latitude': lats,
            'longitude': lons,
        },
        attrs={
            'creation_date': str(now),
            'history':
                f'[{now.format("YYYY-MM-DD HH:mm:ss")}] '
                f'created by SalishSeaNowcast make_ww3_wind_file worker',
            'source':
                f'EC HRDPS via UBC SalishSeaCast NEMO forcing datasets: '
                f'{datasets}'
        }
    )
    del ds.u_wind.attrs['coordinates']
    del ds.v_wind.attrs['coordinates']
    return ds


if __name__ == '__main__':
    main()  # pragma: no cover
