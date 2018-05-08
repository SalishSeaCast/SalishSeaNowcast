# Copyright 2013-2018 The Salish Sea MEOPAR Contributors
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
"""SalishSeaCast worker that monitors and reports on the progress of a
NEMO AGRIF run on an HPC cluster that uses the TORQUE/MOAB scheduler.
"""
import logging
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace

import arrow
import f90nml
from nemo_nowcast import NowcastWorker, WorkerError

from nowcast import ssh_sftp

NAME = 'watch_NEMO_agrif'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.watch_NEMO_agrif --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name', help='Name of the host to monitor the run on'
    )
    worker.cli.add_argument(
        'job_id', help='Job identifier of the job to monitor'
    )
    worker.run(watch_NEMO_agrif, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f'NEMO AGRIF run {parsed_args.job_id} on {parsed_args.host_name} '
        f'completed',
        extra={
            'run_type': 'hindcast',
            'host_name': parsed_args.host_name,
            'job_id': parsed_args.job_id,
        }
    )
    msg_type = 'success'
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f'NEMO hindcast run {parsed_args.job_id} on {parsed_args.host_name} '
        f'watcher failed',
        extra={
            'run_type': 'hindcast',
            'host_name': parsed_args.host_name,
            'job_id': parsed_args.job_id,
        }
    )
    msg_type = 'failure'
    return msg_type


