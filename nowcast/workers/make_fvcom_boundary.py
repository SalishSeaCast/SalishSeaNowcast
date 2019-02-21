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
produces boundary condition files for the FVCOM model open boundary in the
Strait of Georgia from the Salish Sea NEMO model results.
"""
from datetime import timedelta
import logging
import os
from pathlib import Path
import shutil

import arrow
from nemo_nowcast import NowcastWorker
import OPPTools

NAME = "make_fvcom_boundary"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_fvcom_boundary --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "host_name", help="Name of the host to make boundary files on"
    )
    worker.cli.add_argument(
        "model_config",
        choices={"r12", "x2"},
        help="""
        Model configuration to make boundary file for:
        'r12' means the r12 resolution
        'x2' means the x2 resolution
        """,
    )
    worker.cli.add_argument(
        "run_type",
        choices={"nowcast", "forecast"},
        help="""
        Type of run to make boundary file for:
        'nowcast' means run for present UTC day (after NEMO nowcast run)
        'forecast' means updated forecast run 
        (next 36h UTC, after NEMO forecast run)
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Date to make boundary file for.",
    )
    worker.run(make_fvcom_boundary, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f"FVCOM {parsed_args.model_config} {parsed_args.run_type} run boundary condition "
        f'file for {parsed_args.run_date.format("YYYY-MM-DD")} '
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
        f"FVCOM {parsed_args.model_config} {parsed_args.run_type} run boundary condition "
        f'file creation for {parsed_args.run_date.format("YYYY-MM-DD")} '
        f"failed on {parsed_args.host_name}"
    )
    msg_type = f"failure {parsed_args.model_config} {parsed_args.run_type}"
    return msg_type


