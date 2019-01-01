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
"""SalishSeaCast worker that monitors a mirror of HRDPS files from the ECCC MSC datamart
model_hrdps.west.grib2 service, and moves the expected files into our atmospheric forcing
directory tree.
"""
import logging
import os
from pathlib import Path
import shutil
import time

import arrow
from nemo_nowcast import NowcastWorker
import watchdog.events
import watchdog.observers

from nowcast import lib

NAME = "collect_weather"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.collect_weather --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "forecast",
        choices={"00", "06", "12", "18"},
        help="Name of forecast to collect files for.",
    )
    worker.run(collect_weather, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    forecast_date = arrow.utcnow().shift(hours=-int(parsed_args.forecast))
    logger.info(
        f"{forecast_date.format('YYYY-MM-DD')} weather forecast "
        f"{parsed_args.forecast} collection complete"
    )
    return f"success {parsed_args.forecast}"


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    forecast_date = arrow.utcnow().shift(hours=-int(parsed_args.forecast))
    logger.critical(
        f"{forecast_date.format('YYYY-MM-DD')} weather forecast "
        f"{parsed_args.forecast} collection failed"
    )
    return f"failure {parsed_args.forecast}"


def collect_weather(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    forecast = parsed_args.forecast
    forecast_date = arrow.utcnow().shift(hours=-int(forecast) + 4).format("YYYYMMDD")
    datamart_dir = Path(config["weather"]["download"]["datamart dir"])
    grib_dir = Path(config["weather"]["download"]["GRIB dir"])
    grp_name = config["file group"]

    expected_files = _calc_expected_files(datamart_dir, forecast, forecast_date, config)

    lib.mkdir(grib_dir / forecast_date, logger, grp_name=grp_name)
    logger.debug(f"created {grib_dir / forecast_date}/")
    lib.mkdir(grib_dir / forecast_date / forecast, logger, grp_name=grp_name)
    logger.debug(f"created {grib_dir / forecast_date/forecast}/")

    handler = _GribFileEventHandler(
        expected_files, grib_dir / forecast_date / forecast, grp_name
    )
    observer = watchdog.observers.Observer()
    observer.schedule(handler, os.fspath(datamart_dir / forecast), recursive=True)
    logger.info(f"starting to watch for files in {datamart_dir/forecast}/")
    observer.start()
    while expected_files:
        time.sleep(1)
    logger.info(
        f"finished collecting files from {datamart_dir/forecast}/ to "
        f"{grib_dir / forecast_date / forecast}/"
    )

    checklist = {forecast: os.fspath(grib_dir / forecast_date / forecast)}
    return checklist


def _calc_expected_files(datamart_dir, forecast, forecast_date, config):
    """
    :param :py:class:`pathlib.Path` datamart_dir:
    :param str forecast:
    :param str forecast_date:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: HRDPS file paths that are expected in the forecast mirror tree
    :rtype: set
    """
    forecast_duration = config["weather"]["download"]["forecast duration"]
    grib_vars = config["weather"]["download"]["grib variables"]
    file_template = config["weather"]["download"]["file template"]
    expected_files = set()
    for hour in range(forecast_duration):
        forecast_hour = f"{hour+1:03d}"
        var_files = {
            file_template.format(
                variable=var, date=forecast_date, forecast=forecast, hour=forecast_hour
            )
            for var in grib_vars
        }
        expected_files.update(
            {
                datamart_dir / forecast / f"{forecast_hour}" / var_file
                for var_file in var_files
            }
        )
    logger.debug(
        f"calculated set of expected file paths for {forecast_date}/{forecast}"
    )
    return expected_files


class _GribFileEventHandler(watchdog.events.FileSystemEventHandler):
    """watchdog file system event handler that detects completion of HRDPS file downloads
    when they move from .grib2.tmp to .grib2, and moves the .grib2 files to the atmospheric
    forcing tree.
    """

    def __init__(self, expected_files, grib_forecast_dir, grp_name):
        super().__init__()
        self.expected_files = expected_files
        self.grib_forecast_dir = grib_forecast_dir
        self.grp_name = grp_name

    def on_moved(self, event):
        super().on_moved(event)
        if Path(event.dest_path) in self.expected_files:
            expected_file = Path(event.dest_path)
            grib_hour_dir = self.grib_forecast_dir / expected_file.parent.stem
            lib.mkdir(grib_hour_dir, logger, grp_name=self.grp_name)
            shutil.move(os.fspath(expected_file), os.fspath(grib_hour_dir))
            logger.debug(f"moved {expected_file} to {grib_hour_dir}/")
            self.expected_files.remove(expected_file)


if __name__ == "__main__":
    main()  # pragma: no cover