def watch_NEMO_agrif(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    job_id = parsed_args.job_id.split('.', 1)[0]
    ssh_key = Path(
        os.environ['HOME'], '.ssh',
        config['run']['enabled hosts'][host_name]['ssh key']
    )
    scratch_dir = Path(
        config['run']['enabled hosts'][host_name]['scratch dir']
    )
    try:
        ssh_client, sftp_client = ssh_sftp.sftp(host_name, os.fspath(ssh_key))
        run_id = _get_run_id(ssh_client, host_name, job_id)
        while _is_queued(ssh_client, host_name, job_id, run_id):
            time.sleep(60)
        tmp_run_dir = _get_tmp_run_dir(
            ssh_client, host_name, scratch_dir, run_id
        )
        run_info = _get_run_info(sftp_client, host_name, tmp_run_dir)
        while _is_running(
            ssh_client, host_name, job_id, run_id, tmp_run_dir, run_info
        ):
            time.sleep(60 * 5)
    finally:
        sftp_client.close()
        ssh_client.close()
    checklist = {
        'smelt-agrif': {
            'host': host_name,
            'job id': job_id,
            'run date': arrow.get(run_id[:7], 'DDMMMYY').format('YYYY-MM-DD'),
            'completed': True,
        }
    }
    return checklist


def _get_run_id(ssh_client, host_name, job_id):
    """
    :param :py:class:`paramiko.client.SSHClient` ssh_client:
    :param str host_name:
    :param str job_id:

    :return: run id
    :rtype: str
    """
    queue_info = _get_queue_info(ssh_client, host_name, job_id)
    for line in queue_info.splitlines():
        if line.strip().startswith('Job_Name'):
            run_id = line.split()[2]
            logger.info(f'watching {run_id} job {job_id} on {host_name}')
            return run_id


def _is_queued(ssh_client, host_name, job_id, run_id):
    """
    :param :py:class:`paramiko.client.SSHClient` ssh_client:
    :param str host_name:
    :param str job_id:
    :param str run_id:

    :return: Flag indicating whether or not run is queued
    :rtype: boolean
    """
    queue_info = _get_queue_info(ssh_client, host_name, job_id)
    state = 'UNKNOWN'
    for line in queue_info.splitlines():
        if line.strip().startswith('job_state'):
            state = line.split()[2]
            break
    if state != 'Q':
        return False
    msg = f'{run_id} job {job_id} is queued on {host_name}'
    logger.info(msg)
    return True


def _is_running(ssh_client, host_name, job_id, run_id, tmp_run_dir, run_info):
    """
    :param :py:class:`paramiko.client.SSHClient` ssh_client:
    :param str host_name:
    :param str job_id:
    :param str run_id:
    :param :py:class:`pathlib.Path` tmp_run_dir:
    :param :py:class:`types.SimpleNamespace` run_info:

    :return: Flag indicating whether or not run is executing
    :rtype: boolean
    """
    try:
        queue_info = _get_queue_info(ssh_client, host_name, job_id)
    except WorkerError:
        # Job has disappeared from queue, so it has finished, crashed, or
        # been terminated by the resource manager
        return False
    state = 'UNKNOWN'
    for line in queue_info.splitlines():
        if line.strip().startswith('job_state'):
            state = line.split()[2]
            break
    if state != 'R':
        return False
    try:
        stdout = ssh_sftp.ssh_exec_command(
            ssh_client, f'cat {tmp_run_dir}/time.step', host_name, logger
        )
    except ssh_sftp.SSHCommandError:
        # time.step file not found or empty; assume that run is young and it
        # hasn't been created yet, or has finished and it has been
        # moved to the results directory
        logger.info(
            f'{run_id} on {host_name}: time.step not found; '
            f'continuing to watch...'
        )
        return True
    time_step = int(stdout.splitlines()[0].strip())
    model_seconds = (time_step - run_info.it000) * run_info.rdt
    model_time = (
        run_info.date0.replace(seconds=model_seconds
                               ).format('YYYY-MM-DD HH:mm:ss UTC')
    )
    fraction_done = ((time_step - run_info.it000) /
                     (run_info.itend - run_info.it000))
    logger.info(
        f'{run_id} on {host_name}: timestep: '
        f'{time_step} = {model_time}, {fraction_done:.1%} complete'
    )
    return True


def _get_queue_info(ssh_client, host_name, job_id):
    """
    :param :py:class:`paramiko.client.SSHClient` ssh_client:
    :param str host_name:
    :param str job_id:

    :return: Output from TORQUE/MOAB qstat command that describes the run's
             state
    :rtype: str
    """
    try:
        stdout = ssh_sftp.ssh_exec_command(
            ssh_client, f'/global/system/torque/bin/qstat -f -1 {job_id}',
            host_name, logger
        )
    except ssh_sftp.SSHCommandError as exc:
        for line in exc.stderr.splitlines():
            logger.error(line)
        raise WorkerError
    return stdout


def _get_tmp_run_dir(ssh_client, host_name, scratch_dir, run_id):
    """
    :param :py:class:`paramiko.client.SSHClient` ssh_client:
    :param str host_name:
    :param :py:class:`pathlib.Path` scratch_dir:
    :param str run_id:

    :return: Temporary run directory
    :rtype: :py:class:`pathlib.Path`
    """
    stdout = ssh_sftp.ssh_exec_command(
        ssh_client, f'ls -d {scratch_dir/run_id}_*', host_name, logger
    )
    tmp_run_dir = Path(stdout.splitlines()[0].strip())
    logger.debug(f'found tmp run dir: {host_name}:{tmp_run_dir}')
    return tmp_run_dir


def _get_run_info(sftp_client, host_name, tmp_run_dir):
    """
    :param :py:class:`paramiko.sftp_client.SFTPClient` sftp_client:
    :param str host_name:
    :param :py:class:`pathlib.Path` tmp_run_dir:

    :return: Namespace of run timing info:
               it000: 1st time step number
               itend: last time step number
               date0: run start date
               rdt: time step in seconds
    :rtype: :py:class:`types.SimpleNamespace`
    """
    with tempfile.NamedTemporaryFile('wt') as namelist_cfg:
        sftp_client.get(f'{tmp_run_dir}/namelist_cfg', namelist_cfg.name)
        logger.debug(f'downloaded {host_name}:{tmp_run_dir}/namelist_cfg')
        namelist = f90nml.read(namelist_cfg.name)
        run_info = SimpleNamespace(
            it000=namelist['namrun']['nn_it000'],
            itend=namelist['namrun']['nn_itend'],
            date0=arrow.get(str(namelist['namrun']['nn_date0']), 'YYYYMMDD'),
            rdt=namelist['namdom']['rn_rdt'],
        )
    return run_info


if __name__ == '__main__':
    main()  # pragma: no cover
