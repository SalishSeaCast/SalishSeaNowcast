#  Copyright 2013 – present by the SalishSeaCast Project contributors
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
"""SalishSeaCast worker that downloads the results files
from a FVCOM Vancouver Harbour and Fraser River (VHFR) model run on the
cloud facility to archival storage.
"""
import logging
import os
import shlex
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker

from nowcast import lib

NAME = "download_fvcom_results"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.download_fvcom_results --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "host_name", help="Name of the host to download results files from"
    )
    worker.cli.add_argument(
        "model_config",
        choices={"r12", "x2"},
        help="""
        Model configuration to download results files from:
        'r12' means the r12 resolution
        'x2' means the x2 resolution
        """,
    )
    worker.cli.add_argument(
        "run_type",
        choices={"nowcast", "forecast"},
        help="Type of run to download results files from.",
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Date of the run to download results files from.",
    )
    worker.run(download_fvcom_results, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f"VHFR FVCOM {parsed_args.model_config} {parsed_args.run_type} "
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f"results files from {parsed_args.host_name} downloaded"
    )
    msg_type = f"success {parsed_args.model_config} {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f"VHFR FVCOM {parsed_args.model_config} {parsed_args.run_type} "
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f"results files download from {parsed_args.host_name} failed"
    )
    msg_type = f"failure {parsed_args.model_config} {parsed_args.run_type}"
    return msg_type


def download_fvcom_results(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    model_config = parsed_args.model_config
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    results_dir = run_date.format("DDMMMYY").lower()
    run_type_results = Path(
        config["vhfr fvcom runs"]["run types"][f"{run_type} {model_config}"]["results"]
    )
    src = f"{host_name}:{run_type_results / results_dir}"
    dest = Path(
        config["vhfr fvcom runs"]["results archive"][f"{run_type} {model_config}"]
    )
    cmd = shlex.split(f"scp -Cpr {src} {dest}")
    lib.run_in_subprocess(cmd, logger.debug, logger.error)
    results_archive_dir = dest / results_dir
    lib.fix_perms(
        dest / results_dir,
        mode=int(lib.FilePerms(user="rwx", group="rwx", other="rx")),
        grp_name=config["file group"],
    )
    for filepath in results_archive_dir.glob("*"):
        lib.fix_perms(filepath, grp_name=config["file group"])
    checklist = {
        run_type: {
            "host": host_name,
            "model config": model_config,
            "run date": run_date.format("YYYY-MM-DD"),
            "files": list(map(os.fspath, results_archive_dir.glob("vh*.nc"))),
        }
    }
    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
