#  Copyright 2013-2020 The Salish Sea MEOPAR contributors
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
"""SalishSeaCast worker that splits downloaded results of multi-day runs
(e.g. hindcast runs) into daily results directories.
The results files are renamed so that they look like they came from a
single day run so that ERDDAP will accept them.
The run description files are left in the first run day's directory.
The restart file is moved to the last run day's directory.
"""
import logging
import os
import shutil
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker

NAME = "split_results"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.split_results --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "run_type",
        choices={"hindcast"},
        help="Type of run to split results files from.",
    )
    worker.cli.add_argument(
        "run_date",
        type=worker.cli.arrow_date,
        help=(
            "Date of the 1st day of the run to split results files from."
            "Use YYYY-MM-DD format."
        ),
    )
    worker.run(split_results, success, failure)
    return worker


def success(parsed_args):
    logger.info(
        f'{parsed_args.run_type} {parsed_args.run_date.format("YYYY-MM-DD")} '
        f"results files split into daily directories"
    )
    msg_type = f"success {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    logger.critical(
        f'{parsed_args.run_type} {parsed_args.run_date.format("YYYY-MM-DD")} '
        f"results files splitting failed"
    )
    msg_type = f"failure {parsed_args.run_type}"
    return msg_type


def split_results(parsed_args, config, *args):
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    logger.info(
        f'splitting {run_date.format("YYYY-MM-DD")} {run_type} '
        f"results files into daily directories"
    )
    results_dir = run_date.format("DDMMMYY").lower()
    try:
        run_type_results = Path(config["results archive"][run_type])
    except TypeError:
        run_type_results = Path(config["results archive"][run_type]["localhost"])
    src_dir = run_type_results / results_dir
    last_date = run_date
    checklist = set()
    for nc_file in src_dir.glob("*.nc"):
        if "restart" in os.fspath(nc_file):
            continue
        date = arrow.get(nc_file.stem[-8:], "YYYYMMDD")
        checklist.add(date.format("YYYY-MM-DD"))
        last_date = max(date, last_date)
        dest_dir = _mk_dest_dir(run_type_results, date)
        _move_results_nc_file(nc_file, dest_dir, date)
    for restart_file in src_dir.glob("SalishSea_*_restart*.nc"):
        dest_dir = run_type_results / last_date.format("DDMMMYY").lower()
        _move_restart_file(restart_file, dest_dir)
    return checklist


def _mk_dest_dir(run_type_results, date):
    """Separate function for testability."""
    dest_dir = run_type_results / date.format("DDMMMYY").lower()
    dest_dir.mkdir(exist_ok=True)
    return dest_dir


def _move_results_nc_file(nc_file, dest_dir, date):
    """Separate function for testability."""
    if nc_file.stem.startswith("SalishSea_1"):
        fn = Path(
            f"{nc_file.stem[:12]}_"
            f'{date.format("YYYYMMDD")}_{date.format("YYYYMMDD")}_'
            f"{nc_file.stem[31:37]}"
        ).with_suffix(".nc")
    else:
        fn = Path(nc_file.stem[:-18]).with_suffix(".nc")
    dest = dest_dir / fn
    shutil.move(os.fspath(nc_file), os.fspath(dest))
    logger.debug(f"moved {nc_file} to {dest}")


def _move_restart_file(restart_file, dest_dir):
    """Separate function for testability."""
    shutil.move(os.fspath(restart_file), os.fspath(dest_dir))
    logger.debug(f"moved {restart_file} to {dest_dir}")


if __name__ == "__main__":
    main()  # pragma: no cover
