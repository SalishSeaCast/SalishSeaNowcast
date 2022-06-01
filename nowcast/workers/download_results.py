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

# SPDX-License-Identifier: Apache-2.0


"""SalishSeaCast worker that downloads the results files from a run
on an HPC/cloud facility to archival storage.
"""
import contextlib
import logging
import os
import shlex
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker, WorkerError

from nowcast import lib, ssh_sftp

NAME = "download_results"
logger = logging.getLogger(NAME)


def main():
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "host_name", help="Name of the host to download results files from"
    )
    worker.cli.add_argument(
        "run_type",
        choices={
            "nowcast",
            "nowcast-green",
            "forecast",
            "forecast2",
            "hindcast",
            "nowcast-agrif",
        },
        help="Type of run to download results files from.",
    )
    worker.cli.add_argument(
        "--dest-host",
        default="localhost",
        help="Name of the host to download results files to. Default is :kbd:`localhost`.",
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Date of the run to download results files from.",
    )
    worker.run(download_results, success, failure)
    return worker


def success(parsed_args):
    logger.info(
        f'{parsed_args.run_type} {parsed_args.run_date.format("YYYY-MM-DD")} '
        f"results files from {parsed_args.host_name} downloaded"
    )
    msg_type = f"success {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    logger.critical(
        f'{parsed_args.run_type} {parsed_args.run_date.format("YYYY-MM-DD")} '
        f"results files download from {parsed_args.host_name} failed"
    )
    msg_type = f"failure {parsed_args.run_type}"
    return msg_type


def download_results(parsed_args, config, *args):
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    dest_host = parsed_args.dest_host
    run_date = parsed_args.run_date
    try:
        try:
            # Hindcast special case 1st due to hindcast host in enabled hosts
            # with empty run types collection to enable forcing uploads
            host_config = config["run"]["hindcast hosts"][host_name]
        except KeyError:
            host_config = config["run"]["enabled hosts"][host_name]
    except KeyError:
        logger.critical(f"unrecognized host: {host_name}")
        raise WorkerError
    results_dir = run_date.format("DDMMMYY").lower()
    run_type_results = Path(host_config["run types"][run_type]["results"])
    src_dir = run_type_results / results_dir
    src = f"{host_name}:{src_dir}"
    try:
        dest = Path(config["results archive"][run_type])
    except TypeError:
        dest_path = Path(config["results archive"][run_type][dest_host])
        dest = dest_path if dest_host == "localhost" else f"{dest_host}:{dest_path}"
    logger.info(f"downloading results from {src} to {dest}")
    cmd = shlex.split(f"scp -pr {src} {dest}")
    lib.run_in_subprocess(cmd, logger.debug, logger.error)
    checklist = {run_type: {"run date": run_date.format("YYYY-MM-DD")}}
    if dest_host == "localhost":
        results_archive_dir = _tidy_localhost(run_type, dest, results_dir, config)
        for freq in "1h 1d".split():
            checklist[run_type][freq] = list(
                map(os.fspath, results_archive_dir.glob(f"*SalishSea_{freq}_*.nc"))
            )
    else:
        _tidy_dest_host(run_type, dest_host, dest_path, results_dir, config)
        checklist[run_type]["destination"] = dest
    return checklist


def _tidy_localhost(run_type, dest, results_dir, config):
    results_archive_dir = dest / results_dir
    if not run_type == "hindcast":
        # Keep FVCOM boundary slab files from hindcast runs so that we can do FVCOM hindcast runs
        for filepath in results_archive_dir.glob("FVCOM_[TUVW].nc"):
            filepath.unlink()
    lib.fix_perms(
        results_archive_dir,
        mode=int(lib.FilePerms(user="rwx", group="rwx", other="rx")),
        grp_name=config["file group"],
    )
    for filepath in results_archive_dir.glob("*"):
        lib.fix_perms(filepath, grp_name=config["file group"])
    return results_archive_dir


def _tidy_dest_host(run_type, dest_host, dest_path, results_dir, config):
    ssh_key = Path(
        os.environ["HOME"], ".ssh", config["run"]["enabled hosts"][dest_host]["ssh key"]
    )
    ssh_client, sftp_client = ssh_sftp.sftp(dest_host, ssh_key)
    with contextlib.ExitStack() as stack:
        [stack.enter_context(client) for client in (ssh_client, sftp_client)]
        results_archive_dir = dest_path / results_dir
        if not run_type == "hindcast":
            # Keep FVCOM boundary slab files from hindcast runs so that we can do FVCOM hindcast runs
            fvcom_bdy_slabs = ("FVCOM_T.nc", "FVCOM_U.nc", "FVCOM_V.nc", "FVCOM_W.nc")
            fvcom_bdy_files = [
                f
                for f in sftp_client.listdir(results_archive_dir)
                if Path(f).name in fvcom_bdy_slabs
            ]
            for f in fvcom_bdy_files:
                sftp_client.unlink(f)


if __name__ == "__main__":
    main()  # pragma: no cover
