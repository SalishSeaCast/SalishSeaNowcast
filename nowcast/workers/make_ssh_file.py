#  Copyright 2013-2021 The Salish Sea MEOPAR contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""SalishSeaCast worker that generates a sea surface height boundary conditions file from
NOAA Neah Bay observation and forecast values.
"""
import logging
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker

NAME = "make_ssh_file"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_ssh_file --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "run_type",
        choices={"nowcast", "forecast2"},
        help="""
        Type of run to prepare open boundary sea surface height file for:
        'nowcast' means nowcast & forecast runs,
        'forecast2' means preliminary forecast run
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="""
        Date to prepare open boundary sea surface height file for.
        Defaults to today.
        """,
    )
    worker.cli.add_argument(
        "--text-file",
        type=Path,
        help="""
        Absolute path and file name of legacy file like sshNB_YYYY-MM-DD_HH.txt
        to process instead of CSV file from NOAA tarball.
        **This option is intended for hindcast boundary file creation and should be used with
        the --debug option.**
        """,
    )
    worker.cli.add_argument(
        "--archive", action="store_true", help="text-file is archive type"
    )
    worker.run(make_ssh_file, success, failure)
    return worker


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    run_date = parsed_args.run_date
    run_type = parsed_args.run_type
    logger.info(
        f"sea surface height boundary file for {run_date.format('YYYY-MM-DD')} {run_type} run created"
    )
    return f"success {run_type}"


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    run_date = parsed_args.run_date
    run_type = parsed_args.run_type
    logger.critical(
        f"sea surface height boundary file for {run_date.format('YYYY-MM-DD')} {run_type} run creation failed"
    )
    return f"failure {run_type}"


def make_ssh_file(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    run_date = parsed_args.run_date
    run_type = parsed_args.run_type
    if parsed_args.text_file is None:
        pass
    checklist = {}
    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
