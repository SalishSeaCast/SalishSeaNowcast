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
"""SalishSeaCast worker that 
"""
import logging
from pathlib import Path
import shlex
import subprocess
import tempfile
import time
from types import SimpleNamespace

import arrow
import f90nml
from nemo_nowcast import NowcastWorker, WorkerError

NAME = 'watch_NEMO_hindcast'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.watch_NEMO_hindcast --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name', help='Name of the host to monitor the run on'
    )
    worker.run(watch_NEMO_hindcast, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f'NEMO hindcast run on {parsed_args.host_name} completed',
        extra={
            'run_type': 'hindcast',
            'host_name': parsed_args.host_name,
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
        f'NEMO hindcast run on {parsed_args.host_name} watcher failed',
        extra={
            'run_type': 'hindcast',
            'host_name': parsed_args.host_name,
        }
    )
    msg_type = 'failure'
    return msg_type


def watch_NEMO_hindcast(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    users = config['run']['enabled hosts'][host_name]['users']
    scratch_dir = Path(
        config['run']['enabled hosts'][host_name]['scratch dir']
    )
    job_id, run_id = _get_run_id(host_name, users)
    while _is_queued(host_name, users, job_id, run_id):
        time.sleep(60)
    tmp_run_dir = _get_tmp_run_dir(host_name, scratch_dir, run_id)
    run_info = _get_run_info(host_name, tmp_run_dir)
    while _is_running(host_name, users, job_id, run_id, tmp_run_dir, run_info):
        time.sleep(60)
    while not _is_completed(host_name, users, job_id, run_id):
        time.sleep(60)
    checklist = {
        'hindcast': {
            'host': host_name,
            'run id': run_id,
            'completed': True,
        }
    }
    return checklist


def _get_run_id(host_name, users):
    """
    :param str host_name:
    :param str users:

    :return: slurm job id number, run id string
    :rtype: 2-tuple (int, str)
    """
    queue_info = _get_queue_info(host_name, users)
    job_id, run_id = queue_info.split()[:2]
    logger.info(f'watching {run_id} job {job_id} on {host_name}')
    return job_id, run_id


def _is_queued(host_name, users, job_id, run_id):
    """
    :param str host_name:
    :param str users:
    :param int job_id:
    :param str run_id:

    :return: Flag indicating whether or not run is queued in PENDING state
    :rtype: boolean
    """
    queue_info = _get_queue_info(host_name, users, job_id)
    try:
        state, reason, start_time = queue_info.split()[2:]
    except AttributeError:
        # job has disappeared from the queue; maybe cancelled
        logger.error(f'{run_id} job {job_id} not found on {host_name} queue')
        raise WorkerError
    if state != 'PENDING':
        return False
    msg = f'{run_id} job {job_id} pending due to {reason.lower()}'
    if start_time != 'N/A':
        msg = f'{msg}, scheduled for {start_time}'
    logger.info(msg)
    return True


def _get_tmp_run_dir(host_name, scratch_dir, run_id):
    """
    :param str host_name:
    :param :py:class:`pathlib.Path` scratch_dir:
    :param str run_id:

    :return: Temporary run directory
    :rtype: :py:class:`pathlib.Path`
    """
    cmd = f'ssh {host_name} ls -d {scratch_dir/run_id}*'
    proc = subprocess.run(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        check=True,
        universal_newlines=True
    )
    tmp_run_dir = Path(proc.stdout.strip())
    logger.debug(f'found tmp run dir: {host_name}:{tmp_run_dir}')
    return tmp_run_dir


def _is_running(host_name, users, job_id, run_id, tmp_run_dir, run_info):
    """
    :param str host_name:
    :param str users:
    :param int job_id:
    :param str run_id:
    :param :py:class:`pathlib.Path` tmp_run_dir:
    :param :py:class:`types.SimpleNamespace` run_info:

    :return: Flag indicating whether or not run is in RUNNING state
    :rtype: boolean
    """
    try:
        queue_info = _get_queue_info(host_name, users, job_id)
        state = queue_info.split()[2]
    except (subprocess.CalledProcessError, AttributeError):
        # job has disappeared from the queue; finished or cancelled
        logger.info(f'{run_id} job {job_id} not found on {host_name} queue')
        state = 'UNKNOWN'
    if state != 'RUNNING':
        return False
    try:
        cmd = f'ssh {host_name} cat {tmp_run_dir}/time.step'
        proc = subprocess.run(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            check=True,
            universal_newlines=True
        )
        time_step = int(proc.stdout.strip())
        # with (tmp_run_dir / 'time.step').open('rt') as f:
        #     time_step = int(f.read().strip())
        model_seconds = (time_step - run_info.it000) * run_info.rdt
        model_time = (
            run_info.date0.replace(seconds=model_seconds)
            .format('YYYY-MM-DD HH:mm:ss UTC')
        )
        fraction_done = (time_step - run_info.it000
                         ) / (run_info.itend - run_info.it000)
        msg = (
            f'{run_id} on {host_name}: timestep: '
            f'{time_step} = {model_time}, {fraction_done:.1%} complete'
        )
    except (subprocess.CalledProcessError, ValueError):
        # time.step file not found or empty; assume that run is young and it
        # hasn't been created yet, or has finished and it has been
        # moved to the results directory
        msg = (
            f'{run_id} on {host_name}: time.step not found; '
            f'continuing to watch...'
        )
    logger.info(msg)
    return True


def _is_completed(host_name, users, job_id, run_id):
    """
    :param users:
    :param str host_name:
    :param int job_id:
    :param str run_id:

    :return: Flag indicating whether or not run is in COMPLETED state
    :rtype: boolean
    """
    sacct_cmd = f'ssh {host_name} /opt/software/slurm/bin/sacct --user {users}'
    cmd = f'{sacct_cmd} --job {job_id}.batch --format=state'
    proc = subprocess.run(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        check=True,
        universal_newlines=True
    )
    if len(proc.stdout.splitlines()) == 2:
        logger.debug(
            f'{job_id} batch step not found in saact report; '
            f'continuing to look...'
        )
        return False
    state = proc.stdout.splitlines()[2].strip()
    if state != 'COMPLETED':
        return False
    logger.info(f'{run_id} on {host_name}: completed')
    return True


def _get_queue_info(host_name, users, job_id=None):
    """
    :param users:
    :param str host_name:
    :param int job_id:

    :return: None or 1 line of output from slurm squeue command that describes
             the run's state
    :rtype: str
    """
    squeue_cmd = (
        f'ssh {host_name} /opt/software/slurm/bin/squeue --user {users}'
    )
    queue_info_format = '--Format "jobid,name,state,reason,starttime"'
    cmd = (
        f'{squeue_cmd} {queue_info_format}' if job_id is None else
        f'{squeue_cmd} --job {job_id} {queue_info_format}'
    )
    proc = subprocess.run(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        check=True,
        universal_newlines=True
    )
    if len(proc.stdout.splitlines()) == 1:
        if job_id is None:
            logger.error(f'no hindcast jobs found on {host_name} queue')
            raise WorkerError
        else:
            # Various callers handle job id not on queue in difference ways
            return
    for queue_info in proc.stdout.splitlines()[1:]:
        if 'hindcast' in queue_info.strip().split()[1]:
            return queue_info.strip()


def _get_run_info(host_name, tmp_run_dir):
    """
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
        cmd = f'scp {host_name}:{tmp_run_dir}/namelist_cfg {namelist_cfg.name}'
        subprocess.run(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            check=True,
            universal_newlines=True
        )
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
