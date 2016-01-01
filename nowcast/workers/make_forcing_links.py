# Copyright 2013-2015 The Salish Sea MEOPAR contributors
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

"""Salish Sea NEMO nowcast forcing files symlink creation worker.
Creates the forcing file symlinks for a nowcast run on the HPC/cloud
facility where the run will be.
executed.
"""
import logging
import os
import shutil

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
        'host_name', help='Name of the host to symlink forcing files on')
    worker.arg_parser.add_argument(
        'run_type', choices=set(
            ('nowcast+', 'forecast2', 'ssh', 'nowcast-green')),
        help='''
        Type of run to symlink files for:
        'nowcast+' means nowcast & 1st forecast runs,
        'forecast2' means 2nd forecast run,
        'ssh' means Neah Bay sea surface height files only (for forecast run).
        'nowcast-green' means nowcast green ocean run,
        ''',
    )
    salishsea_today = arrow.now('Canada/Pacific').floor('day')
    worker.arg_parser.add_argument(
        '--run-date', type=lib.arrow_date,
        default=salishsea_today,
        help='''
        Date of the run to symlink files for; use YYYY-MM-DD format.
        Defaults to {}.
        '''.format(salishsea_today.format('YYYY-MM-DD')),
    )
    worker.arg_parser.add_argument(
        '--shared-storage', action='store_true',
        help='''
        If running on a machine (Salish) that directly accesses
        the repo datafiles, copy the ssh files so that the nowcast
        does not change the files while nowcast-green is running
        ''',
    )
    worker.run(make_forcing_links, success, failure)


def success(parsed_args):
    logger.info(
        '{0.run_type} forcing file links on {0.host_name} created'
        .format(parsed_args), extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'success {.run_type}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.error(
        '{0.run_type} forcing file links creation on {0.host_name} failed'
        .format(parsed_args), extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'failure {.run_type}'.format(parsed_args)
    return msg_type


def make_forcing_links(parsed_args, config, *args):
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    shared_storage = parsed_args.shared_storage
    host_run_config = config['run'][host_name]
    ssh_client, sftp_client = lib.sftp(
        host_name, host_run_config['ssh key name']['nowcast'])
    _make_NeahBay_ssh_links(
        sftp_client, host_run_config, run_date, host_name, shared_storage)
    if run_type == 'ssh':
        sftp_client.close()
        ssh_client.close()
        return {host_name: True}
    _make_runoff_links(sftp_client, host_run_config, run_date, host_name)
    _make_weather_links(
        sftp_client, host_run_config, run_date, host_name, run_type)
    sftp_client.close()
    ssh_client.close()
    return {host_name: True}


def _make_NeahBay_ssh_links(
        sftp_client, host_run_config, run_date, host_name, shared_storage):
    _clear_links(sftp_client, host_run_config, 'open_boundaries/west/ssh/')
    for day in range(-1, 3):
        filename = get_NeahBay_ssh.FILENAME_TMPL.format(
            run_date.replace(days=day).date())
        dir = 'obs' if day == -1 else 'fcst'
        src = os.path.join(host_run_config['ssh_dir'], dir, filename)
        dest = os.path.join(
            host_run_config['nowcast_dir'],
            'open_boundaries/west/ssh/',
            filename)
        if shared_storage:
            shutil.copy2(src, dest)
        else:
            _create_symlink(sftp_client, host_name, src, dest)


def _make_runoff_links(sftp_client, host_run_config, run_date, host_name):
    _clear_links(sftp_client, host_run_config, 'rivers/')
    src = host_run_config['rivers_month.nc']
    dest = os.path.join(
        host_run_config['nowcast_dir'], 'rivers/', os.path.basename(src))
    _create_symlink(sftp_client, host_name, src, dest)
    for tmpl in make_runoff_file.FILENAME_TMPLS.values():
        src = os.path.join(
            host_run_config['rivers_dir'],
            tmpl.format(run_date.replace(days=-1).date())
        )
        for day in range(-1, 3):
            filename = tmpl.format(run_date.replace(days=day).date())
            dest = os.path.join(
                host_run_config['nowcast_dir'], 'rivers/', filename)
            _create_symlink(sftp_client, host_name, src, dest)


def _make_weather_links(
    sftp_client, host_run_config, run_date, host_name, run_type,
):
    _clear_links(sftp_client, host_run_config, 'NEMO-atmos/')
    NEMO_atmos_dir = os.path.join(
        host_run_config['nowcast_dir'], 'NEMO-atmos/')
    for linkfile in 'no_snow.nc weights'.split():
        src = host_run_config[linkfile]
        dest = os.path.join(NEMO_atmos_dir, os.path.basename(src))
        _create_symlink(sftp_client, host_name, src, dest)
    nowcast_runs = {'nowcast+', 'nowcast-green'}
    if run_type in nowcast_runs:
        weather_start = -1
    else:
        weather_start = 0
    for day in range(weather_start, 3):
        filename = grib_to_netcdf.FILENAME_TMPL.format(
            run_date.replace(days=day).date())
        if run_type in nowcast_runs:
            dir = '' if day <= 0 else 'fcst'
        else:
            dir = 'fcst'
        src = os.path.join(host_run_config['weather_dir'], dir, filename)
        dest = os.path.join(NEMO_atmos_dir, filename)
        _create_symlink(sftp_client, host_name, src, dest)


def _clear_links(sftp_client, host_run_config, dir):
    links_dir = os.path.join(host_run_config['nowcast_dir'], dir)
    for linkname in sftp_client.listdir(links_dir):
        sftp_client.unlink(os.path.join(links_dir, linkname))
    logger.debug('{} symlinks cleared'.format(links_dir))


def _create_symlink(sftp_client, host_name, src, dest):
    sftp_client.symlink(src, dest)
    logger.debug(
        '{src} symlinked as {dest} on {host}'
        .format(src=src, dest=dest, host=host_name))


if __name__ == '__main__':
    main()
