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

"""Salish Sea NEMO nowcast weather model dataset download worker.

Download the GRIB2 files from today's 00, 06, 12, or 18 Environment Canada
GEM 2.5km HRDPS operational model forecast.
"""
import logging
import os
from pathlib import Path

import arrow
import requests
from nemo_nowcast import (
    get_web_data,
    NowcastWorker,
    WorkerError,
)

from nowcast import lib


NAME = 'download_weather'
logger = logging.getLogger(NAME)


GRIB_VARIABLES = (
    'UGRD_TGL_10_',  # u component of wind velocity at 10m elevation
    'VGRD_TGL_10_',  # v component of wind velocity at 10m elevation
    'DSWRF_SFC_0_',  # accumulated downward shortwave (solar) radiation
                     # at ground level
    'DLWRF_SFC_0_',  # accumulated downward longwave (thermal) radiation
                     # at ground level
    'TMP_TGL_2_',    # air temperature at 2m elevation
    'SPFH_TGL_2_',   # specific humidity at 2m elevation
    'APCP_SFC_0_',   # accumulated precipitation at ground level
    'PRMSL_MSL_0_',  # atmospheric pressure at mean sea level
)
URL_TEMPLATE = (
    'http://dd.weather.gc.ca/model_hrdps/west/grib2/'
    '{forecast}/{hour}/{filename}'
)
FILENAME_TEMPLATE = (
    'CMC_hrdps_west_{variable}ps2.5km_{date}{forecast}_P{hour}-00.grib2'
)
FORECAST_DURATION = 48  # hours


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.download_weather --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'forecast', choices=set(('00', '06', '12', '18')),
        help='Name of forecast to download files from.',
    )
    worker.cli.add_argument(
        '--yesterday', action='store_true',
        help="Download forecast files for previous day's date."
    )
    worker.run(get_grib, success, failure)


def success(parsed_args):
    if parsed_args.yesterday:
        ymd = arrow.now().floor('day').replace(days=-1).format('YYYY-MM-DD')
    else:
        ymd = arrow.now().floor('day').format('YYYY-MM-DD')
    logger.info(
        '{date} weather forecast {0.forecast} downloads complete'
        .format(parsed_args, date=ymd),
        extra={'forecast_date': ymd, 'forecast': parsed_args.forecast})
    msg_type = 'success {.forecast}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    if parsed_args.yesterday:
        ymd = arrow.now().floor('day').replace(days=-1).format('YYYY-MM-DD')
    else:
        ymd = arrow.now().floor('day').format('YYYY-MM-DD')
    logger.critical(
        '{date} weather forecast {0.forecast} downloads failed'
        .format(parsed_args, date=ymd),
        extra={'forecast_date': ymd, 'forecast': parsed_args.forecast})
    msg_type = 'failure {.forecast}'.format(parsed_args)
    return msg_type


def get_grib(parsed_args, config, *args):
    forecast = parsed_args.forecast
    date = _calc_date(parsed_args, forecast)
    logger.info(
        'downloading {forecast} forecast GRIB2 files for {date}'
        .format(forecast=forecast, date=date),
        extra={'forecast': parsed_args.forecast})
    dest_dir_root = config['weather']['GRIB dir']
    grp_name = config['file group']
    _mkdirs(dest_dir_root, date, forecast, grp_name)
    with requests.Session() as session:
        for forecast_hour in range(1, FORECAST_DURATION+1):
            hr_str = '{:0=3}'.format(forecast_hour)
            lib.mkdir(
                os.path.join(dest_dir_root, date, forecast, hr_str),
                logger, grp_name=grp_name, exist_ok=False)
            for var in GRIB_VARIABLES:
                filepath = _get_file(
                    var, dest_dir_root, date, forecast, hr_str, session)
                lib.fix_perms(filepath)
    checklist = {
        '{date} {forecast} forecast'
        .format(date=date, forecast=forecast): True}
    return checklist


def _calc_date(parsed_args, forecast):
    yesterday = parsed_args.yesterday
    utc = arrow.utcnow()
    utc = utc.replace(hours=-int(forecast))
    if yesterday:
        utc = utc.replace(days=-1)
    date = utc.format('YYYYMMDD')
    return date


def _mkdirs(dest_dir_root, date, forecast, grp_name):
    lib.mkdir(
        os.path.join(dest_dir_root, date),
        logger, grp_name=grp_name)
    lib.mkdir(
        os.path.join(dest_dir_root, date, forecast),
        logger, grp_name=grp_name, exist_ok=False)


def _get_file(var, dest_dir_root, date, forecast, hr_str, session):
    filename = FILENAME_TEMPLATE.format(
        variable=var, date=date, forecast=forecast, hour=hr_str)
    filepath = os.path.join(
        dest_dir_root, date, forecast, hr_str, filename)
    fileURL = URL_TEMPLATE.format(
        forecast=forecast, hour=hr_str, filename=filename)
    get_web_data(
        fileURL, Path(filepath), NAME,
        session=session, wait_exponential_max=9000)
    size = os.stat(filepath).st_size
    logger.debug(
        'downloaded {bytes} bytes from {fileURL}'
        .format(bytes=size, fileURL=fileURL), extra={'forecast': forecast})
    if size == 0:
        logger.critical(
            'Problem, 0 size file {}'.format(fileURL),
            extra={'forecast': forecast})
        raise WorkerError
    return filepath


if __name__ == '__main__':
    main()  # pragma: no cover
