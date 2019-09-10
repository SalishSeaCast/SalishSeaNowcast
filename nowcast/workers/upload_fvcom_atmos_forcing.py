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
"""SalishSeaCast FVCOM Vancouver Harbour and Fraser River model worker that
uploads atmospheric forcing files for the FVCOM model to the compute host.
"""
import logging
import os
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker

from nowcast import ssh_sftp

NAME = "upload_fvcom_atmos_forcing"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.upload_fvcom_atmos_forcing --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "host_name", help="Name of the host to upload atmospheric forcing files to"
    )
    worker.cli.add_argument(
        "model_config",
        choices={"r12", "x2"},
        help="""
        Model configuration to upload atmospheric forcing files for:
        'r12' means the r12 resolution
        'x2' means the x2 resolution
        """,
    )
    worker.cli.add_argument(
        "run_type",
        choices={"nowcast", "forecast"},
        help="""
        Type of run to upload atmospheric forcing files for:
        'nowcast' means run for present UTC day (after NEMO nowcast run),
        'forecast' means updated forecast run (next 36h UTC, after NEMO forecast run)
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Date to upload atmospheric forcing file for.",
    )
    worker.run(upload_fvcom_atmos_forcing, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f"FVCOM {parsed_args.model_config} {parsed_args.run_type} run atmospheric forcing files "
        f'for {parsed_args.run_date.format("YYYY-MM-DD")} uploaded to {parsed_args.host_name}'
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
        f"FVCOM {parsed_args.model_config} {parsed_args.run_type} run atmospheric forcing files "
        f'upload for {parsed_args.run_date.format("YYYY-MM-DD")} '
        f"failed on {parsed_args.host_name}"
    )
    msg_type = f"failure {parsed_args.model_config} {parsed_args.run_type}"
    return msg_type


def upload_fvcom_atmos_forcing(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    model_config = parsed_args.model_config
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    checklist = {
        host_name: {
            parsed_args.run_type: {
                "run date": f'{parsed_args.run_date.format("YYYY-MM-DD")}',
                "model config": model_config,
                "files": [],
            }
        }
    }
    logger.info(
        f"Uploading VHFR FVCOM atmospheric forcing files for "
        f'{run_date.format("YYYY-MM-DD")} {parsed_args.model_config} {parsed_args.run_type} '
        f"run to {host_name}"
    )
    fvcom_atmos_dir = Path(
        config["vhfr fvcom runs"]["atmospheric forcing"]["fvcom atmos dir"]
    )
    atmos_file_tmpl = config["vhfr fvcom runs"]["atmospheric forcing"][
        "atmos file template"
    ]
    atmos_file_date = run_date if run_type == "nowcast" else run_date.shift(days=+1)
    for atmos_field_type in config["vhfr fvcom runs"]["atmospheric forcing"][
        "field types"
    ]:
        atmos_file = atmos_file_tmpl.format(
            model_config=model_config,
            run_type=run_type,
            field_type=atmos_field_type,
            yyyymmdd=atmos_file_date.format("YYYYMMDD"),
        )
        fvcom_input_dir = Path(config["vhfr fvcom runs"]["input dir"][model_config])
        ssh_key = Path(os.environ["HOME"], ".ssh", config["vhfr fvcom runs"]["ssh key"])
        ssh_client, sftp_client = ssh_sftp.sftp(host_name, ssh_key)
        ssh_sftp.upload_file(
            sftp_client,
            host_name,
            fvcom_atmos_dir / atmos_file,
            fvcom_input_dir / atmos_file,
            logger,
        )
        sftp_client.close()
        ssh_client.close()
        logger.debug(
            f"Uploaded {fvcom_atmos_dir/atmos_file} to "
            f"{host_name}:{fvcom_input_dir/atmos_file}"
        )
        checklist[host_name][parsed_args.run_type]["files"].append(atmos_file)
    return checklist


if __name__ == "__main__":
    main()  # pragma: no cover
