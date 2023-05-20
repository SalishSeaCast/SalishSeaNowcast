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


"""SalishSeaCast worker that calculates NEMO runoff forcing file from day-averaged river
discharge observations (lagged by 1 day) from representative gauged rivers in all watersheds
and fits developed by Susan Allen.
Missing river discharge observations are handled by a scheme of persistence or scaling of
a nearby gauged river, depending on time span of missing observations.
"""
import logging

import arrow
from nemo_nowcast import NowcastWorker

NAME = "make_v202111_runoff_file"
logger = logging.getLogger(NAME)


def main():
    """For command-line usage see:

    :command:`python -m nowcast.workers.make_v202111_runoff_file --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_date_option(
        "--data-date",
        default=arrow.now().floor("day"),
        help="Date to make runoff file for.",
    )
    worker.run(make_v202111_runoff_file, success, failure)
    return worker


def success(parsed_args):
    logger.info(
        f"{parsed_args.data_date.format('YYYY-MM-DD')} runoff file creation completed"
    )
    return "success"


def failure(parsed_args):
    logger.critical(
        f"{parsed_args.data_date.format('YYYY-MM-DD')} runoff file creation failed"
    )
    return "failure"


def make_v202111_runoff_file(parsed_args, config, *args):
    checklist = {}

    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
