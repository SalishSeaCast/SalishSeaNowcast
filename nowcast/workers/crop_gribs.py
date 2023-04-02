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


"""SalishSeaCast worker that loads ECCC MSC 2.5 km rotated lat-lon continental grid HRDPS GRIB2
files, crops them to the subdomain needed for SalishSeaCast NEMO forcing, and writes them to
new GRIB2 files.
"""
# Development notebook:
#
# * https://github.com/SalishSeaCast/analysis-doug/tree/main/notebooks/continental-HRDPS/crop-grib-to-SSC-domain.ipynb.ipynb
import logging

import arrow
from nemo_nowcast import NowcastWorker


NAME = "crop_gribs"
logger = logging.getLogger(NAME)


def main():
    """For command-line usage see:

    :command:`python -m nowcast.workers.crop_gribs --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "forecast",
        choices={"00", "06", "12", "18"},
        help="Name of forecast to crop files in.",
    )
    worker.cli.add_date_option(
        "--fcst-date",
        default=arrow.now().floor("day"),
        help="Forecast date to crop files in.",
    )
    worker.run(crop_gribs, success, failure)
    return worker


def success(parsed_args):
    ymd = parsed_args.fcst_date.format("YYYY-MM-DD")
    logger.info(f"{ymd} {parsed_args.forecast} GRIBs cropping complete")
    msg_type = f"success {parsed_args.forecast}"
    return msg_type


def failure(parsed_args):
    ymd = parsed_args.fcst_date.format("YYYY-MM-DD")
    logger.critical(f"{ymd} {parsed_args.forecast} GRIBs cropping failed")
    msg_type = f"failure {parsed_args.forecast}"
    return msg_type


def crop_gribs(parsed_args, config, *args):
    """Collect weather forecast results from hourly GRIB2 files
    and produces day-long NEMO atmospheric forcing netCDF files.
    """
    checklist = {}
    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
