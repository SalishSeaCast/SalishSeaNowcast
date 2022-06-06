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


"""SalishSeaCast worker that creates a tarball of a month's run results and
moves it to remote archival storage. Compression is *not* used for the tarball
because the netCDF files that compose most of it are already highly compressed.
A .index text file containing a list of the files in the tarball is also created
and moved to the remote storage.
"""
import argparse
import functools
import logging
import os
import stat
import tarfile
from pathlib import Path

import arrow
import sysrsync
from nemo_nowcast import NowcastWorker

NAME = "archive_tarball"
logger = logging.getLogger(NAME)


def main():
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "run_type",
        choices={
            "nowcast",
            "nowcast-green",
            "nowcast-agrif",
        },
        help="Type of run to archive results files from.",
    )
    worker.cli.add_argument(
        "yyyy_mmm",
        type=_arrow_yyyy_mmm,
        help="Year and month of run results to archive. Use YYYY-MMM format.",
    )
    worker.cli.add_argument(
        "dest_host",
        default="graham-dtn",
        help="Name of the host to move tarball and index files to. Default is :kbd:`graham-dtn`.",
    )
    worker.run(archive_tarball, success, failure)
    return worker


def _arrow_yyyy_mmm(string):
    """Convert a YYYY-MMM string to a UTC arrow object or raise
    :py:exc:`argparse.ArgumentTypeError`.

    The day part of the resulting arrow object is set to 01,
    and the time part is set to 00:00:00.

    :arg str string: YYYY-MMM string to convert.

    :returns: Year-month string converted to a UTC :py:class:`arrow.Arrow` object.

    :raises: :py:exc:`argparse.ArgumentTypeError`
    """
    try:
        return arrow.get(string, "YYYY-MMM")
    except arrow.parser.ParserError:
        msg = f"unrecognized year-month format: {string} - please use YYYY-MMM"
        raise argparse.ArgumentTypeError(msg)


def success(parsed_args):
    logger.info(
        f'{parsed_args.run_type} {parsed_args.yyyy_mmm.format("*MMMYY").lower()} '
        f"results files archived to {parsed_args.dest_host}"
    )
    msg_type = f"success {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    logger.critical(
        f'{parsed_args.run_type} {parsed_args.yyyy_mmm.format("*MMMYY").lower()} '
        f"results files archiving to {parsed_args.dest_host} failed"
    )
    msg_type = f"failure {parsed_args.run_type}"
    return msg_type


def archive_tarball(parsed_args, config, *args):
    run_type = parsed_args.run_type
    yyyy_mmm = parsed_args.yyyy_mmm.format("MMMYY").lower()
    dest_host = parsed_args.dest_host
    tmp_tarball_dir = Path(config["results tarballs"]["temporary tarball dir"])
    run_type_results = Path(config["results archive"][run_type])
    tarball = tmp_tarball_dir / f"{run_type_results.parts[-1]}-{yyyy_mmm}.tar"
    results_path_pattern = run_type_results / f"*{yyyy_mmm}"
    logger.info(f"creating {tarball} from {results_path_pattern}/")
    _create_tarball(tarball, results_path_pattern)
    logger.info(f"creating {tarball.with_suffix('.index')} from {tarball}")
    _create_tarball_index(tarball)
    dest_dir = Path(config["results tarballs"][dest_host]) / run_type_results.parts[-1]
    logger.info(f"rsync-ing {tarball} and index to {dest_host}:{dest_dir}/")
    _rsync_to_remote(tarball, dest_host, dest_dir)
    _delete_tmp_files(tarball)
    return {
        "tarball archived": {
            "tarball": os.fspath(tarball),
            "index": os.fspath(tarball.with_suffix(".index")),
            "destination": f"{dest_host}:{dest_dir}/",
        }
    }


def _create_tarball(tarball, results_path_pattern):
    """
    :param :py:class:`pathlib.Path` tarball:
    :param :py:class:`pathlib.Path` results_path_pattern:
    """
    with tarfile.open(tarball, "w") as tar:
        results_dir = results_path_pattern.parent.parent
        os.chdir(results_dir)
        for p in sorted(
            results_path_pattern.parent.glob(results_path_pattern.parts[-1])
        ):
            logger.debug(f"adding {p}/ to {tarball}")
            tar.add(p.relative_to(results_dir))


def _create_tarball_index(tarball):
    """
    :param :py:class:`pathlib.Path` tarball:
    """
    with tarball.with_suffix(".index").open("wt") as f:
        with tarfile.open(tarball, "r") as tar:
            for m in tar.getmembers():
                mode_str = stat.filemode(m.mode)[1:]
                mode = f"d{mode_str}" if m.isdir() else f"-{mode_str}"
                name = f"{m.name}/" if m.isdir() else m.name
                f.write(
                    f"{mode} {m.gname}/{m.uname} {m.size:>10} "
                    f"{arrow.get(m.mtime).format('YYYY-MM-DD HH:mm')} {name}\n"
                )


def _rsync_to_remote(tarball, dest_host, dest_dir):
    """
    :param :py:class:`pathlib.Path` tarball:
    :param str dest_host:
    :param :py:class:`pathlib.Path` dest_dir:
    """
    rsync = functools.partial(
        sysrsync.run,
        destination_ssh=dest_host,
        destination=os.fspath(dest_dir),
        options=["-t"],
    )
    logger.debug(f"rsync-ing {tarball} to {dest_host}:{dest_dir}/")
    rsync(source=os.fspath(tarball))
    logger.debug(
        f"rsync-ing {tarball.with_suffix('.index')} to {dest_host}:{dest_dir}/"
    )
    rsync(source=os.fspath(tarball.with_suffix(".index")))


def _delete_tmp_files(tarball):
    """
    :param :py:class:`pathlib.Path` tarball:
    """
    logger.debug(f"deleting {tarball}")
    tarball.unlink()
    logger.debug(f"deleting {tarball.with_suffix('.index')}")
    tarball.with_suffix(".index").unlink()


if __name__ == "__main__":
    main()  # pragma: no cover
