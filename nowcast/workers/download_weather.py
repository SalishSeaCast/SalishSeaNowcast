# Copyright 2013-2015 The Salish Sea MEOPAR contributors
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
Download the GRIB2 files from today's 00, 06, 12, or 18 EC GEM 2.5km
HRDPS operational model forecast.
"""
import logging
import os

import arrow

from nowcast import lib
from nowcast.nowcast_worker import (
    NowcastWorker,
    WorkerError,
)


worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)


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
    worker = NowcastWorker(worker_name, description=__doc__)
    worker.arg_parser.add_argument(
        'forecast', choices=set(('00', '06', '12', '18')),
        help='Name of forecast to download files from.',
    )
    worker.arg_parser.add_argument(
        '--yesterday', action='store_true',
        help="Download forecast files for previous day's date."
    )
    worker.run(get_grib, success, failure)


def success(parsed_args):
    logger.info(
        'weather forecast {.forecast} downloads complete'
        .format(parsed_args), extra={'forecast': parsed_args.forecast})
    msg_type = '{} {}'.format('success', parsed_args.forecast)
    return msg_type


def failure(parsed_args):
    logger.error(
        'weather forecast {.forecast} downloads failed'
        .format(parsed_args), extra={'forecast': parsed_args.forecast})
    msg_type = '{} {}'.format('failure', parsed_args.forecast)
    return msg_type


def get_grib(parsed_args, config, *args):
    forecast = parsed_args.forecast
    date = _calc_date(parsed_args, forecast)
    logger.info(
        'downloading {forecast} forecast GRIB2 files for {date}'
        .format(forecast=forecast, date=date),
        extra={'forecast': parsed_args.forecast})
    dest_dir_root = config['weather']['GRIB_dir']
    grp_name = config['file group']
    _mkdirs(dest_dir_root, date, forecast, grp_name)
    for forecast_hour in range(1, FORECAST_DURATION+1):
        hr_str = '{:0=3}'.format(forecast_hour)
        lib.mkdir(
            os.path.join(dest_dir_root, date, forecast, hr_str),
            logger, grp_name=grp_name, exist_ok=False)
        for var in GRIB_VARIABLES:
            filepath = _get_file(var, dest_dir_root, date, forecast, hr_str)
            lib.fix_perms(filepath)
    checklist = {'{} forecast'.format(forecast): True}
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


def _get_file(var, dest_dir_root, date, forecast, hr_str):
    filename = FILENAME_TEMPLATE.format(
        variable=var, date=date, forecast=forecast, hour=hr_str)
    filepath = os.path.join(
        dest_dir_root, date, forecast, hr_str, filename)
    fileURL = URL_TEMPLATE.format(
        forecast=forecast, hour=hr_str, filename=filename)
    headers = lib.get_web_data(
        fileURL, logger, filepath, retry_time_limit=9000)
    size = headers['Content-Length']
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
