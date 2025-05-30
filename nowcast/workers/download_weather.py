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


"""SalishSeaCast worker that downloads the GRIB2 files from the 00, 06, 12, or 18
Environment and Climate Change Canada GEM 2.5km HRDPS operational model forecast.
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
    """For command-line usage see:

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
        "resolution",
        choices={"1km", "2.5km"},
        default="2.5km",
        help="Horizontal resolution of forecast to download files from.",
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Forecast date to download.",
    )
    worker.cli.add_argument(
        "--no-verify-certs",
        action="store_true",
        help="""
            Don't verify TLS/SSL certificates for downloads.
            NOTE: This is intended for use *only* when downloading from dd.alpha.meteo.gc.ca
            which has still uses deprecated TLS-1.0.
        """,
    )
    worker.cli.add_argument(
        "--backfill",
        action="store_true",
        help="""
            Don't abort if destination directory already exists.
            NOTE: This is intended for use in recovery from automation failures.
        """,
    )
    worker.run(get_grib, success, failure)
    return worker


def success(parsed_args):
    ymd = parsed_args.run_date.format("YYYY-MM-DD")
    logger.info(
        f"{ymd} {parsed_args.resolution} weather forecast {parsed_args.forecast} downloads complete"
    )
    msg_type = f"success {parsed_args.resolution} {parsed_args.forecast}"
    return msg_type


def failure(parsed_args):
    ymd = parsed_args.run_date.format("YYYY-MM-DD")
    logger.critical(
        f"{ymd} {parsed_args.resolution} weather forecast {parsed_args.forecast} downloads failed"
    )
    msg_type = f"failure {parsed_args.resolution} {parsed_args.forecast}"
    return msg_type


def get_grib(parsed_args, config, *args):
    forecast = parsed_args.forecast
    resolution = parsed_args.resolution.replace("km", " km")
    date = parsed_args.run_date.format("YYYYMMDD")
    logger.info(f"downloading {forecast} {resolution} forecast GRIB2 files for {date}")
    dest_dir_root = config["weather"]["download"][resolution]["GRIB dir"]
    grp_name = config["file group"]
    _mkdirs(dest_dir_root, date, forecast, grp_name, parsed_args.backfill)
    logger.debug(
        f"destination directory for {forecast} {resolution} forecast GRIB2 files: "
        f"{dest_dir_root}{date}/{forecast}"
    )
    url_tmpl = config["weather"]["download"][resolution]["url template"]
    filename_tmpl = config["weather"]["download"][resolution]["ECCC file template"]
    var_names = config["weather"]["download"][resolution]["variables"]
    # 2.5km config has collections of 3 names per var, 1km has just MSC var name
    msc_var_names = [
        var_name[0] if resolution == "2.5 km" else var_name for var_name in var_names
    ]
    forecast_duration = config["weather"]["download"][resolution]["forecast duration"]
    with requests.Session() as session:
        if parsed_args.no_verify_certs:
            session.verify = False
        for forecast_hour in range(1, forecast_duration + 1):
            hr_str = f"{forecast_hour:0=3}"
            lib.mkdir(
                Path(dest_dir_root, date, forecast, hr_str),
                logger,
                grp_name=grp_name,
                exist_ok=False,
            )
            for var_name in msc_var_names:
                filepath = _get_file(
                    url_tmpl,
                    filename_tmpl,
                    var_name,
                    dest_dir_root,
                    date,
                    forecast,
                    hr_str,
                    session,
                )
                lib.fix_perms(filepath)
    checklist = {
        f"{forecast} {resolution.replace(' km', 'km')}": os.path.join(
            dest_dir_root, date, forecast
        )
    }
    return checklist


def _mkdirs(dest_dir_root, date, forecast, grp_name, exist_ok):
    lib.mkdir(Path(dest_dir_root, date), logger, grp_name=grp_name)
    lib.mkdir(
        Path(dest_dir_root, date, forecast),
        logger,
        grp_name=grp_name,
        exist_ok=exist_ok,
    )


def _get_file(
    url_tmpl, filename_tmpl, var, dest_dir_root, date, forecast, hr_str, session
):
    filename = filename_tmpl.format(
        variable=var, date=date, forecast=forecast, hour=hr_str
    )
    filepath = Path(dest_dir_root, date, forecast, hr_str, filename)
    file_url = url_tmpl.format(
        date=date, forecast=forecast, hour=hr_str, filename=filename
    )
    get_web_data(file_url, NAME, filepath, session=session, wait_exponential_max=9000)
    size = os.stat(filepath).st_size
    logger.debug(f"downloaded {size} bytes from {file_url}")
    if size == 0:
        logger.critical(f"Problem! 0 size file: {file_url}")
        raise WorkerError
    return filepath


if __name__ == "__main__":
    main()  # pragma: no cover
