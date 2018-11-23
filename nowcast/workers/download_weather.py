#  Copyright 2013-2018 The Salish Sea MEOPAR contributors
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
"""Salish Sea NEMO nowcast weather model dataset download worker.

Download the GRIB2 files from today's 00, 06, 12, or 18 Environment Canada
GEM 2.5km HRDPS operational model forecast.
"""
import logging
import os
from pathlib import Path

import arrow
import requests
from nemo_nowcast import get_web_data, NowcastWorker, WorkerError

from nowcast import lib

NAME = "download_weather"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.download_weather --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "forecast",
        choices={"00", "06", "12", "18"},
        help="Name of forecast to download files from.",
    )
    worker.cli.add_argument(
        "--yesterday",
        action="store_true",
        help="Download forecast files for previous day's date.",
    )
    worker.run(get_grib, success, failure)


def success(parsed_args):
    if parsed_args.yesterday:
        ymd = arrow.now().floor("day").shift(days=-1).format("YYYY-MM-DD")
    else:
        ymd = arrow.now().floor("day").format("YYYY-MM-DD")
    logger.info(
        f"{ymd} weather forecast {parsed_args.forecast} downloads complete",
        extra={"forecast_date": ymd, "forecast": parsed_args.forecast},
    )
    msg_type = f"success {parsed_args.forecast}"
    return msg_type


def failure(parsed_args):
    if parsed_args.yesterday:
        ymd = arrow.now().floor("day").shift(days=-1).format("YYYY-MM-DD")
    else:
        ymd = arrow.now().floor("day").format("YYYY-MM-DD")
    logger.critical(
        f"{ymd} weather forecast {parsed_args.forecast} downloads failed",
        extra={"forecast_date": ymd, "forecast": parsed_args.forecast},
    )
    msg_type = f"failure {parsed_args.forecast}"
    return msg_type


def get_grib(parsed_args, config, *args):
    forecast = parsed_args.forecast
    date = _calc_date(parsed_args, forecast)
    logger.info(
        f"downloading {forecast} forecast GRIB2 files for {date}",
        extra={"forecast": parsed_args.forecast},
    )
    dest_dir_root = config["weather"]["download"]["GRIB dir"]
    grp_name = config["file group"]
    _mkdirs(dest_dir_root, date, forecast, grp_name)
    url_tmpl = config["weather"]["download"]["url template"]
    filename_tmpl = config["weather"]["download"]["file template"]
    forecast_duration = config["weather"]["download"]["forecast duration"]
    with requests.Session() as session:
        for forecast_hour in range(1, forecast_duration + 1):
            hr_str = f"{forecast_hour:0=3}"
            lib.mkdir(
                os.path.join(dest_dir_root, date, forecast, hr_str),
                logger,
                grp_name=grp_name,
                exist_ok=False,
            )
            for var in config["weather"]["download"]["grib variables"]:
                filepath = _get_file(
                    url_tmpl,
                    filename_tmpl,
                    var,
                    dest_dir_root,
                    date,
                    forecast,
                    hr_str,
                    session,
                )
                lib.fix_perms(filepath)
    checklist = {f"{date} {forecast} forecast": True}
    return checklist


def _calc_date(parsed_args, forecast):
    yesterday = parsed_args.yesterday
    utc = arrow.utcnow()
    utc = utc.shift(hours=-int(forecast))
    if yesterday:
        utc = utc.shift(days=-1)
    date = utc.format("YYYYMMDD")
    return date


def _mkdirs(dest_dir_root, date, forecast, grp_name):
    lib.mkdir(os.path.join(dest_dir_root, date), logger, grp_name=grp_name)
    lib.mkdir(
        os.path.join(dest_dir_root, date, forecast),
        logger,
        grp_name=grp_name,
        exist_ok=False,
    )


def _get_file(
    url_tmpl, filename_tmpl, var, dest_dir_root, date, forecast, hr_str, session
):
    filename = filename_tmpl.format(
        variable=var, date=date, forecast=forecast, hour=hr_str
    )
    filepath = os.path.join(dest_dir_root, date, forecast, hr_str, filename)
    file_url = url_tmpl.format(forecast=forecast, hour=hr_str, filename=filename)
    get_web_data(
        file_url, NAME, Path(filepath), session=session, wait_exponential_max=9000
    )
    size = os.stat(filepath).st_size
    logger.debug(
        f"downloaded {size} bytes from {file_url}", extra={"forecast": forecast}
    )
    if size == 0:
        logger.critical(
            f"Problem, 0 size file {file_url}", extra={"forecast": forecast}
        )
        raise WorkerError
    return filepath


if __name__ == "__main__":
    main()  # pragma: no cover
