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

"""Salish Sea NEMO nowcast worker that downloads the results files
from a nowcast run on the HPC/cloud facility to archival storage.
"""
import glob
import logging
import os

import arrow

from nowcast import lib
from nowcast.nowcast_worker import NowcastWorker


worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)


def main():
    worker = NowcastWorker(worker_name, description=__doc__)
    salishsea_today = arrow.now('Canada/Pacific').floor('day')
    worker.arg_parser.add_argument(
        'host_name',
        help='Name of the host to download results files from',
    )
    worker.arg_parser.add_argument(
        'run_type',
        choices=set(('nowcast', 'nowcast-green', 'forecast', 'forecast2')),
        help='Type of run to download results files from.',
    )
    worker.arg_parser.add_argument(
        '--run-date', type=lib.arrow_date,
        default=salishsea_today,
        help='''
        Date of the run to download results files from;
        use YYYY-MM-DD format.
        Defaults to {}.
        '''.format(salishsea_today.format('YYYY-MM-DD')),
    )
    worker.run(download_results, success, failure)


def success(parsed_args):
    logger.info(
        '{0.run_type} results files from {0.host_name} downloaded'
        .format(parsed_args), extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = '{} {}'.format('success', parsed_args.run_type)
    return msg_type


def failure(parsed_args):
    logger.critical(
        '{0.run_type} results files download from {0.host_name} failed'
        .format(parsed_args), extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = '{} {}'.format('failure', parsed_args.run_type)
    return msg_type


def download_results(parsed_args, config, *args):
    host_name = parsed_args.host_name
    run_date = parsed_args.run_date
    run_type = parsed_args.run_type
    host = config['run'][host_name]
    results_dir = run_date.strftime('%d%b%y').lower()
    src_dir = os.path.join(host['results'][run_type], results_dir)
    src = (
        '{host}:{src_dir}'.format(host=host_name, src_dir=src_dir))
    dest = os.path.join(config['run']['results archive'][run_type])
    cmd = ['scp', '-Cpr', src, dest]
    lib.run_in_subprocess(cmd, logger.debug, logger.error)
    lib.fix_perms(
        os.path.join(dest, results_dir),
        mode=lib.PERMS_RWX_RWX_R_X, grp_name='sallen')
    for filepath in glob.glob(os.path.join(dest, results_dir, '*')):
        lib.fix_perms(filepath, grp_name='sallen')
    checklist = {run_type: {}}
    for freq in '1h 1d'.split():
        checklist[run_type][freq] = glob.glob(
            os.path.join(dest, results_dir, 'SalishSea_{}_*.nc'.format(freq)))
    return checklist


if __name__ == '__main__':
    main()
