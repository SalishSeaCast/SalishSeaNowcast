#  Copyright 2013-2019 The Salish Sea MEOPAR contributors
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
"""Salish Sea FVCOM Vancouver Harbour and Fraser River model worker that
produces atmospheric forcing files for the FVCOM model from the ECCC HRDPS
model product.
"""
from datetime import timedelta
import logging
import os
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker
import OPPTools

NAME = "make_fvcom_atmos_forcing"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_fvcom_atmos_forcing --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "run_type",
        choices={"nowcast", "forecast"},
        help="""
        Type of run to make atmospheric forcing file for:
        'nowcast' means run for present UTC day (after NEMO nowcast run),
        'forecast' means updated forecast run (next 36h UTC, after NEMO forecast run)
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Date to make atmospheric forcing file for.",
    )
    worker.run(make_fvcom_atmos_forcing, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f"FVCOM {parsed_args.run_type} run atmospheric forcing file for "
        f'{parsed_args.run_date.format("YYYY-MM-DD")} created',
        extra={
            "run_type": parsed_args.run_type,
            "date": parsed_args.run_date.format("YYYY-MM-DD HH:mm:ss ZZ"),
        },
    )
    msg_type = f"success {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f"FVCOM {parsed_args.run_type} run atmospheric forcing file creation "
        f'for {parsed_args.run_date.format("YYYY-MM-DD")} failed',
        extra={
            "run_type": parsed_args.run_type,
            "date": parsed_args.run_date.format("YYYY-MM-DD HH:mm:ss ZZ"),
        },
    )
    msg_type = f"failure {parsed_args.run_type}"
    return msg_type


def make_fvcom_atmos_forcing(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    checklist = {run_type: {"run date": run_date.format("YYYY-MM-DD")}}
    logger.info(
        f"Creating VHFR FVCOM atmospheric forcing file for {run_type} run from "
        f'{run_date.format("YYYY-MM-DD")} HRDPS GRIB files'
    )
    hrdps_gribs = Path(
        config["vhfr fvcom runs"]["atmospheric forcing"]["hrdps grib dir"]
    )
    hrdps_grib_dirs = (
        hrdps_gribs / run_date.shift(days=-1).format("YYYYMMDD"),
        hrdps_gribs / run_date.format("YYYYMMDD"),
    )
    fvcom_atmos_dir = Path(
        config["vhfr fvcom runs"]["atmospheric forcing"]["fvcom atmos dir"]
    )
    atmos_file_tmpl = config["vhfr fvcom runs"]["atmospheric forcing"][
        "atmos file template"
    ]
    grid_dir = Path(config["vhfr fvcom runs"]["atmospheric forcing"]["fvcom grid dir"])
    fvcom_grid_file = Path(config["vhfr fvcom runs"]["fvcom grid"]["grid file"])
    tri, nodes = OPPTools.fvcomToolbox.readMesh_V3(
        os.fspath(grid_dir / fvcom_grid_file)
    )
    logger.debug(f"read VHFR FVCOM grid mesh from {grid_dir/fvcom_grid_file}")
    x, y = nodes[:, 0], nodes[:, 1]
    time_start_offsets = {
        "nowcast": timedelta(hours=0),
        "forecast": timedelta(hours=24),
    }
    time_start = run_date + time_start_offsets[run_type]
    time_end_offsets = {"nowcast": timedelta(hours=24), "forecast": timedelta(hours=60)}
    time_end = run_date + time_end_offsets[run_type]
    atmos_file_date = run_date if run_type == "nowcast" else run_date.shift(days=+1)
    for atmos_field_type in config["vhfr fvcom runs"]["atmospheric forcing"][
        "field types"
    ]:
        atmos_file = atmos_file_tmpl.format(
            run_type=run_type,
            field_type=atmos_field_type,
            yyyymmdd=atmos_file_date.format("YYYYMMDD"),
        )
        logger.debug(
            f"creating {atmos_field_type} file for {time_start} to {time_end} "
            f"from {hrdps_grib_dirs}"
        )
        OPPTools.atm.create_atm_hrdps(
            atmos_field_type,
            x,
            y,
            tri,
            utmzone=config["vhfr fvcom runs"]["fvcom grid"]["utm zone"],
            tlim=(
                time_start.format("YYYY-MM-DD HH:mm:ss"),
                time_end.format("YYYY-MM-DD HH:mm:ss"),
            ),
            fname=os.fspath(fvcom_atmos_dir / atmos_file),
            hrdps_folder=[f"{hrdps_grib_dir}/" for hrdps_grib_dir in hrdps_grib_dirs],
        )
        logger.info(
            f"Stored VHFR FVCOM atmospheric forcing {atmos_field_type} file: "
            f"{fvcom_atmos_dir/atmos_file}"
        )
        checklist[run_type].update(
            {atmos_field_type: os.fspath(fvcom_atmos_dir / atmos_file)}
        )
    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