def make_fvcom_boundary(parsed_args, config, *args):
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
        f"Creating VHFR FVCOM open boundary file for {model_config} {run_type} run from "
        f'{run_date.format("YYYY-MM-DD")} NEMO run'
    )
    fvcom_input_dir = Path(config["vhfr fvcom runs"]["input dir"])
    try:
        shutil.rmtree(fvcom_input_dir)
    except FileNotFoundError:
        # input/ directory doesn't exist, and that's what we wanted
        pass
    fvcom_input_dir.mkdir()
    bdy_file_tmpl = config["vhfr fvcom runs"]["nemo coupling"]["boundary file template"]
    grid_dir = Path(config["vhfr fvcom runs"]["fvcom grid"]["grid dir"])
    fvcom_grid_file = Path(
        config["vhfr fvcom runs"]["fvcom grid"][model_config]["grid file"]
    )
    fvcom_depths_file = Path(
        config["vhfr fvcom runs"]["fvcom grid"][model_config]["depths file"]
    )
    fvcom_sigma_file = Path(
        config["vhfr fvcom runs"]["fvcom grid"][model_config]["sigma file"]
    )
    coupling_dir = Path(config["vhfr fvcom runs"]["nemo coupling"]["coupling dir"])
    fvcom_nest_indices_file = Path(
        config["vhfr fvcom runs"]["nemo coupling"][model_config][
            "fvcom nest indices file"
        ]
    )
    fvcom_nest_ref_line_file = Path(
        config["vhfr fvcom runs"]["nemo coupling"][model_config][
            "fvcom nest ref line file"
        ]
    )
    (
        x,
        y,
        z,
        tri,
        nsiglev,
        siglev,
        nsiglay,
        siglay,
        nemo_lon,
        nemo_lat,
        e1t,
        e2t,
        e3u_0,
        e3v_0,
        gdept_0,
        gdepw_0,
        gdepu,
        gdepv,
        tmask,
        umask,
        vmask,
        gdept_1d,
        nemo_h,
    ) = OPPTools.nesting.read_metrics(
        fgrd=os.fspath(grid_dir / fvcom_grid_file),
        fbathy=os.fspath(grid_dir / fvcom_depths_file),
        fsigma=os.fspath(grid_dir / fvcom_sigma_file),
        fnemocoord=(config["vhfr fvcom runs"]["nemo coupling"]["nemo coordinates"]),
        fnemomask=config["vhfr fvcom runs"]["nemo coupling"]["nemo mesh mask"],
        fnemobathy=(config["vhfr fvcom runs"]["nemo coupling"]["nemo bathymetry"]),
        nemo_cut_i=(config["vhfr fvcom runs"]["nemo coupling"]["nemo cut i range"]),
        nemo_cut_j=(config["vhfr fvcom runs"]["nemo coupling"]["nemo cut j range"]),
    )
    inest, xb, yb = OPPTools.nesting.read_nesting(
        fnest=os.fspath(coupling_dir / fvcom_nest_indices_file),
        frefline=os.fspath(coupling_dir / fvcom_nest_ref_line_file),
    )
    time_start_offsets = {
        "nowcast": timedelta(hours=0),
        "forecast": timedelta(hours=24),
    }
    time_start = run_date + time_start_offsets[run_type]
    time_end_offsets = {"nowcast": timedelta(hours=24), "forecast": timedelta(hours=60)}
    time_end = run_date + time_end_offsets[run_type]
    nemo_files_list = [
        os.path.join(
            config["vhfr fvcom runs"]["run types"]["nowcast"]["nemo boundary results"],
            run_date.shift(days=-1).format("DDMMMYY").lower(),
            "FVCOM_T.nc",
        ),
        os.path.join(
            config["vhfr fvcom runs"]["run types"]["nowcast"]["nemo boundary results"],
            run_date.format("DDMMMYY").lower(),
            "FVCOM_T.nc",
        ),
    ]
    if run_type == "forecast":
        nemo_files_list.append(
            os.path.join(
                config["vhfr fvcom runs"]["run types"]["forecast"][
                    "nemo boundary results"
                ],
                run_date.format("DDMMMYY").lower(),
                "FVCOM_T.nc",
            )
        )
    bdy_file_date = run_date if run_type == "nowcast" else run_date.shift(days=+1)
    bdy_file = bdy_file_tmpl.format(
        model_config=model_config,
        run_type=run_type,
        yyyymmdd=bdy_file_date.format("YYYYMMDD"),
    )
    OPPTools.nesting.make_type3_nesting_file2(
        fout=os.fspath(fvcom_input_dir / bdy_file),
        x=x,
        y=y,
        z=z,
        tri=tri,
        nsiglev=nsiglev,
        siglev=siglev,
        nsiglay=nsiglay,
        siglay=siglay,
        utmzone=config["vhfr fvcom runs"]["fvcom grid"]["utm zone"],
        inest=inest,
        xb=xb,
        yb=yb,
        rwidth=(config["vhfr fvcom runs"]["nemo coupling"]["transition zone width"]),
        dl=config["vhfr fvcom runs"]["nemo coupling"]["tanh dl"],
        du=config["vhfr fvcom runs"]["nemo coupling"]["tanh du"],
        nemo_lon=nemo_lon,
        nemo_lat=nemo_lat,
        e1t=e1t,
        e2t=e2t,
        e3u_0=e3u_0,
        e3v_0=e3v_0,
        nemo_file_list=nemo_files_list,
        time_start=time_start.format("YYYY-MM-DD HH:mm:ss"),
        time_end=time_end.format("YYYY-MM-DD HH:mm:ss"),
        opt="BRCL",
        gdept_0=gdept_0,
        gdepw_0=gdepw_0,
        gdepu=gdepu,
        gdepv=gdepv,
        tmask=tmask,
        umask=umask,
        vmask=vmask,
        u_name="uvelocity",
        v_name="vvelocity",
        w_name="wvelocity",
        t_name="cons_temp",
        s_name="ref_salinity",
    )
    logger.info(f"Stored VHFR FVCOM open boundary file: {fvcom_input_dir/bdy_file}")
    checklist = {
        run_type: {
            "run date": run_date.format("YYYY-MM-DD"),
            "model config": model_config,
            "open boundary file": os.fspath(fvcom_input_dir / bdy_file),
        }
    }
    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
