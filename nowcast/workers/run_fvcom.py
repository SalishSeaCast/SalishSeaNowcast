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
"""Salish Sea FVCOM Vancouver Harbour and Fraser River model worker that
prepares the temporary run directory and bash run script for a nowcast or
forecast run on the ONC cloud, and launches the run.
"""
import logging
import os
from pathlib import Path
import shlex
import shutil
import subprocess

import arrow
import fvcom_cmd.api
from nemo_nowcast import NowcastWorker
import yaml

from nowcast import lib

NAME = 'run_fvcom'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.run_fvcom --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name', help='Name of the host to execute the run on'
    )
    worker.cli.add_argument(
        'run_type',
        choices={'nowcast', 'forecast'},
        help='''
        Type of run to execute:
        'nowcast' means run for present UTC day (after NEMO nowcast run)
        'forecast' means updated forecast run 
        (next 36h UTC, after NEMO forecast run)
        ''',
    )
    worker.cli.add_date_option(
        '--run-date',
        default=arrow.now().floor('day'),
        help='Date to execute the run for.'
    )
    worker.run(run_fvcom, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f'{parsed_args.run_type} FVCOM VH-FR run for '
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'on {parsed_args.host_name} started',
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = f'success {parsed_args.run_type}'
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f'{parsed_args.run_type} FVCOM VH-FR run for '
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'on {parsed_args.host_name} failed',
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        }
    )
    msg_type = f'failure {parsed_args.run_type}'
    return msg_type


