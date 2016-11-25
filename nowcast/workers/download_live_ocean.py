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
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker
from salishsea_tools import UBC_subdomain


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
        '{date} Live Ocean western boundary sub-domain files created'
        .format(date=ymd), extra={'run_date': ymd})
    msg_type = 'success'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    ymd = parsed_args.run_date.format('YYYY-MM-DD')
    logger.critical(
        '{date} Live Ocean western boundary sub-domain files creation failed'
        .format(date=ymd), extra={'run_date': ymd})
    msg_type = 'failure'
    return msg_type


def download_live_ocean(parsed_args, config, *args):
    ymd = parsed_args.run_date.format('YYYY-MM-DD')
    checklist = {}
    return checklist
