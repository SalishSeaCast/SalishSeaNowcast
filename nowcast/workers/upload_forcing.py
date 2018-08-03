# Copyright 2013-2018 The Salish Sea MEOPAR contributors
# and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Salish Sea NEMO nowcast upload forcing files worker.

Upload the forcing files for a nowcast or forecast run to the HPC/cloud
facility where the run will be executed.
"""
import logging
import os
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker

from nowcast import ssh_sftp

NAME = 'upload_forcing'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.upload_forcing --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name', help='Name of the host to upload forcing files to'
    )
    worker.cli.add_argument(
        'run_type',
        choices={'nowcast+', 'forecast2', 'ssh', 'turbidity'},
        help='''
        Type of run to upload files for:
        'nowcast+' means nowcast & 1st forecast runs,
        'forecast2' means 2nd forecast run,
        'ssh' means Neah Bay sea surface height files only (for forecast run),
        'turbidity' means Fraser River turbidity file only 
        (for nowcast-green run).
        ''',
    )
    worker.cli.add_date_option(
        '--run-date',
        default=arrow.now().floor('day'),
        help='Date of the run to upload files for.'
    )
    worker.run(upload_forcing, success, failure)


def success(parsed_args):
    logger.info(
        f'{parsed_args.run_type} {parsed_args.run_date.format("YYYY-MM-DD")} '
        f'forcing files upload to {parsed_args.host_name} completed',
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = f'success {parsed_args.run_type}'
    return msg_type


def failure(parsed_args):
    logger.critical(
        f'{parsed_args.run_type} {parsed_args.run_date.format("YYYY-MM-DD")} '
        f'forcing files upload to {parsed_args.host_name} failed',
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = f'failure {parsed_args.run_type}'
    return msg_type


def upload_forcing(parsed_args, config, *args):
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    ssh_key = Path(
        os.environ['HOME'], '.ssh',
        config['run']['enabled hosts'][host_name]['ssh key']
    )
    host_config = config['run']['enabled hosts'][host_name]
    ssh_client, sftp_client = ssh_sftp.sftp(host_name, os.fspath(ssh_key))
    # Neah Bay sea surface height
    _upload_ssh_files(
        sftp_client, run_type, run_date, config, host_name, host_config
    )
    if run_type == 'ssh':
        sftp_client.close()
        ssh_client.close()
        checklist = {
            host_name:
                f'{parsed_args.run_type} '
                f'{parsed_args.run_date.format("YYYY-MM-DD")} ssh'
        }
        return checklist
    # Rivers turbidity and runoff
    if run_type == 'turbidity':
        _upload_fraser_turbidity_file(
            sftp_client, run_date, config, host_name, host_config
        )
        sftp_client.close()
        ssh_client.close()
        checklist = {
            host_name:
                f'{parsed_args.run_type} '
                f'{parsed_args.run_date.format("YYYY-MM-DD")} turbidity'
        }
        return checklist
    _upload_river_runoff_files(
        sftp_client, run_date, config, host_name, host_config
    )
    # Weather
    _upload_weather(
        sftp_client, run_type, run_date, config, host_name, host_config
    )
    # Live Ocean Boundary Conditions
    _upload_live_ocean_files(
        sftp_client, run_type, run_date, config, host_name, host_config
    )
    sftp_client.close()
    ssh_client.close()
    checklist = {
        host_name:
            f'{parsed_args.run_type} '
            f'{parsed_args.run_date.format("YYYY-MM-DD")} '
            f'ssh  rivers  weather  boundary conditions'
    }
    return checklist


def _upload_ssh_files(
    sftp_client, run_type, run_date, config, host_name, host_config
):
    for day in range(-1, 3):
        filename = config['ssh']['file template'].format(
            run_date.shift(days=day).date()
        )
        dest_dir = 'obs' if day == -1 else 'fcst'
        localpath = Path(config['ssh']['ssh dir'], dest_dir, filename)
        remotepath = Path(
            host_config['forcing']['ssh dir'], dest_dir, filename
        )
        try:
            ssh_sftp.upload_file(
                sftp_client, host_name, localpath, remotepath, logger
            )
        except FileNotFoundError:
            if dest_dir != 'obs':
                raise
            # obs file does not exist, so create symlink to corresponding
            # forecast file
            fcst = Path(config['ssh']['ssh dir'], 'fcst', filename)
            fcst.symlink_to(localpath)
            logger.warning(
                f'ssh obs file not found; created symlink to {fcst}',
                extra={
                    'run_type': run_type,
                    'host_name': host_name,
                    'date': run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
                }
            )
            ssh_sftp.upload_file(
                sftp_client, host_name, localpath, remotepath, logger
            )


def _upload_fraser_turbidity_file(
    sftp_client, run_date, config, host_name, host_config
):
    filename_tmpl = config['rivers']['turbidity']['file template']
    filename = filename_tmpl.format(run_date.date())
    localpath = Path(config['rivers']['turbidity']['forcing dir'], filename)
    remotepath = Path(host_config['forcing']['Fraser turbidity dir'], filename)
    try:
        ssh_sftp.upload_file(
            sftp_client, host_name, localpath, remotepath, logger
        )
    except FileNotFoundError:
        # turbidity file does not exist, so create symlink to persist
        # previous day's file
        prev_day_fn = filename_tmpl.format(run_date.shift(days=-1).date())
        try:
            localpath.symlink_to(localpath.with_name(prev_day_fn))
        except FileExistsError:
            # This probably happens due to a race condition when 2 or more
            # upload_forcing workers are running concurrently; see
            # https://bitbucket.org/salishsea/salishseanowcast/issues/57
            # So, we assume that another instance created the symlink, and
            # don't worry.
            pass
        logger.critical(
            f'Fraser River turbidity forcing file not found; '
            f'created symlink to {localpath.with_name(prev_day_fn)}',
            extra={
                'run_type': 'turbidity',
                'host_name': host_name,
                'date': run_date.format('YYYY-MM-DD HH:mm:ss ZZ')
            }
        )
        ssh_sftp.upload_file(
            sftp_client, host_name, localpath, remotepath, logger
        )


def _upload_river_runoff_files(
    sftp_client, run_date, config, host_name, host_config
):
    for tmpl in config['rivers']['file templates'].values():
        filename = tmpl.format(run_date.shift(days=-1).date())
        localpath = Path(config['rivers']['rivers dir'], filename)
        remotepath = Path(host_config['forcing']['rivers dir'], filename)
        ssh_sftp.upload_file(
            sftp_client, host_name, localpath, remotepath, logger
        )


def _upload_weather(
    sftp_client, run_type, run_date, config, host_name, host_config
):
    if run_type == 'nowcast+':
        weather_start = 0
    else:
        weather_start = 1
    for day in range(weather_start, 3):
        filename = config['weather']['file template'].format(
            run_date.shift(days=day).date()
        )
        dest_dir = '' if day == 0 else 'fcst'
        localpath = Path(config['weather']['ops dir'], dest_dir, filename)
        remotepath = Path(
            host_config['forcing']['weather dir'], dest_dir, filename
        )
        ssh_sftp.upload_file(
            sftp_client, host_name, localpath, remotepath, logger
        )


def _upload_live_ocean_files(
    sftp_client, run_type, run_date, config, host_name, host_config
):
    filename = config['temperature salinity']['file template'].format(
        run_date.date()
    )
    localpath = Path(config['temperature salinity']['bc dir'], filename)
    remotepath = (Path(host_config['forcing']['bc dir'], filename))
    try:
        ssh_sftp.upload_file(
            sftp_client, host_name, localpath, remotepath, logger
        )
    except FileNotFoundError:
        # Boundary condition file does not exist, so create symlink to
        # persist previous day's file.
        # This happens as a matter of course for forecast2 runs because
        # they run before the day's LiveOcean product is available,
        # but for other run types it is a cause for concern.
        prev_day_fn = (
            config['temperature salinity']['file template'].format(
                run_date.shift(days=-1).date()
            )
        )
        localpath.symlink_to(localpath.with_name(prev_day_fn))
        logging_level = (
            logging.INFO if run_type == 'forecast2' else logging.CRITICAL
        )
        logger.log(
            logging_level,
            f'LiveOcean boundary conditions file not found; '
            f'created symlink to {localpath.with_name(prev_day_fn)}',
            extra={
                'run_type': run_type,
                'host_name': host_name,
                'date': run_date.format('YYYY-MM-DD HH:mm:ss ZZ')
            }
        )
        ssh_sftp.upload_file(
            sftp_client, host_name, localpath, remotepath, logger
        )


if __name__ == '__main__':
    main()  # pragma: no cover
