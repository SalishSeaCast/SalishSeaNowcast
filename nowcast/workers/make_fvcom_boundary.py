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
"""Salish Sea FVCOM Vancouver Harbour and Fraser River model worker that
produces boundary condition files for the FVCOM model open boundary in the
Strait of Georgia from the Salish Sea NEMO model results.
"""
import logging

import arrow
from nemo_nowcast import NowcastWorker

NAME = 'make_fvcom_boundary'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_fvcom_boundary --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name', help='Name of the host to make boundary files on'
    )
    worker.cli.add_argument(
        'run_type',
        choices={'nowcast', 'forecast'},
        help='''
        Type of run to make boundary files for:
        'nowcast' means run for present UTC day (after NEMO nowcast run)
        'forecast' means updated forecast run 
        (next 36h UTC, after NEMO forecast run)
        ''',
    )
    worker.cli.add_date_option(
        '--run-date',
        default=arrow.now().floor('day'),
        help='Date to make boundary files for.'
    )
    worker.run(make_fvcom_boundary, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f'FVCOM {parsed_args.run_type} run boundary condition files for '
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'created on {parsed_args.host_name}',
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = f'success {parsed_args.run_type}'
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f'FVCOM {parsed_args.run_type} run boundary condition files creation'
        f' for {parsed_args.run_date.format("YYYY-MM-DD")} '
        f'failed on {parsed_args.host_name}',
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = f'failure {parsed_args.run_type}'
    return msg_type


def make_fvcom_boundary(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    checklist = {}
    return checklist


if __name__ == '__main__':
    main()  # pragma: no cover