def run_fvcom(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    run_desc_file_path = _create_run_desc_file(run_date, run_type, config)
    tmp_run_dir = fvcom_cmd.api.prepare(run_desc_file_path)
    ## TODO: It would be nice if prepare() copied YAML file to tmp run dir
    shutil.copy2(run_desc_file_path, tmp_run_dir / run_desc_file_path.name)
    logger.debug(f'{run_type}: temporary run directory: {tmp_run_dir}')
    run_script_path = _create_run_script(
        run_date, run_type, tmp_run_dir, run_desc_file_path, config
    )
    run_desc_file_path.unlink()
    run_exec_cmd = _launch_run_script(run_type, run_script_path, host_name)
    return {
        run_type: {
            'host': host_name,
            'run dir': os.fspath(tmp_run_dir),
            'run exec cmd': run_exec_cmd,
            'run date': run_date.format('YYYY-MM-DD'),
        }
    }


def _create_run_desc_file(run_date, run_type, config):
    """
    :param :py:class:`arrow.Arrow` run_date:
    :param str run_type:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run description file path
    :rtype: :py:class:`pathlib.Path`
    """
    ddmmmyy = run_date.format('DDMMMYY').lower()
    run_id = f'{ddmmmyy}fvcom-{run_type}'
    run_prep_dir = Path(config['vhfr fvcom runs']['run prep dir'])
    run_desc = _run_description(run_id, run_prep_dir, config)
    run_desc_file_path = run_prep_dir / f'{run_id}.yaml'
    with run_desc_file_path.open('wt') as f:
        yaml.dump(run_desc, f, default_flow_style=False)
    logger.debug(f'{run_type}: run description file: {run_desc_file_path}')
    return run_desc_file_path


def _run_description(run_id, run_prep_dir, config):
    """
    :param str run_id:
    :param :py:class:`pathlib.Path` run_prep_dir:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run description
    :rtype dict:
    """
    casename = config['vhfr fvcom runs']['case name']
    run_desc = {
        'run_id':
            run_id,
        'casename':
            casename,
        'nproc':
            config['vhfr fvcom runs']['number of processors'],
        'paths': {
            'FVCOM':
                os.fspath(
                    Path(config['vhfr fvcom runs']['FVCOM exe path']).resolve()
                ),
            'runs directory':
                os.fspath(run_prep_dir.resolve()),
            'input':
                os.fspath((run_prep_dir / 'input').resolve()),
        },
        ## TODO: I would prefer to split the namelist into sections.
        ## If we change fvcom.prepare, then this becomes a list of sections,
        ## otherwise the sections have to be concatenated here.
        'namelist':
            os.fspath((run_prep_dir / f'{casename}_run.nml').resolve()),
        ## TODO: Add VCS revision tracking, but need to be able to handle Git
        ## repos to do so.
    }
    return run_desc


def _create_run_script(
    run_date, run_type, tmp_run_dir, run_desc_file_path, config
):
    """
    :param :py:class:`arrow.Arrow` run_date:
    :param str run_type:
    :param :py:class:`pathlib.Path` tmp_run_dir:
    :param :py:class:`pathlib.Path` run_desc_file_path:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run script file path
    :rtype: :py:class:`pathlib.Path`
    """
    results_dir = Path(
        config['vhfr fvcom runs']['run types'][run_type]['results']
    )
    ddmmmyy = run_date.format('DDMMMYY').lower()
    script = _build_script(
        tmp_run_dir, run_desc_file_path, results_dir / ddmmmyy, config
    )
    run_script_path = tmp_run_dir / 'VHFR_FVCOM.sh'
    with run_script_path.open('wt') as f:
        f.write(script)
    lib.fix_perms(
        run_script_path, lib.FilePerms(user='rwx', group='rwx', other='r')
    )
    logger.debug(f'{run_type}: run script: {run_script_path}')
    return run_script_path


def _build_script(tmp_run_dir, run_desc_file_path, results_dir, config):
    """
    :param :py:class:`pathlib.Path` tmp_run_dir:
    :param :py:class:`pathlib.Path` run_desc_file_path:
    :param :py:class:`pathlib.Path` results_dir:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run script
    :rtype: str
    """
    with run_desc_file_path.open('rt') as f:
        run_desc = yaml.load(f)
    script = '#!/bin/bash\n'
    script = '\n'.join((
        script, '{defns}\n'
        '{execute}\n'
        '{fix_permissions}\n'
        '{cleanup}'.format(
            defns=_definitions(
                run_desc, tmp_run_dir, run_desc_file_path, results_dir, config
            ),
            execute=_execute(config),
            fix_permissions=_fix_permissions(),
            cleanup=_cleanup(),
        )
    ))
    return script


def _definitions(
    run_desc, tmp_run_dir, run_desc_file_path, results_dir, config
):
    """
    :param dict run_desc:
    :param :py:class:`pathlib.Path` tmp_run_dir:
    :param :py:class:`pathlib.Path` run_desc_file_path:
    :param :py:class:`pathlib.Path` results_dir:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run script definitions
    :rtype: str
    """
    defns = (
        'RUN_ID="{run_id}"\n'
        'RUN_DESC="{run_desc_file}"\n'
        'WORK_DIR="{run_dir}"\n'
        'RESULTS_DIR="{results_dir}"\n'
        'MPIRUN="mpirun --hostfile ${{HOME}}/mpi_hosts.fvcom"\n'
        'GATHER="{fvc_cmd} gather"\n'
    ).format(
        run_id=run_desc['run_id'],
        run_desc_file=run_desc_file_path.name,
        run_dir=tmp_run_dir,
        results_dir=results_dir,
        mpirun=
        f'mpirun --hostfile {config["vhfr fvcom runs"]["mpi hosts file"]}',
        fvc_cmd=config['vhfr fvcom runs']['fvc_cmd'],
    )
    return defns


def _execute(config):
    """
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run script model execution commands
    :rtype: str
    """
    mpirun = (
        f'${{MPIRUN}} -np {config["vhfr fvcom runs"]["number of processors"]} '
        f'--bind-to-core ./fvcom '
        f'--casename={config["vhfr fvcom runs"]["case name"]} '
        f'--logfile=./fvcom.log'
    )
    script = (
        'mkdir -p ${RESULTS_DIR}\n'
        '\n'
        'cd ${WORK_DIR}\n'
        'echo "working dir: $(pwd)" >>${RESULTS_DIR}/stdout\n'
        '\n'
        'echo "Starting run at $(date)" >>${RESULTS_DIR}/stdout\n'
    )
    script += (
        f'{mpirun} >>${{RESULTS_DIR}}/stdout 2>>${{RESULTS_DIR}}/stderr\n'
    )
    script += (
        'echo "Ended run at $(date)" >>${RESULTS_DIR}/stdout\n'
        '\n'
        'echo "Results gathering started at $(date)" >>${RESULTS_DIR}/stdout\n'
        '${GATHER} ${RESULTS_DIR} --debug >>${RESULTS_DIR}/stdout\n'
        'echo "Results gathering ended at $(date)" >>${RESULTS_DIR}/stdout\n'
    )
    return script


def _fix_permissions():
    """
    :return: Run script results directory and files permissions adjustment commands
    :rtype: str
    """
    script = (
        'chmod g+rwx ${RESULTS_DIR}\n'
        'chmod g+rw ${RESULTS_DIR}/*\n'
        'chmod o+rx ${RESULTS_DIR}\n'
        'chmod o+r ${RESULTS_DIR}/*\n'
    )
    return script


def _cleanup():
    """
    :return: Run script commands to delete temporary run directory
    :rtype: str
    """
    script = (
        'echo "Deleting run directory" >>${RESULTS_DIR}/stdout\n'
        'rmdir $(pwd)\n'
        'echo "Finished at $(date)" >>${RESULTS_DIR}/stdout\n'
    )
    return script


def _launch_run_script(run_type, run_script_path, host_name):
    """
    :param str run_type:
    :param :py:class:`pathlib.Path` run_script_path:
    :param str host_name:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run execution command
    :rtype: str
    """
    logger.info(f'{run_type}: launching {run_script_path} on {host_name}')
    run_exec_cmd = f'bash {run_script_path}'
    logger.debug(
        f'{run_type}: running command in subprocess: '
        f'{shlex.split(run_exec_cmd)}'
    )
    subprocess.Popen(shlex.split(run_exec_cmd))
    run_process_pid = None
    while not run_process_pid:
        try:
            proc = subprocess.run(
                shlex.split(f'pgrep --newest --exact --full "{run_exec_cmd}"'),
                stdout=subprocess.PIPE,
                check=True,
                universal_newlines=True
            )
            run_process_pid = int(proc.stdout)
        except subprocess.CalledProcessError:
            # Process has not yet been spawned
            pass
    logger.debug(f'{run_type} on {host_name}: run pid: {run_process_pid}')
    return run_exec_cmd


if __name__ == '__main__':
    main()  # pragma: no cover
