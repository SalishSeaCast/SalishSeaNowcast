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
"""Salish Sea FVCOM Vancouver Harbour and Fraser River model worker that
produces river discharges forcing files for the FVCOM model from the Salish Sea NEMO
model runoff forcing files.
"""
import logging
import os
from datetime import timedelta
from pathlib import Path

import OPPTools
import arrow
import numpy
from nemo_nowcast import NowcastWorker

NAME = "make_fvcom_rivers_forcing"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_fvcom_rivers_forcing --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "host_name", help="Name of the host to make rivers forcing files on"
    )
    worker.cli.add_argument(
        "model_config",
        choices={"r12", "x2"},
        help="""
        Model configuration to make rivers forcing file for:
        'r12' means the r12 resolution
        'x2' means the x2 resolution
        """,
    )
    worker.cli.add_argument(
        "run_type",
        choices={"nowcast", "forecast"},
        help="""
        Type of run to make rivers forcing file for:
        'nowcast' means run for present UTC day (after NEMO nowcast run)
        'forecast' means updated forecast run
        (next 36h UTC, after NEMO forecast run)
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Date to make rivers forcing file for.",
    )
    worker.run(make_fvcom_rivers_forcing, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f"FVCOM {parsed_args.model_config} {parsed_args.run_type} run rivers forcing file for "
        f"{parsed_args.run_date.format('YYYY-MM-DD')} "
        f"created on {parsed_args.host_name}"
    )
    msg_type = f"success {parsed_args.model_config} {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f"FVCOM {parsed_args.model_config} {parsed_args.run_type} run rivers forcing file creation "
        f"for {parsed_args.run_date.format('YYYY-MM-DD')} "
        f"failed on {parsed_args.host_name}"
    )
    msg_type = f"failure {parsed_args.model_config} {parsed_args.run_type}"
    return msg_type


def make_fvcom_rivers_forcing(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    model_config = parsed_args.model_config
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    logger.info(
        f"Creating VHFR FVCOM rivers forcing file for {model_config} {run_type} run from "
        f'{run_date.format("YYYY-MM-DD")} NEMO runoff forcing files'
    )
    time_start_offsets = {
        "nowcast": timedelta(hours=0),
        "forecast": timedelta(hours=24),
    }
    time_start = run_date + time_start_offsets[run_type]
    time_end_offsets = {"nowcast": timedelta(hours=24), "forecast": timedelta(hours=60)}
    time_end = run_date + time_end_offsets[run_type]
    nemo_rivers_dir = Path(
        config["vhfr fvcom runs"]["rivers forcing"]["nemo rivers dir"]
    )
    runoff_file_tmpl = config["vhfr fvcom runs"]["rivers forcing"][
        "runoff file template"
    ]
    runoff_day = run_date.shift(days=-1)
    runoff_file = runoff_file_tmpl.format(
        yyyymmdd=f"y{runoff_day.year:04d}m{runoff_day.month:02d}d{runoff_day.day:02d}"
    )
    logger.debug(
        f"creating rivers forcing file for {run_type} for {time_start} to {time_end} "
        f"from {nemo_rivers_dir / runoff_file}"
    )
    time, discharge, temperature = OPPTools.river.nemo_fraser(
        (
            time_start.format("YYYY-MM-DD HH:mm:ss"),
            time_end.format("YYYY-MM-DD HH:mm:ss"),
        ),
        [os.fspath(nemo_rivers_dir / runoff_file)],
        config["vhfr fvcom runs"]["nemo coupling"]["nemo coordinates"],
        config["vhfr fvcom runs"]["rivers forcing"]["temperature climatology"],
    )
    grid_dir = Path(config["vhfr fvcom runs"]["fvcom grid"]["grid dir"])
    fraser_nodes_file = (
        grid_dir
        / config["vhfr fvcom runs"]["fvcom grid"][model_config]["fraser nodes file"]
    )
    river_nodes = numpy.genfromtxt(fraser_nodes_file, dtype=int)
    fvcom_input_dir = Path(config["vhfr fvcom runs"]["input dir"][model_config])
    rivers_file_tmpl = config["vhfr fvcom runs"]["rivers forcing"][
        "rivers file template"
    ]
    rivers_file_date = run_date if run_type == "nowcast" else run_date.shift(days=+1)
    rivers_file = rivers_file_tmpl.format(
        model_config=model_config,
        run_type=run_type,
        yyyymmdd=rivers_file_date.format("YYYYMMDD"),
    )
    OPPTools.fvcomToolbox.generate_riv(
        os.fspath(fvcom_input_dir / rivers_file),
        [t1.strftime("%Y-%m-%d %H:%M:%S") for t1 in time],
        river_nodes,
        OPPTools.river.discharge_split(discharge, len(river_nodes)),
        numpy.tile(temperature[:, None], len(river_nodes)),
        rivName="fraser",
        namelist_file=os.fspath(
            fvcom_input_dir.parent / f"namelist.rivers.{model_config}"
        ),
    )
    logger.info(f"Stored VHFR FVCOM rivers forcing file: {fvcom_input_dir/rivers_file}")
    checklist = {
        run_type: {
            "run date": run_date.format("YYYY-MM-DD"),
            "model config": model_config,
            "rivers forcing file": os.fspath(fvcom_input_dir / rivers_file),
        }
    }
    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
