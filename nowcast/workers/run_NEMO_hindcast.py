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
"""SalishSeaCast worker that prepares the YAML run description file and
bash run script for a NEMO hindcast run on an HPC cluster that uses the SLURM
scheduler, and queues the run.
"""
import logging
from pathlib import Path
import shlex
import subprocess
import tempfile
from types import SimpleNamespace

import arrow
import f90nml
from nemo_nowcast import NowcastWorker, WorkerError
import yaml

NAME = 'run_NEMO_hindcast'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.run_NEMO_hindcast --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name', help='Name of the host to monitor the run on'
    )
    worker.cli.add_argument(
        '--prev-run-date',
        default=None,
        help='Start date of the previous hindcast run.'
    )
    worker.run(run_NEMO_hindcast, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f'NEMO hindcast run queued on {parsed_args.host_name}',
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
        f'NEMO hindcast run failed to queue on {parsed_args.host_name}',
        extra={
            'run_type': 'hindcast',
            'host_name': parsed_args.host_name,
        }
    )
    msg_type = 'failure'
    return msg_type


def run_NEMO_hindcast(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    if parsed_args.prev_run_date is None:
        prev_run_date, prev_job_id = _get_prev_run_queue_info(
            host_name, config
        )
    else:
        prev_run_date = arrow.get(parsed_args.prev_run_date)
        prev_job_id = None
    run_date = prev_run_date.replace(months=+1)
    prev_namelist_info = _get_prev_run_namelist_info(
        host_name, prev_run_date, config
    )
    _edit_namelist_time(host_name, prev_namelist_info, run_date, config)
    _edit_run_desc(
        host_name, prev_run_date, prev_namelist_info, run_date, config
    )
    run_id = f'{run_date.format("DDMMMYY").lower()}hindcast'
    _launch_run(host_name, run_id, prev_job_id, config)
    checklist = {
        'hindcast': {
            'host': host_name,
            'run id': run_id,
        }
    }
    return checklist


def _get_prev_run_queue_info(host_name, config):
    """
    :param str host_name:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run date of the previous hindcast run found on the queue,
             slurm job id number
    :rtype: 2-tuple (:py:class:`arrow.Arrow`, int)
    """
    users = config['run']['hindcast hosts'][host_name]['users']
    squeue_cmd = (
        f'ssh {host_name} /opt/software/slurm/bin/squeue --user {users}'
    )
    queue_info_format = '--Format "jobid,name"'
    cmd_output = _cmd_in_subprocess(f'{squeue_cmd} {queue_info_format}')
    if len(cmd_output.splitlines()) == 1:
        logger.error(f'no jobs found on {host_name} queue')
        raise WorkerError
    queue_info_lines = cmd_output.splitlines()[1:]
    queue_info_lines.reverse()
    for queue_info in queue_info_lines:
        if 'hindcast' in queue_info.strip().split()[1]:
            job_id, run_id = queue_info.strip().split()
            logger.info(
                f'using {run_id} job {job_id} on {host_name} as previous run'
            )
            job_id = int(job_id)
            prev_run_date = arrow.get(run_id[:7], 'DDMMMYY')
            return prev_run_date, job_id
    logger.error(f'no hindcast jobs found on {host_name} queue')
    raise WorkerError


def _get_prev_run_namelist_info(host_name, prev_run_date, config):
    """
    :param str host_name:
    :param :py:class:`arrow.Arrow` prev_run_date:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Namespace of run timing info:
               itend: last time step number
               rdt: time step in seconds
    :rtype: :py:class:`types.SimpleNamespace`
    """
    scratch_dir = Path(
        config['run']['hindcast hosts'][host_name]['scratch dir']
    )
    dmy = prev_run_date.format('DDMMMYY').lower()
    cmd_output = _cmd_in_subprocess(
        f'ssh {host_name} ls -d {scratch_dir/dmy}*/namelist_cfg'
    )
    prev_namelist_cfg = cmd_output.strip()
    logger.info(
        f'found previous run namelist: {host_name}:{prev_namelist_cfg}'
    )
    with tempfile.NamedTemporaryFile('wt') as namelist_cfg:
        _cmd_in_subprocess(
            f'scp {host_name}:{prev_namelist_cfg} {namelist_cfg.name}'
        )
        namelist = f90nml.read(namelist_cfg.name)
        prev_namelist_info = SimpleNamespace(
            itend=namelist['namrun']['nn_itend'],
            rdt=namelist['namdom']['rn_rdt'],
        )
    return prev_namelist_info


def _edit_namelist_time(host_name, prev_namelist_info, run_date, config):
    """
    :param str host_name:
    :param :py:class:`types.SimpleNamespace` prev_namelist_info:
    :param :py:class:`arrow.Arrow` prev_run_date:
    :param :py:class:`nemo_nowcast.Config` config:
    """
    run_days = (run_date.replace(months=+1) - run_date).days
    timesteps_per_day = 24 * 60 * 60 / prev_namelist_info.rdt
    itend = prev_namelist_info.itend + run_days * timesteps_per_day
    patch = {
        'namrun': {
            'nn_it000':
                prev_namelist_info.itend + 1,
            'nn_itend':
                int(itend),
            'nn_date0':
                int(run_date.format('YYYYMMDD')),
            'nn_stocklist': [
                (int(prev_namelist_info.itend + timesteps_per_day * 10)),
                (int(prev_namelist_info.itend + timesteps_per_day * 20)),
                int(itend), 0, 0, 0, 0, 0, 0, 0
            ],
        }
    }
    run_prep_dir = Path(
        config['run']['hindcast hosts'][host_name]['run prep dir']
    )
    namelist_time_tmpl = f'{run_prep_dir}/namelist.time'
    _cmd_in_subprocess(
        f'scp {host_name}:{namelist_time_tmpl} /tmp/hindcast.namelist.time'
    )
    logger.debug(f'downloaded {host_name}:{run_prep_dir}/namelist.time')
    f90nml.patch(
        '/tmp/hindcast.namelist.time', patch,
        '/tmp/patched_hindcast.namelist.time'
    )
    logger.debug('patched namelist.time')
    _cmd_in_subprocess(
        f'scp /tmp/patched_hindcast.namelist.time '
        f'{host_name}:{run_prep_dir}/namelist.time'
    )
    logger.debug(f'uploaded new {host_name}:{run_prep_dir}/namelist.time')


def _edit_run_desc(
    host_name, prev_run_date, prev_namelist_info, run_date, config
):
    """
    :param str host_name:
    :param :py:class:`arrow.Arrow` prev_run_date:
    :param :py:class:`types.SimpleNamespace` prev_namelist_info:
    :param :py:class:`arrow.Arrow` run_date:
    :param :py:class:`nemo_nowcast.Config` config:
    """
    run_prep_dir = Path(
        config['run']['hindcast hosts'][host_name]['run prep dir']
    )
    _cmd_in_subprocess(
        f'scp {host_name}:{run_prep_dir}/hindcast_template.yaml '
        f'/tmp/hindcast_template.yaml'
    )
    with Path('/tmp/hindcast_template.yaml').open('rt') as run_desc_tmpl:
        run_desc = yaml.safe_load(run_desc_tmpl)
    logger.debug(
        f'downloaded {host_name}:{run_prep_dir}/hindcast_template.yaml'
    )
    run_id = f'{run_date.format("DDMMMYY").lower()}hindcast'
    run_desc['run_id'] = run_id
    logger.debug(f'set run_id to {run_id}')
    scratch_dir = Path(
        config['run']['hindcast hosts'][host_name]['scratch dir']
    )
    prev_run_dir = scratch_dir / (prev_run_date.format('DDMMMYY').lower())
    restart_file = (
        f'{prev_run_dir}/SalishSea_{prev_namelist_info.itend:08d}_restart.nc'
    )
    run_desc['restart']['restart.nc'] = restart_file
    logger.debug(f'set restart.nc to {restart_file}')
    restart_trc_file = (
        f'{prev_run_dir}/'
        f'SalishSea_{prev_namelist_info.itend:08d}_restart_trc.nc'
    )
    run_desc['restart']['restart_trc.nc'] = restart_trc_file
    logger.debug(f'set restart_trc.nc to {restart_trc_file}')
    with Path('/tmp/hindcast.yaml').open('wt') as run_desc_tmpl:
        yaml.safe_dump(run_desc, run_desc_tmpl, default_flow_style=False)
    _cmd_in_subprocess(
        f'scp /tmp/hindcast.yaml {host_name}:{run_prep_dir}/{run_id}.yaml'
    )
    logger.debug(f'uploaded {host_name}:{run_prep_dir}/{run_id}.yaml')


def _launch_run(host_name, run_id, prev_job_id, config):
    """
    :param str host_name:
    :param str run_id:
    :param int prev_job_id:
    :param :py:class:`nemo_nowcast.Config` config:
    """
    salishsea_cmd = config['run']['hindcast hosts'][host_name]['salishsea cmd']
    run_prep_dir = Path(
        config['run']['hindcast hosts'][host_name]['run prep dir']
    )
    run_desc = run_prep_dir / f'{run_id}.yaml'
    scratch_dir = Path(
        config['run']['hindcast hosts'][host_name]['scratch dir']
    )
    results_dir = scratch_dir / run_id[:7]
    cmd = (
        f'ssh {host_name} {salishsea_cmd} run {run_desc} {results_dir} '
        f'--no-deflate'
    )
    if prev_job_id:
        cmd = f'{cmd} --waitjob {prev_job_id} --nocheck-initial-conditions'
    _cmd_in_subprocess(cmd)


def _cmd_in_subprocess(cmd):
    """
    :param str cmd:

    :return: Output from the command
    :rtype: str
    """
    logger.debug(f'running command in subprocess: {cmd}')
    try:
        cmd_output = subprocess.check_output(
            shlex.split(cmd),
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        for line in cmd_output.splitlines():
            if line:
                logger.info(line)
        return cmd_output
    except subprocess.CalledProcessError as e:
        for line in e.output.splitlines():
            if line:
                logger.debug(line)


if __name__ == '__main__':
    main()  # pragma: no cover
