# Copyright 2013-2016 The Salish Sea MEOPAR contributors
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

import arrow
from nemo_nowcast import NowcastWorker

from nowcast import lib
from nowcast.workers import grib_to_netcdf


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
        'host_name', help='Name of the host to upload forcing files to')
    worker.cli.add_argument(
        'run_type', choices={'nowcast+', 'forecast2', 'ssh'},
        help='''
        Type of run to upload files for:
        'nowcast+' means nowcast & 1st forecast runs,
        'forecast2' means 2nd forecast run,
        'ssh' means Neah Bay sea surface height files only (for forecast run).
        ''',
    )
    worker.cli.add_date_option(
        '--run-date', default=arrow.now().floor('day'),
        help='Date of the run to upload files for.')
    worker.run(upload_forcing, success, failure)


def success(parsed_args):
    logger.info(
        '{0.run_type} {date} forcing files upload to {0.host_name} completed'
        .format(parsed_args, date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'success {.run_type}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical(
        '{0.run_type} {date} forcing files upload to {0.host_name} failed'
        .format(parsed_args, date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'failure {.run_type}'.format(parsed_args)
    return msg_type


def upload_forcing(parsed_args, config, *args):
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    ssh_key = os.path.join(
        os.environ['HOME'], '.ssh',
        config['run']['enabled hosts'][host_name]['ssh key'])
    host_run_config = config['run'][host_name]
    ssh_client, sftp_client = lib.sftp(host_name, ssh_key)
    # Neah Bay sea surface height
    for day in range(-1, 3):
        filename = config['ssh']['file template'].format(
            run_date.replace(days=day).date())
        dest_dir = 'obs' if day == -1 else 'fcst'
        localpath = os.path.join(config['ssh']['ssh dir'], dest_dir, filename)
        remotepath = os.path.join(
            host_run_config['forcing']['ssh dir'], dest_dir, filename)
        try:
            _upload_file(sftp_client, host_name, localpath, remotepath)
        except OSError:
            if dest_dir != 'obs':
                raise
            # obs file does not exist, to create symlink to corresponding
            # forecast file
            fcst = os.path.join(config['ssh']['ssh dir'], 'fcst', filename)
            os.symlink(fcst, localpath)
            logger.warning(
                'ssh obs file not found; created symlink to {}'.format(fcst),
                extra={
                    'run_type': run_type,
                    'host_name': host_name,
                    'date': run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
                })
            _upload_file(sftp_client, host_name, localpath, remotepath)
    if run_type == 'ssh':
        sftp_client.close()
        ssh_client.close()
        checklist = {
            host_name: '{0.run_type} {date} ssh'
            .format(
                parsed_args,
                date=parsed_args.run_date.format('YYYY-MM-DD'))}
        return checklist
    # Rivers runoff
    for tmpl in config['rivers']['file templates'].values():
        filename = tmpl.format(run_date.replace(days=-1).date())
        localpath = os.path.join(config['rivers']['rivers dir'], filename)
        remotepath = os.path.join(
            host_run_config['forcing']['rivers dir'], filename)
        _upload_file(sftp_client, host_name, localpath, remotepath)
    # Weather
    if run_type == 'nowcast+':
        weather_start = 0
    else:
        weather_start = 1
    for day in range(weather_start, 3):
        filename = config['weather']['file template'].format(
            run_date.replace(days=day).date())
        dest_dir = '' if day == 0 else 'fcst'
        localpath = os.path.join(
            config['weather']['ops dir'], dest_dir, filename)
        remotepath = os.path.join(
            host_run_config['forcing']['weather dir'], dest_dir, filename)
        _upload_file(sftp_client, host_name, localpath, remotepath)
    sftp_client.close()
    ssh_client.close()
    checklist = {
        host_name: '{0.run_type} {date} ssh rivers weather'
        .format(parsed_args, date=parsed_args.run_date.format('YYYY-MM-DD'))}
    return checklist


def _upload_file(sftp_client, host_name, localpath, remotepath):
    sftp_client.put(localpath, remotepath)
    sftp_client.chmod(remotepath, lib.PERMS_RW_RW_R)
    logger.debug(
        '{local} uploaded to {host} at {remote}'
        .format(local=localpath, host=host_name, remote=remotepath))


if __name__ == '__main__':
    main()  # pragma: no cover
