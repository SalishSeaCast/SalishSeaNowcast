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
"""SalishSeaCast worker that repares the YAML run description file and
bash run script for a NEMO SMELT AGRIF run on an HPC cluster that uses the
TORQUE/MOAB scheduler, and queues the run.
"""
import logging
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace

import arrow
import f90nml
from nemo_nowcast import NowcastWorker, WorkerError
import yaml

from nowcast import ssh_sftp

NAME = 'run_NEMO_agrif'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.run_NEMO_agrif --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name', help='Name of the host to queue the run on'
    )
    worker.cli.add_argument(
        'run_type',
        choices={'nowcast-agrif'},
        help='''
        Type of run to execute:
        'nowcast-agrif' means nowcast green ocean run with AGRIF sub-grids
        ''',
    )
    worker.cli.add_date_option(
        '--run-date',
        default=arrow.now().floor('day'),
        help='Date to execute the run for.'
    )
    worker.run(run_NEMO_agrif, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f'NEMO nowcast-agrif run for '
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'queued on {parsed_args.host_name}',
        extra={
            'run_type': 'nowcast-agrif',
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
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
        f'NEMO nowcast-agrif run for '
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'failed to queue on {parsed_args.host_name}',
        extra={
            'run_type': 'nowcast-agrif',
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = 'failure'
    return msg_type


def run_NEMO_agrif(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    run_date = parsed_args.run_date
    ssh_key = Path(
        os.environ['HOME'], '.ssh',
        config['run']['enabled hosts'][host_name]['ssh key']
    )
    run_id = f'{run_date.format("DDMMMYY").lower()}nowcast-agrif'
    try:
        ssh_client, sftp_client = ssh_sftp.sftp(host_name, os.fspath(ssh_key))
        prev_run_namelists_info = _get_prev_run_namelists_info(
            sftp_client, host_name, run_date.replace(days=-1), config
        )
        _edit_namelist_times(
            sftp_client, host_name, prev_run_namelists_info, run_date, config
        )
        _edit_run_desc(
            sftp_client, host_name, prev_run_namelists_info, run_id, run_date,
            config
        )
        run_dir, job_id = _launch_run(ssh_client, host_name, run_id, config)
    finally:
        sftp_client.close()
        ssh_client.close()
    checklist = {
        'nowcast-agrif': {
            'host': host_name,
            'run id': run_id,
            'run dir': run_dir,
            'job id': job_id,
            'run date': run_date.format('YYYY-MM-DD'),
        }
    }
    return checklist


def _get_prev_run_namelists_info(
    sftp_client, host_name, prev_run_date, config
):
    """
    :param :py:class:`paramiko.sftp_client.SFTPClient` sftp_client:
    :param str host_name:
    :param :py:class:`arrow.Arrow` prev_run_date:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Namespace of run timing info from previous run namelists:
               itend: last time step number in full domain
               rdt: time step in seconds in full domain
               1_rdt: time step in seconds in 1st sub-grid
               2_rdt: time step in seconds in 2nd sub-grid
    :rtype: :py:class:`types.SimpleNamespace`
    """
    scratch_dir = Path(
        config['run']['enabled hosts'][host_name]['scratch dir']
    )
    dmy = prev_run_date.format('DDMMMYY').lower()
    prev_namelist_cfgs = ['namelist_cfg', '1_namelist_cfg', '2_namelist_cfg']
    prev_run_namelists_info = SimpleNamespace()
    for i, namelist in enumerate(prev_namelist_cfgs):
        prev_namelist_cfg = scratch_dir / dmy / namelist
        with tempfile.NamedTemporaryFile('wt') as namelist_cfg:
            sftp_client.get(os.fspath(prev_namelist_cfg), namelist_cfg.name)
            logger.debug(f'downloaded {host_name}:{prev_namelist_cfg}')
            namelist = f90nml.read(namelist_cfg.name)
            if i == 0:
                prev_run_namelists_info.itend = namelist['namrun']['nn_itend']
                prev_run_namelists_info.rdt = namelist['namdom']['rn_rdt']
            else:
                setattr(
                    prev_run_namelists_info, f'{i}_rdt',
                    namelist['namdom']['rn_rdt']
                )
    return prev_run_namelists_info


def _edit_namelist_times(
    sftp_client, host_name, prev_run_namelists_info, run_date, config
):
    """
    :param :py:class:`paramiko.sftp_client.SFTPClient` sftp_client:
    :param str host_name:
    :param :py:class:`types.SimpleNamespace` prev_run_namelists_info:
    :param :py:class:`arrow.Arrow` run_date:
    :param :py:class:`nemo_nowcast.Config` config:
    """
    itend = (
        prev_run_namelists_info.itend +
        24 * 60 * 60 / prev_run_namelists_info.rdt
    )
    patches = {
        'namelist.time': {
            'namrun': {
                'nn_it000': prev_run_namelists_info.itend + 1,
                'nn_itend': int(itend),
                'nn_date0': int(run_date.format('YYYYMMDD')),
            }
        },
        'namelist.time.HS': {
            'namrun': {
                'nn_date0': int(run_date.format('YYYYMMDD')),
            }
        },
        'namelist.time.BS': {
            'namrun': {
                'nn_date0': int(run_date.format('YYYYMMDD')),
            }
        },
    }
    run_prep_dir = Path(
        config['run']['enabled hosts'][host_name]['run prep dir']
    )
    for i, namelist in enumerate(patches):
        sftp_client.get(
            os.fspath(run_prep_dir / namelist),
            f'/tmp/nowcast-agrif.{namelist}'
        )
        logger.debug(f'downloaded {host_name}:{run_prep_dir/namelist}')
        f90nml.patch(
            f'/tmp/nowcast-agrif.{namelist}', patches[namelist],
            f'/tmp/patched_nowcast-agrif.{namelist}'
        )
        logger.debug('patched namelist.time')
        sftp_client.put(
            f'/tmp/patched_nowcast-agrif.{namelist}',
            os.fspath(run_prep_dir / namelist)
        )
        logger.debug(f'uploaded new {host_name}:{run_prep_dir/namelist}')


def _edit_run_desc(
    sftp_client,
    host_name,
    prev_run_namelists_info,
    run_id,
    run_date,
    config,
    yaml_tmpl='/tmp/nowcast-agrif_template.yaml'
):
    """
    :param :py:class:`paramiko.sftp_client.SFTPClient` sftp_client:
    :param str host_name:
    :param :py:class:`types.SimpleNamespace` prev_run_namelists_info:
    :param str run_id:
    :param :py:class:`arrow.Arrow` run_date:
    :param :py:class:`nemo_nowcast.Config` config:
    :param str yaml_tmpl:
    """
    run_prep_dir = Path(
        config['run']['enabled hosts'][host_name]['run prep dir']
    )
    sftp_client.get(
        f'{run_prep_dir}/nowcast-agrif_template.yaml',
        '/tmp/nowcast-agrif_template.yaml'
    )
    logger.debug(
        f'downloaded {host_name}:{run_prep_dir}/nowcast-agrif_template.yaml'
    )
    with Path(yaml_tmpl).open('rt') as run_desc_tmpl:
        run_desc = yaml.safe_load(run_desc_tmpl)
    run_desc['run_id'] = run_id
    logger.debug(f'set run_id to {run_id}')
    scratch_dir = Path(
        config['run']['enabled hosts'][host_name]['scratch dir']
    )
    prev_run_dir = scratch_dir / (
        run_date.replace(days=-1).format('DDMMMYY').lower()
    )
    restart_file = (
        f'{prev_run_dir}/'
        f'SalishSea_{prev_run_namelists_info.itend:08d}_restart.nc'
    )
    run_desc['restart']['restart.nc'] = restart_file
    logger.debug(f'set restart.nc to {restart_file}')
    restart_trc_file = (
        f'{prev_run_dir}/'
        f'SalishSea_{prev_run_namelists_info.itend:08d}_restart_trc.nc'
    )
    run_desc['restart']['restart_trc.nc'] = restart_trc_file
    logger.debug(f'set restart_trc.nc to {restart_trc_file}')
    for i in range(1, 3):
        itend = int(
            prev_run_namelists_info.itend * prev_run_namelists_info.rdt /
            getattr(prev_run_namelists_info, f'{i}_rdt')
        )
        restart_file = (
            f'{prev_run_dir}/'
            f'{i}_SalishSea_{itend:08d}_restart.nc'
        )
        run_desc['restart'][f'AGRIF_{i}']['restart.nc'] = restart_file
        logger.debug(f'set AGRIF_{i} restart.nc to {restart_file}')
        restart_trc_file = (
            f'{prev_run_dir}/{i}_SalishSea_{itend:08d}_restart_trc.nc'
        )
        run_desc['restart'][f'AGRIF_{i}']['restart_trc.nc'] = restart_trc_file
        logger.debug(f'set AGRIF_{i} restart_trc.nc to {restart_trc_file}')
    with Path(yaml_tmpl).open('wt') as run_desc_tmpl:
        yaml.safe_dump(run_desc, run_desc_tmpl, default_flow_style=False)
    sftp_client.put(
        '/tmp/nowcast-agrif_template.yaml', f'{run_prep_dir}/{run_id}.yaml'
    )
    logger.debug(f'uploaded {host_name}:{run_prep_dir}/{run_id}.yaml')


def _launch_run(ssh_client, host_name, run_id, config):
    """
    :param :py:class:`paramiko.sftp_client.SFTPClient` ssh_client:
    :param str host_name:
    :param str run_id:
    :param :py:class:`nemo_nowcast.Config` config:

    :returns: Job id from TORQUE/MOAD resource manager
    :rtype: str
    """
    salishsea_cmd = config['run']['enabled hosts'][host_name]['salishsea cmd']
    run_prep_dir = Path(
        config['run']['enabled hosts'][host_name]['run prep dir']
    )
    run_desc = run_prep_dir / f'{run_id}.yaml'
    scratch_dir = Path(
        config['run']['enabled hosts'][host_name]['scratch dir']
    )
    results_dir = scratch_dir / run_id[:7]
    cmd = f'{salishsea_cmd} run {run_desc} {results_dir} --no-deflate'
    logger.debug(f'launching run on {host_name}: {cmd}')
    _, stdout, stderr = ssh_client.exec_command(cmd)
    stderr_lines = stderr.readlines()
    if stderr_lines:
        for line in stderr_lines:
            logger.error(line.strip())
        raise WorkerError
    stdout_lines = stdout.readlines()
    run_dir = stdout_lines[0].split()[-1]
    logger.debug(f'temporary run dir: {host_name}:{run_dir}')
    job_id = stdout_lines[1].split()[-1]
    logger.info(f'job id for {run_id}: {job_id}')
    return run_dir, job_id


if __name__ == '__main__':
    main()  # pragma: no cover
