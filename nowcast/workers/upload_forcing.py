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

from nowcast import lib
from nowcast.nowcast_worker import NowcastWorker
from nowcast.workers import (
    get_NeahBay_ssh,
    grib_to_netcdf,
    make_runoff_file,
)


worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)


def main():
    worker = NowcastWorker(worker_name, description=__doc__)
    worker.arg_parser.add_argument(
        'host_name', help='Name of the host to upload forcing files to')
    worker.arg_parser.add_argument(
        'run_type', choices=set(('nowcast+', 'forecast2', 'ssh')),
        help='''
        Type of run to upload files for:
        'nowcast+' means nowcast & 1st forecast runs,
        'forecast2' means 2nd forecast run,
        'ssh' means Neah Bay sea surface height files only (for forecast run).
        ''',
    )
    salishsea_today = arrow.now('Canada/Pacific').floor('day')
    worker.arg_parser.add_argument(
        '--run-date', type=lib.arrow_date,
        default=salishsea_today,
        help='''
        Date of the run to upload files for; use YYYY-MM-DD format.
        Defaults to {}.
        '''.format(salishsea_today.format('YYYY-MM-DD')),
    )
    worker.run(upload_forcing, success, failure)


def success(parsed_args):
    logger.info(
        '{0.run_type} forcing files upload to {0.host_name} completed'
        .format(parsed_args), extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'success {.run_type}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical(
        '{0.run_type} forcing files upload to {0.host_name} failed'
        .format(parsed_args), extra={
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
    host = config['run'][host_name]
    ssh_client, sftp_client = lib.sftp(
        host_name, host['ssh key name']['nowcast'])
    # Neah Bay sea surface height
    for day in range(-1, 3):
        filename = get_NeahBay_ssh.FILENAME_TMPL.format(
            run_date.replace(days=day).date())
        dest_dir = 'obs' if day == -1 else 'fcst'
        localpath = os.path.join(config['ssh']['ssh_dir'], dest_dir, filename)
        remotepath = os.path.join(host['ssh_dir'], dest_dir, filename)
        try:
            _upload_file(sftp_client, host_name, localpath, remotepath)
        except OSError:
            if dest_dir != 'obs':
                raise
            # obs file does not exist, to create symlink to corresponding
            # forecast file
            fcst = os.path.join(config['ssh']['ssh_dir'], 'fcst', filename)
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
        return {host_name: True}
    # Rivers runoff
    for tmpl in make_runoff_file.FILENAME_TMPLS.values():
        filename = tmpl.format(run_date.replace(days=-1).date())
        localpath = os.path.join(config['rivers']['rivers_dir'], filename)
        remotepath = os.path.join(host['rivers_dir'], filename)
        _upload_file(sftp_client, host_name, localpath, remotepath)
    # Weather
    if run_type == 'nowcast+':
        weather_start = 0
    else:
        weather_start = 1
    for day in range(weather_start, 3):
        filename = grib_to_netcdf.FILENAME_TMPL.format(
            run_date.replace(days=day).date())
        dest_dir = '' if day == 0 else 'fcst'
        localpath = os.path.join(
            config['weather']['ops_dir'], dest_dir, filename)
        remotepath = os.path.join(host['weather_dir'], dest_dir, filename)
        _upload_file(sftp_client, host_name, localpath, remotepath)
    sftp_client.close()
    ssh_client.close()
    return {host_name: True}


def _upload_file(sftp_client, host_name, localpath, remotepath):
    sftp_client.put(localpath, remotepath)
    sftp_client.chmod(remotepath, lib.PERMS_RW_RW_R)
    logger.debug(
        '{local} uploaded to {host} at {remote}'
        .format(local=localpath, host=host_name, remote=remotepath))


if __name__ == '__main__':
    main()
