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

"""Salish Sea nowcast worker that produces hourly temperature and salinity
boundary conditions files for the Salish Sea NEMO model western (Juan de Fuca)
open boundary from the University of Washington Live Ocean model forecast
product.
"""
import logging
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker
from salishsea_tools.LiveOcean_BCs import (
    create_LiveOcean_TS_BCs,
    create_LiveOcean_bio_BCs_fromTS,
)


NAME = 'make_live_ocean_files'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_live_ocean_files -h`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_date_option(
        '--run-date', default=arrow.now().floor('day'),
        help='''
        Date of Live Ocean forecast product to produce files from.
        Note that boundary conditions files are produced for the 2 days
        following run-date.
        ''')
    worker.run(make_live_ocean_files, success, failure)


def success(parsed_args):
    ymd = parsed_args.run_date.format('YYYY-MM-DD')
    logger.info(
        f'{ymd} Live Ocean western boundary conditions files created',
        extra={'run_date': ymd})
    msg_type = 'success'
    return msg_type


def failure(parsed_args):
    ymd = parsed_args.run_date.format('YYYY-MM-DD')
    logger.critical(
        f'{ymd} Live Ocean western boundary conditions files preparation '
        f'failed',
        extra={'run_date': ymd})
    msg_type = 'failure'
    return msg_type


def make_live_ocean_files(parsed_args, config, *args):
    ymd = parsed_args.run_date.format('YYYY-MM-DD')
    logger.info(
        f'Creating T&S western boundary conditions files from {ymd} Live '
        f'Ocean run')
    download_dir = Path(config['temperature salinity']['download']['dest dir'])
    bc_dir = Path(config['temperature salinity']['bc dir'])
    boundary_info = Path(config['temperature salinity']['boundary info'])
    checklist = create_LiveOcean_TS_BCs(
        ymd, ymd, '1D', 'daily', single_nowcast=True, teos_10=True,
        basename='single_LO',
        bc_dir=str(bc_dir), LO_dir=str(download_dir),
        NEMO_BC=str(boundary_info))

    # make bio files
    TSfile = config['temperature salinity']['file template'].format(
        parsed_args.run_date.date())
    checklist2 = create_LiveOcean_bio_BCs_fromTS(
        TSfile, strdate=None, TSdir=bc_dir,
        outFile=config['n and si']['file template'],
        outDir=config['n and si']['bc bio dir'],
        nFitFilePath=config['n and si']['n fit'],
        siFitFilePath=config['n and si']['si fit'],
        nClimFilePath=config['n and si']['n clim'],
        siClimFilePath=config['n and si']['si clim'],
        recalcFits=False
    )
    checklist.append(checklist2)
    return checklist


if __name__ == '__main__':
    main()  # pragma: no cover
