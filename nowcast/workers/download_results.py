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

"""Salish Sea NEMO nowcast worker that downloads the results files
from a nowcast run on the HPC/cloud facility to archival storage.
"""
import argparse
import glob
import logging
import os
import traceback

import arrow
import zmq

from salishsea_tools.nowcast import lib


worker_name = lib.get_module_name()

logger = logging.getLogger(worker_name)

context = zmq.Context()


def main():
    # Prepare the worker
    base_parser = lib.basic_arg_parser(
        worker_name, description=__doc__, add_help=False)
    parser = configure_argparser(
        prog=base_parser.prog,
        description=base_parser.description,
        parents=[base_parser],
    )
    parsed_args = parser.parse_args()
    config = lib.load_config(parsed_args.config_file)
    lib.configure_logging(config, logger, parsed_args.debug)
    logger.debug('running in process {}'.format(os.getpid()))
    logger.debug('read config from {.config_file}'.format(parsed_args))
    lib.install_signal_handlers(logger, context)
    socket = lib.init_zmq_req_rep_worker(context, config, logger)
    # Do the work
    try:
        checklist = download_results(
            parsed_args.host_name, parsed_args.run_type, parsed_args.run_date,
            config)
        logger.info(
            '{0.run_type} results files from {0.host_name} downloaded'
            .format(parsed_args), extra={
                'run_type': parsed_args.run_type,
                'host_name': parsed_args.host_name,
                'date': parsed_args.run_date,
            })
        # Exchange success messages with the nowcast manager process
        msg_type = 'success {.run_type}'.format(parsed_args)
        lib.tell_manager(
            worker_name, msg_type, config, logger, socket, checklist)
    except lib.WorkerError:
        logger.critical(
            '{0.run_type} results files download from {0.host_name} failed'
            .format(parsed_args), extra={
                'run_type': parsed_args.run_type,
                'host_name': parsed_args.host_name,
                'date': parsed_args.run_date,
            })
        # Exchange failure messages with the nowcast manager process
        msg_type = 'failure {.run_type}'.format(parsed_args)
        lib.tell_manager(worker_name, msg_type, config, logger, socket)
    except SystemExit:
        # Normal termination
        pass
    except:
        logger.critical('unhandled exception:')
        for line in traceback.format_exc().splitlines():
            logger.error(line)
        # Exchange crash messages with the nowcast manager process
        lib.tell_manager(worker_name, 'crash', config, logger, socket)
    # Finish up
    context.destroy()
    logger.debug('task completed; shutting down')


def configure_argparser(prog, description, parents):
    parser = argparse.ArgumentParser(
        prog=prog, description=description, parents=parents)
    parser.add_argument(
        'host_name', help='Name of the host to download results files from')
    parser.add_argument(
        'run_type', choices=set(('nowcast', 'forecast', 'forecast2')),
        help='Type of run to download results files from.'
    )
    parser.add_argument(
        '--run-date', type=lib.arrow_date,
        default=arrow.now().date(),
        help='''
        Date of the run to download results files from;
        use YYYY-MM-DD format.
        Defaults to %(default)s.
        ''',
    )
    return parser


def download_results(host_name, run_type, run_date, config):
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
