# Copyright 2013-2016 The Salish Sea MEOPAR Contributors
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

"""Salish Sea nowcast worker that downloads the University of Washington
Live Ocean model forecast product for a specified date and extracts from it
a hyperslab that covers the Salish Sea NEMO model western (Juan de Fuca)
open boundary.
"""
import logging
import math
import multiprocessing
from pathlib import Path

import arrow
import nemo_cmd.api
import requests
import salishsea_tools.UBC_subdomain
from nemo_nowcast import get_web_data, NowcastWorker

from nowcast import lib

NAME = 'download_live_ocean'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.download_live_ocean -h`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_date_option(
        '--run-date', default=arrow.utcnow().floor('day'),
        help='Date to download the Live Ocean forecast product for.')
    worker.run(download_live_ocean, success, failure)


def success(parsed_args):
    ymd = parsed_args.run_date.format('YYYY-MM-DD')
    logger.info(
        '{date} Live Ocean western boundary sub-domain files created'.format(
            date=ymd), extra={'run_date': ymd})
    msg_type = 'success'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    ymd = parsed_args.run_date.format('YYYY-MM-DD')
    logger.critical(
        '{date} Live Ocean western boundary sub-domain files '
        'creation failed'.format(date=ymd), extra={'run_date': ymd})
    msg_type = 'failure'
    return msg_type


def download_live_ocean(parsed_args, config, *args):
    yyyymmdd = parsed_args.run_date.format('YYYYMMDD')
    ymd = parsed_args.run_date.format('YYYY-MM-DD')
    logger.info(
        'downloading hourly Live Ocean forecast starting on {date}'.format(
            date=ymd, extra={'run_date': ymd}))
    base_url = config['temperature salinity']['download']['url']
    dir_prefix = config['temperature salinity']['download']['directory prefix']
    filename_tmpl = config['temperature salinity']['download']['file template']
    url = (
        '{base_url}{dir_prefix}{yyyymmdd}/{filename_tmpl}'.format(
            base_url=base_url,
            dir_prefix=dir_prefix,
            yyyymmdd=yyyymmdd,
            filename_tmpl=filename_tmpl))
    hours = config['temperature salinity']['download']['hours range']
    dest_dir = Path(
        config['temperature salinity']['download']['dest dir'], yyyymmdd)
    grp_name = config['file group']
    lib.mkdir(str(dest_dir), logger, grp_name=grp_name)
    checklist = {ymd: []}
    with requests.Session() as session:
        for hr in range(hours[0], hours[1] + 1):
            filepath = _get_file(
                url.format(hh=hr), filename_tmpl.format(hh=hr), dest_dir,
                session)
            salishsea_tools.UBC_subdomain.get_UBC_subdomain([str(filepath)])
            subdomain_filepath = str(filepath).replace('.nc', '_UBC.nc')
            logger.debug(
                'extracted UBC sub-domain: {}'.format(subdomain_filepath),
                extra={'subdomain_filepath': subdomain_filepath})
            checklist[ymd].append(subdomain_filepath)
            filepath.unlink()
    nemo_cmd.api.deflate(
        dest_dir.glob('*.nc'), math.floor(multiprocessing.cpu_count() / 2))
    return checklist


def _get_file(url, filename, dest_dir, session):
    """
    :type dest_dir: :class:`pathlib.Path`
    """
    filepath = dest_dir / filename
    get_web_data(url, NAME, filepath, session)
    size = filepath.stat().st_size
    logger.debug(
        'downloaded {} bytes from {}'.format(size, url),
        extra={'url': url, 'dest_dir': dest_dir})
    return filepath


if __name__ == '__main__':
    main()  # pragma: no cover
