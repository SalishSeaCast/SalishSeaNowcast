# Copyright 2013-2017 The Salish Sea MEOPAR contributors
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

Create the forcing file symlinks for a nowcast run on the HPC/cloud
facility where the run will be executed.
"""
import logging
import os
import shutil

import arrow
from nemo_nowcast import NowcastWorker

from nowcast import lib


NAME = 'make_forcing_links'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_forcing_links --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name', help='Name of the host to symlink forcing files on')
    worker.cli.add_argument(
        'run_type', choices={'nowcast+', 'forecast2', 'ssh', 'nowcast-green'},
        help='''
        Type of run to symlink files for:
        'nowcast+' means nowcast & 1st forecast runs,
        'forecast2' means 2nd forecast run,
        'ssh' means Neah Bay sea surface height files only (for forecast run).
        'nowcast-green' means nowcast green ocean run,
        ''')
    worker.cli.add_argument(
        '--shared-storage', action='store_true',
        help='''
        If running on a machine (Salish) that directly accesses
        the repo datafiles, copy the forcing files instead of symlinking them
        so that they do not get changed as a result of preparations for faster
        runs on remote hosts
        ''')
    worker.cli.add_date_option(
        '--run-date', default=(arrow.now().floor('day')),
        help='Date of the run to symlink files for.')
    worker.run(make_forcing_links, success, failure)


def success(parsed_args):
    logger.info(
        '{0.run_type} {date} forcing file links on {0.host_name} created'
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
        '{0.run_type} {date} forcing file links creation on {0.host_name} '
        'failed'
        .format(parsed_args, date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
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
    ssh_key = os.path.join(
        os.environ['HOME'], '.ssh',
        config['run']['enabled hosts'][host_name]['ssh key'])
    ssh_client, sftp_client = lib.sftp(host_name, ssh_key)
    _make_NeahBay_ssh_links(
        sftp_client, run_date, config, host_name, shared_storage)
    if run_type == 'ssh':
        sftp_client.close()
        ssh_client.close()
        checklist = {
            host_name: {
                'links': '{0.run_type} {date} ssh'
                         .format(
                            parsed_args,
                            date=parsed_args.run_date.format('YYYY-MM-DD')),
                'run date': parsed_args.run_date.format('YYYY-MM-DD')}}
        return checklist
    _make_runoff_links(sftp_client, run_date, config, host_name)
    _make_weather_links(sftp_client, run_date, config, host_name, run_type)
    _make_live_ocean_links(
        sftp_client, run_date, config, host_name, shared_storage)
    sftp_client.close()
    ssh_client.close()
    checklist = {
        host_name: {
            'links': '{0.run_type} {date} ssh rivers weather LiveOcean '
                     .format(
                        parsed_args,
                        date=parsed_args.run_date.format('YYYY-MM-DD')),
            'run date': parsed_args.run_date.format('YYYY-MM-DD')
        }
    }
    return checklist


def _make_NeahBay_ssh_links(
        sftp_client, run_date, config, host_name, shared_storage,
):
    host_run_config = config['run'][host_name]
    _clear_links(sftp_client, host_run_config, 'open_boundaries/west/ssh/')
    for day in range(-1, 3):
        filename = config['ssh']['file template'].format(
            run_date.replace(days=day).date())
        dir = 'obs' if day == -1 else 'fcst'
        src = os.path.join(host_run_config['forcing']['ssh dir'], dir, filename)
        dest = os.path.join(
            host_run_config['run prep dir'],
            'open_boundaries/west/ssh/',
            filename)
        if shared_storage:
            shutil.copy2(src, dest)
        else:
            _create_symlink(sftp_client, host_name, src, dest)


def _make_runoff_links(sftp_client, run_date, config, host_name):
    host_run_config = config['run'][host_name]
    _clear_links(sftp_client, host_run_config, 'rivers/')
    src = host_run_config['forcing']['rivers_month.nc']
    dest = os.path.join(
        host_run_config['run prep dir'], 'rivers', os.path.basename(src))
    _create_symlink(sftp_client, host_name, src, dest)
    if 'rivers_temp.nc' in host_run_config['forcing']:
        src = host_run_config['forcing']['rivers_temp.nc']
        dest = os.path.join(
            host_run_config['run prep dir'], 'rivers', os.path.basename(src))
        _create_symlink(sftp_client, host_name, src, dest)
    if 'rivers bio dir' in host_run_config['forcing']:
        src = host_run_config['forcing']['rivers bio dir']
        dest = os.path.join(
            host_run_config['run prep dir'], 'rivers', 'bio_climatology')
        _create_symlink(sftp_client, host_name, src, dest)
    for tmpl in config['rivers']['file templates'].values():
        src = os.path.join(
            host_run_config['forcing']['rivers dir'],
            tmpl.format(run_date.replace(days=-1).date())
        )
        for day in range(-1, 3):
            filename = tmpl.format(run_date.replace(days=day).date())
            dest = os.path.join(
                host_run_config['run prep dir'], 'rivers', filename)
            _create_symlink(sftp_client, host_name, src, dest)


def _make_weather_links(sftp_client, run_date, config, host_name, run_type):
    host_run_config = config['run'][host_name]
    _clear_links(sftp_client, host_run_config, 'NEMO-atmos/')
    NEMO_atmos_dir = os.path.join(
        host_run_config['run prep dir'], 'NEMO-atmos/')
    for linkfile in 'no_snow.nc weights'.split():
        src = host_run_config['forcing'][linkfile]
        dest = os.path.join(NEMO_atmos_dir, os.path.basename(src))
        _create_symlink(sftp_client, host_name, src, dest)
    nowcast_runs = {'nowcast+', 'nowcast-green'}
    if run_type in nowcast_runs:
        weather_start = -1
    else:
        weather_start = 0
    for day in range(weather_start, 3):
        filename = config['weather']['file template'].format(
            run_date.replace(days=day).date())
        if run_type in nowcast_runs:
            dir = '' if day <= 0 else 'fcst'
        else:
            dir = 'fcst'
        src = os.path.join(
            host_run_config['forcing']['weather dir'], dir, filename)
        dest = os.path.join(NEMO_atmos_dir, filename)
        _create_symlink(sftp_client, host_name, src, dest)


def _make_live_ocean_links(
        sftp_client, run_date, config, host_name, shared_storage,
):
    host_run_config = config['run'][host_name]
    _clear_links(
        sftp_client, host_run_config, 'open_boundaries/west/LiveOcean/')
    for day in range(-1, 3):
        filename = config['temperature salinity']['file template'].format(
            run_date.replace(days=day).date())
        dir = '' if day <= 0 else 'fcst'
        if day != 2:
            # if day=2, we use the previous day as source
            src = os.path.join(
                host_run_config['forcing']['bc dir'], dir, filename)
        dest = os.path.join(
            host_run_config['run prep dir'],
            'open_boundaries/west/LiveOcean/',
            filename)
        if shared_storage:
            shutil.copy2(src, dest)
        else:
            _create_symlink(sftp_client, host_name, src, dest)


def _clear_links(sftp_client, host_run_config, dir):
    links_dir = os.path.join(host_run_config['run prep dir'], dir)
    logger.debug(links_dir)
    for linkname in sftp_client.listdir(links_dir):
        sftp_client.unlink(os.path.join(links_dir, linkname))
    logger.debug('{} symlinks cleared'.format(links_dir))


def _create_symlink(sftp_client, host_name, src, dest):
    sftp_client.symlink(src, dest)
    logger.debug(
        '{src} symlinked as {dest} on {host}'
        .format(src=src, dest=dest, host=host_name))


if __name__ == '__main__':
    main()  # pragma: no cover
