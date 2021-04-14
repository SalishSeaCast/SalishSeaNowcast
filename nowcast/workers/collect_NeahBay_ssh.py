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
"""SalishSeaCast worker that collects a file containing sea surface height observations and
forecast values at Neah Bay from an HTTPS server and stores them locally for subsequent processing
by another worker to produce a sea surface height boundary condition file.
"""
import logging
import os
import tarfile
import tempfile
from pathlib import Path

import arrow
from nemo_nowcast import get_web_data, NowcastWorker

NAME = "collect_NeahBay_ssh"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.collect_NeahBay_ssh --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "forecast",
        choices={"00", "06", "12", "18"},
        help="Name of forecast to collect files for.",
    )
    worker.cli.add_date_option(
        "--data-date",
        default=arrow.now().floor("day"),
        help="Date to collect Neah Bay ssh data for.",
    )
    worker.run(collect_NeahBay_ssh, success, failure)
    return worker


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    data_date = parsed_args.data_date
    forecast = parsed_args.forecast
    logger.info(
        f"{data_date} Neah Bay ssh {forecast}Z obs/forecast data collection complete"
    )
    return f"success {forecast}"


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    data_date = parsed_args.data_date
    forecast = parsed_args.forecast
    logger.critical(
        f"{data_date} Neah Bay ssh {forecast}Z obs/forecast data collection failed"
    )
    return f"failure {forecast}"


def collect_NeahBay_ssh(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    data_date = parsed_args.data_date
    yyyymmdd = arrow.get(data_date).format("YYYYMMDD")
    forecast = parsed_args.forecast
    logger.info(
        f"collecting Neah Bay ssh {forecast}Z obs/forecast for {data_date.format('YYYY-MM-DD')}"
    )
    url_tmpl = config["ssh"]["download"]["url template"]
    tar_url = url_tmpl.format(yyyymmdd=yyyymmdd, forecast=forecast)
    tar_file_tmpl = config["ssh"]["download"]["tar file template"]
    tar_file = tar_file_tmpl.format(yyyymmdd=yyyymmdd, forecast=forecast)
    ssh_dir = Path(config["ssh"]["ssh dir"])
    csv_file = Path(tar_file).with_suffix(".csv")
    csv_file_path = ssh_dir / "txt" / csv_file
    tar_csv_tmpl = config["ssh"]["download"]["tarball csv file template"]
    tar_csv_member = tar_csv_tmpl.format(yyyymmdd=yyyymmdd, forecast=forecast)
    with tempfile.TemporaryDirectory() as tmp_dir:
        tar_file_path = Path(tmp_dir, tar_file)
        logger.debug(f"downloading {tar_url}")
        get_web_data(tar_url, NAME, tar_file_path)
        size = os.stat(tar_file_path).st_size
        logger.debug(f"downloaded {size} bytes from {tar_url}")
        _extract_csv(tar_csv_member, tar_file_path, csv_file_path)
    checklist = {
        "data date": data_date,
        f"{forecast}": os.fspath(csv_file_path),
    }
    return checklist


def _extract_csv(tar_csv_member, tar_file_path, csv_file_path):
    with tarfile.open(tar_file_path) as tar:
        logger.debug(f"extracting {tar_csv_member} from tarball to {csv_file_path}")
        buff = tar.extractfile(tar.getmember(tar_csv_member))
        with csv_file_path.open("wb") as f:
            f.write(buff.read())
        size = os.stat(csv_file_path).st_size
        logger.debug(f"wrote {size} bytes to {csv_file_path}")


if __name__ == "__main__":
    main()  # pragma: no cover
