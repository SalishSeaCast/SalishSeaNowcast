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

"""Salish Sea NEMO nowcast worker that uploads the forcing files
for a nowcast run to the HPC/cloud facility where the run will be
executed assuming that the previous nowcasts were not run there
"""
import argparse
import glob
import logging
import os
import traceback

import arrow
import zmq

from nowcast import lib
from nemo_nowcast import WorkerError


worker_name = lib.get_module_name()

logger = logging.getLogger(worker_name)

context = zmq.Context()


def main():
    # Prepare the worker
    base_parser = lib.basic_arg_parser(
        worker_name, description=__doc__, add_help=False)
    parser = configure_argparser(
        prog=base_parser.prog,
        description=base_parser.description,
        parents=[base_parser],
    )
    parsed_args = parser.parse_args()
    config = lib.load_config(parsed_args.config_file)
    lib.configure_logging(config, logger, parsed_args.debug)
    logger.info('running in process {}'.format(os.getpid()))
    logger.info('read config from {.config_file}'.format(parsed_args))
    lib.install_signal_handlers(logger, context)
    socket = lib.init_zmq_req_rep_worker(context, config, logger)
    # Do the work
    try:
        checklist = upload_all_files(
            parsed_args.host_name, parsed_args.run_date,
            config)
        logger.info(
            'Nowcast ALL files upload to {0.host_name} completed'
            .format(parsed_args), extra={
                'host_name': parsed_args.host_name,
                'date': parsed_args.run_date,
            })
        # Exchange success messages with the nowcast manager process
        lib.tell_manager(
            worker_name, 'success', config, logger, socket, checklist)
    except WorkerError:
        logger.critical(
            'Nowcast ALL files upload to {0.host_name} failed'
            .format(parsed_args), extra={
                'host_name': parsed_args.host_name,
                'date': parsed_args.run_date,
            })
        # Exchange failure messages with the nowcast manager process
        lib.tell_manager(worker_name, 'failure', config, logger, socket)
    except SystemExit:
        # Normal termination
        pass
    except:
        logger.critical('unhandled exception:')
        for line in traceback.format_exc().splitlines():
            logger.error(line)
        # Exchange crash messages with the nowcast manager process
        lib.tell_manager(worker_name, 'crash', config, logger, socket)
    # Finish up
    context.destroy()
    logger.info('task completed; shutting down')


def configure_argparser(prog, description, parents):
    parser = argparse.ArgumentParser(
        prog=prog, description=description, parents=parents)
    parser.add_argument(
        'host_name', help='Name of the host to upload the files to')
    parser.add_argument(
        '--run-date', type=lib.arrow_date, default=arrow.now(),
        help='''
        Date of the run to upload files from;
        use YYYY-MM-DD format.
        Defaults to %(default)s.
        ''',
    )
    return parser


def upload_all_files(host_name, run_date, config):
    host = config['run'][host_name]
    ssh_client, sftp_client = lib.sftp(
        host_name, host['ssh key name']['nowcast'])
    # Neah Bay sea surface height
    for day in range(-1, 2):
        filename = config['ssh']['file template'].format(
            run_date.replace(days=day).date())
        dest_dir = 'obs' if day == -1 else 'fcst'
        localpath = os.path.join(config['ssh']['ssh_dir'], dest_dir, filename)
        remotepath = os.path.join(host['ssh_dir'], dest_dir, filename)
        try:
            upload_file(sftp_client, host_name, localpath, remotepath)
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
                    'host_name': host_name,
                    'date': run_date,
                })
            upload_file(sftp_client, host_name, localpath, remotepath)
    # Rivers runoff
    for tmpl in config['rivers']['file templates'].values():
        filename = tmpl.format(run_date.replace(days=-1).date())
        localpath = os.path.join(config['rivers']['rivers_dir'], filename)
        remotepath = os.path.join(host['rivers_dir'], filename)
        upload_file(sftp_client, host_name, localpath, remotepath)
    # Weather
    for day in range(-1, 2):
        filename = config['weather']['file template'].format(
            run_date.replace(days=day).date())
        dest_dir = '' if day <= 0 else 'fcst'
        localpath = os.path.join(
            config['weather']['ops_dir'], dest_dir, filename)
        remotepath = os.path.join(host['weather_dir'], dest_dir, filename)
        upload_file(sftp_client, host_name, localpath, remotepath)
    # Live Ocean Boundary Conditions
    for day in range(-1, 2):
        filename = config['temperature salinity']['file template'].format(
            run_date.replace(days=day).date())
        dest_dir = '' if day <= 0 else 'fcst'
        localpath = os.path.join(
            config['temperature salinity']['bc dir'], dest_dir, filename)
        remotepath = os.path.join(
            host['forcing']['bc dir'], dest_dir, filename)
        upload_file(sftp_client, host_name, localpath, remotepath)

    # Restart File
    prev_run_id = run_date.replace(days=-1).date()
    prev_run_dir = prev_run_id.strftime('%d%b%y').lower()
    local_dir = os.path.join(
        config['run']['results archive']['nowcast'], prev_run_dir)
    localpath = glob.glob(os.path.join(local_dir, '*restart.nc'))
    filename = os.path.basename(localpath[0])
    remote_dir = os.path.join(host['results']['nowcast'], prev_run_dir)
    remotepath = os.path.join(remote_dir, filename)
    make_remote_directory(sftp_client, host_name, remote_dir)
    upload_file(sftp_client, host_name, localpath[0], remotepath)

    sftp_client.close()
    ssh_client.close()
    return {host_name: True}


def upload_file(sftp_client, host_name, localpath, remotepath):
    sftp_client.put(localpath, remotepath)
    sftp_client.chmod(remotepath, lib.PERMS_RW_RW_R)
    logger.debug(
        '{local} uploaded to {host} at {remote}'
        .format(local=localpath, host=host_name, remote=remotepath))


def make_remote_directory(sftp_client, host_name, remote_dir):
    sftp_client.mkdir(remote_dir, mode=lib.PERMS_RWX_RWX_R_X)
    logger.debug(
        '{remote} directory made on {host}'
        .format(remote=remote_dir, host=host_name))


if __name__ == '__main__':
    main()
