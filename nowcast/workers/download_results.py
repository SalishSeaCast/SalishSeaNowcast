# Copyright 2013-2017 The Salish Sea MEOPAR contributors
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

"""Salish Sea NEMO nowcast worker that downloads the results files
from a run on the HPC/cloud facility to archival storage.
"""
import glob
import logging
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker

from nowcast import lib


NAME = 'download_results'
logger = logging.getLogger(NAME)


def main():
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name',
        help='Name of the host to download results files from',
    )
    worker.cli.add_argument(
        'run_type',
        choices={
            'nowcast', 'nowcast-green', 'forecast', 'forecast2', 'hindcast'},
        help='Type of run to download results files from.',
    )
    worker.cli.add_date_option(
        '--run-date', default=arrow.now().floor('day'),
        help='Date of the run to download results files from.'
    )
    worker.run(download_results, success, failure)


def success(parsed_args):
    logger.info(
        f'{parsed_args.run_type} {parsed_args.run_date.format("YYYY-MM-DD")} '
        f'results files from {parsed_args.host_name} downloaded',
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = f'success {parsed_args.run_type}'
    return msg_type


def failure(parsed_args):
    logger.critical(
        f'{parsed_args.run_type} {parsed_args.run_date.format("YYYY-MM-DD")} '
        f'results files download from {parsed_args.host_name} failed',
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = f'failure {parsed_args.run_type}'
    return msg_type


def download_results(parsed_args, config, *args):
    host_name = parsed_args.host_name
    run_date = parsed_args.run_date
    run_type = parsed_args.run_type
    host_run_config = config['run'][host_name]
    results_dir = run_date.strftime('%d%b%y').lower()
    run_type_results = Path(host_run_config['results'][run_type])
    src_dir = run_type_results/results_dir
    src = f'{host_name}:{src_dir}'
    dest = Path(config['results archive'][run_type])
    cmd = ['scp', '-Cpr', src, str(dest)]
    lib.run_in_subprocess(cmd, logger.debug, logger.error)
    lib.fix_perms(
        str(dest/results_dir),
        mode=lib.PERMS_RWX_RWX_R_X, grp_name='sallen')
    results_archive_dir = dest/results_dir
    for filepath in results_archive_dir.glob('*'):
        lib.fix_perms(str(filepath), grp_name='sallen')
    checklist = {run_type: {}}
    for freq in '1h 1d'.split():
        checklist[run_type][freq] = list(map(str, results_archive_dir.glob(
            f'SalishSea_{freq}_*.nc')))
    return checklist


if __name__ == '__main__':
    main()  # pragma: no cover
