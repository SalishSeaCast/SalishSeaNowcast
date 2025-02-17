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
"""SalishSeaCast nowcast worker that produces hourly temperature and salinity
boundary conditions files for the SalishSeaCast NEMO model western (Juan de Fuca)
open boundary from the University of Washington Live Ocean model forecast
product.
"""
import logging
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker
from salishsea_tools import LiveOcean_parameters
from salishsea_tools.LiveOcean_BCs import create_LiveOcean_TS_BCs

NAME = "make_live_ocean_files"
logger = logging.getLogger(NAME)


def main():
    """For command-line usage see:

    :command:`python -m nowcast.workers.make_live_ocean_files -h`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="""
        Date of Live Ocean forecast product to produce files from.
        """,
    )
    worker.run(make_live_ocean_files, success, failure)
    return worker


def success(parsed_args):
    ymd = parsed_args.run_date.format("YYYY-MM-DD")
    logger.info(f"{ymd} Live Ocean western boundary conditions files created")
    msg_type = "success"
    return msg_type


def failure(parsed_args):
    ymd = parsed_args.run_date.format("YYYY-MM-DD")
    logger.critical(
        f"{ymd} Live Ocean western boundary conditions files preparation failed"
    )
    msg_type = "failure"
    return msg_type


def make_live_ocean_files(parsed_args, config, *args):
    ymd = parsed_args.run_date.format("YYYY-MM-DD")
    logger.info(
        f"Creating T&S western boundary conditions file from {ymd} Live Ocean run"
    )
    bc_dir = Path(config["temperature salinity"]["bc dir"])
    file_template = config["temperature salinity"]["file template"]
    bc_filepath = bc_dir / file_template.format(parsed_args.run_date.datetime)
    if bc_filepath.is_symlink():
        bc_filepath.unlink()
    meshfilename = Path(config["temperature salinity"]["mesh mask"])
    download_dir = Path(config["temperature salinity"]["download"]["dest dir"])
    LO_to_SSC_parameters = LiveOcean_parameters.set_parameters(
        config["temperature salinity"]["parameter set"]
    )
    filepath = create_LiveOcean_TS_BCs(
        ymd,
        file_template=file_template,
        meshfilename=meshfilename,
        bc_dir=bc_dir,
        LO_dir=download_dir,
        LO_to_SSC_parameters=LO_to_SSC_parameters,
    )
    logger.info(f"Stored T&S western boundary conditions file: {filepath}")
    checklist = {"temperature & salinity": filepath}
    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
