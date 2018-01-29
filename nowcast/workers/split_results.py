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
"""Salish Sea nowcast worker that splits downloaded results of multi-day runs
(e.g. hindcast runs) into daily results directories.
The results files are renamed so that they look like they came from a
single day run so that ERDDAP will accept them.
The run description files are left in the first run day's directory.
The restart file is moved to the last run day's directory.
"""
import logging
from pathlib import Path

import arrow
import shutil
from nemo_nowcast import NowcastWorker

NAME = 'split_results'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.split_results --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'run_type',
        choices={'hindcast'},
        help='Type of run to split results files from.',
    )
    worker.cli.add_argument(
        'run_date',
        type=worker.cli._arrow_date,
        help=(
            'Date of the 1st day of the run to split results files from.'
            'Use YYYY-MM-DD format.'
        )
    )
    worker.run(split_results, success, failure)


def success(parsed_args):
    logger.info(
        '{0.run_type} {date} results files split into daily directories'
        .format(parsed_args, date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
            'run_type': parsed_args.run_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = '{} {}'.format('success', parsed_args.run_type)
    return msg_type


def failure(parsed_args):
    logger.critical(
        '{0.run_type} {date} results files splitting failed'
        .format(parsed_args, date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
            'run_type': parsed_args.run_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = '{} {}'.format('failure', parsed_args.run_type)
    return msg_type


def split_results(parsed_args, config, *args):
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    logger.info(
        'splitting {run_date} {run_type} results files '
        'into daily directories'.format(
            run_date=run_date.format('YYYY-MM-DD'), run_type=run_type
        ),
        extra={
            'run_type': run_type,
            'date': run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    results_dir = run_date.format('DDMMMYY').lower()
    run_type_results = Path(config['results archive'][run_type])
    src_dir = run_type_results / results_dir
    last_date = run_date
    checklist = set()
    for fp in src_dir.glob('*.nc'):
        if 'restart' in str(fp):
            continue
        date = arrow.get(fp.stem[-8:], 'YYYYMMDD')
        checklist.add(date.format('YYYY-MM-DD'))
        last_date = max(date, last_date)
        dest_dir = run_type_results / date.format('DDMMMYY').lower()
        dest_dir.mkdir(exist_ok=True)
        if fp.stem.startswith('SalishSea_1'):
            fn = Path(
                '{prefix}_{date}_{date}_{grid}'.format(
                    prefix=fp.stem[:12],
                    date=date.format('YYYYMMDD'),
                    grid=fp.stem[31:37]
                )
            ).with_suffix('.nc')
        else:
            fn = Path(fp.stem[:-18]).with_suffix('.nc')
        dest = dest_dir / fn
        shutil.move(str(fp), str(dest))
        logger.debug('moved {fp} to {dest}'.format(fp=fp, dest=dest))
    for fp in src_dir.glob('SalishSea_*_restart*.nc'):
        dest_dir = run_type_results / last_date.format('DDMMMYY').lower()
        shutil.move(str(fp), str(dest_dir))
        logger.debug(
            'moved {fp} to {dest_dir}'.format(fp=fp, dest_dir=dest_dir)
        )
    return checklist


if __name__ == '__main__':
    main()  # pragma: no cover
