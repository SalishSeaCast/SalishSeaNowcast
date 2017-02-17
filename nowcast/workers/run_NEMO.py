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

"""Salish Sea NEMO nowcast worker that prepares the YAML run
description file and bash run script for a nowcast, nowcast-green,
forecast or forecast2 run on the ONC cloud or salish,
and launches the run.
"""
import logging
from pathlib import Path
import shlex
import subprocess

import arrow
from nemo_nowcast import (
    NowcastWorker,
    WorkerError,
)
from nemo_cmd.namelist import namelist2dict
from nemo_nowcast.fileutils import FilePerms
import salishsea_cmd.api
from salishsea_cmd.lib import get_n_processors
import yaml


NAME = 'run_NEMO'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.run_NEMO --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name',
        help='Name of the host to execute the run on')
    worker.cli.add_argument(
        'run_type',
        choices={
            'nowcast', 'nowcast-green', 'nowcast-dev', 'forecast', 'forecast2'},
        help='''
        Type of run to execute:
        'nowcast' means nowcast physics run,
        'nowcast-green' means nowcast green ocean run,
        'nowcast-dev' means nowcast physics run with in-development features,
        'forecast' means updated forecast run,
        'forecast2' means preliminary forecast run,
        ''',
    )
    worker.cli.add_argument(
        '--shared-storage', action='store_true',
        help='''
        Indicates that the NEMO run is on a machine (e.g. salish) that
        shares storage with the machine on which the nowcast manager is
        running. That affects how log messages are handled.
        ''')
    worker.cli.add_date_option(
        '--run-date', default=arrow.now().floor('day'),
        help='Date to execute the run for.')
    worker.run(run_NEMO, success, failure)


def success(parsed_args):
    logger.info(
        '{0.run_type} NEMO run for {run_date} on {0.host_name} started'
        .format(
            parsed_args, run_date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'success {.run_type}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical(
        '{0.run_type} NEMO run for {run_date} on {0.host_name} failed'
        .format(
            parsed_args, run_date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'failure {.run_type}'.format(parsed_args)
    return msg_type


def run_NEMO(parsed_args, config, tell_manager):
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    if not run_type.startswith('nowcast'):
        run_info = tell_manager('need', 'NEMO run').payload
        run_date = arrow.get(run_info['nowcast']['run date'])
    run_desc_filepath = _create_run_desc_file(
        run_date, run_type, host_name, config)
    run_dir = Path(salishsea_cmd.api.prepare(str(run_desc_filepath)))
    logger.debug(
        '{}: temporary run directory: {}'.format(run_type, run_dir))
    run_script_filepath = _create_run_script(
        run_date, run_type, run_dir, run_desc_filepath, host_name, config)
    run_desc_filepath.unlink()
    run_process_pid = _launch_run_script(
        run_type, run_script_filepath, host_name, config)
    watcher_process_pid = _launch_run_watcher(
        run_type, run_process_pid, host_name, config,
        shared_storage=parsed_args.shared_storage)
    return {run_type: {
        'host': host_name,
        'run dir': str(run_dir),
        'pid': run_process_pid,
        'watcher pid': watcher_process_pid,
        'run date': run_date.format('YYYY-MM-DD'),
    }}


def _create_run_desc_file(run_date, run_type, host_name, config):
    dmy = run_date.format('DDMMMYY').lower()
    run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
    run_days = {
        'nowcast': run_date,
        'nowcast-green': run_date,
        'nowcast-dev': run_date,
        'forecast': run_date.replace(days=1),
        'forecast2': run_date.replace(days=2),
    }
    run_duration = config['run types'][run_type]['duration']
    host_run_config = config['run'][host_name]
    restart_timestep = _update_time_namelist(
        run_date, run_type, run_duration, host_run_config)
    run_desc = _run_description(
        run_days[run_type], run_type, run_id, restart_timestep, host_name,
        config)
    run_prep_dir = Path(host_run_config['run prep dir'])
    run_desc_filepath = run_prep_dir/'{}.yaml'.format(run_id)
    with run_desc_filepath.open('wt') as f:
        yaml.dump(run_desc, f, default_flow_style=False)
    logger.debug(
        '{}: run description file: {}'.format(run_type, run_desc_filepath))
    return run_desc_filepath


def _update_time_namelist(run_date, run_type, run_duration, host_run_config):
    prev_runs = {
        # run-type: based-on run-type, date offset
        'nowcast': ('nowcast', -1),
        'nowcast-green': ('nowcast-green', -1),
        'nowcast-dev': ('nowcast-dev', -1),
        'forecast': ('nowcast', 0),
        'forecast2': ('forecast', 0),
    }
    prev_run_type, date_offset = prev_runs[run_type]
    results_dir = Path(host_run_config['results'][prev_run_type])
    dmy = run_date.replace(days=date_offset).format('DDMMMYY').lower()
    prev_run_namelist = namelist2dict(str(results_dir/dmy/'namelist_cfg'))
    prev_it000 = prev_run_namelist['namrun'][0]['nn_it000']
    try:
        namelist_domain_path = Path(
            host_run_config['run prep dir'], 'namelist.domain')
        namelist_domain = namelist2dict(str(namelist_domain_path))
        rdt = namelist_domain['namdom'][0]['rn_rdt']
    except FileNotFoundError:
        rdt = prev_run_namelist['namdom'][0]['rn_rdt']
    timesteps_per_day = 86400 / rdt
    namelist_time = Path(host_run_config['run prep dir'], 'namelist.time')
    with namelist_time.open('rt') as f:
        lines = f.readlines()
    new_lines, restart_timestep = _calc_new_namelist_lines(
        run_date, run_type, run_duration, prev_it000, timesteps_per_day, lines)
    with namelist_time.open('wt') as f:
        f.writelines(new_lines)
    return restart_timestep


def _calc_new_namelist_lines(
    run_date, run_type, run_duration, prev_it000, timesteps_per_day, lines,
):
    it000_line, it000 = _get_namelist_value('nn_it000', lines)
    itend_line, itend = _get_namelist_value('nn_itend', lines)
    new_it000 = int(prev_it000 + timesteps_per_day)
    lines[it000_line] = lines[it000_line].replace(it000, str(new_it000))
    restart_timestep = int(
        (prev_it000 - 1) + int(run_duration) * timesteps_per_day)
    new_itend = int(restart_timestep + (run_duration * timesteps_per_day))
    lines[itend_line] = lines[itend_line].replace(itend, str(new_itend))
    date0_line, date0 = _get_namelist_value('nn_date0', lines)
    run_date_offset = {
        'nowcast': 0,
        'nowcast-green': 0,
        'nowcast-dev': 0,
        'forecast': 1,
        'forecast2': 2,
    }
    new_date0 = run_date.replace(days=run_date_offset[run_type])
    lines[date0_line] = lines[date0_line].replace(
        date0, new_date0.format('YYYYMMDD'))
    stocklist_line, stocklist = _get_namelist_value('nn_stocklist', lines)
    next_restart_timestep = int(
        restart_timestep + int(run_duration) * timesteps_per_day)
    lines[stocklist_line] = lines[stocklist_line].replace(
        stocklist, '{},'.format(next_restart_timestep))
    return lines, restart_timestep


def _get_namelist_value(key, lines):
    line_index = [
        i for i, line in enumerate(lines)
        if line.strip() and line.split()[0] == key][-1]
    value = lines[line_index].split()[2]
    return line_index, value


def _run_description(
    run_date, run_type, run_id, restart_timestep, host_name, config,
):
    host_run_config = config['run'][host_name]
    restart_from = {
        'nowcast': 'nowcast',
        'nowcast-green': 'nowcast-green',
        'nowcast-dev': 'nowcast-dev',
        'forecast': 'nowcast',
        'forecast2': 'forecast',
    }
    try:
        restart_dir = Path(host_run_config['results'][restart_from[run_type]])
    except KeyError:
        logger.critical(
            'no results directory for {run_type} in {host_name} run config'
            .format(run_type=run_type, host_name=host_name))
        raise WorkerError
    prev_run_dmys = {
        # run-type: previous run's ddmmmyy results directory name
        'nowcast': run_date.replace(days=-1).format('DDMMMYY').lower(),
        'nowcast-green': run_date.replace(days=-1).format('DDMMMYY').lower(),
        'nowcast-dev': run_date.replace(days=-1).format('DDMMMYY').lower(),
        'forecast': run_date.replace(days=-1).format('DDMMMYY').lower(),
        'forecast2': run_date.replace(days=-2).format('DDMMMYY').lower(),
    }
    restart_filepaths = {
        'restart.nc': {
            'link to': str(
                Path(
                    restart_dir/prev_run_dmys[run_type] /
                    'SalishSea_{:08d}_restart.nc'.format(restart_timestep))
                .resolve())
        }}
    if run_type == 'nowcast-green':
        restart_filepaths['restart_trc.nc'] = {
            'link to': str(
                Path(
                    restart_dir/prev_run_dmys[run_type] /
                    'SalishSea_{:08d}_restart_trc.nc'.format(restart_timestep))
                .resolve())
        }
    run_prep_dir = Path(host_run_config['run prep dir'])
    NEMO_config_name = config['run types'][run_type]['config name']
    walltime = host_run_config.get('walltime')
    forcing = {
        'NEMO-atmos': {
            'link to': str((run_prep_dir/'NEMO-atmos').resolve()),
            'check link': {
                'type': 'atmospheric',
                'namelist filename': 'namelist_cfg',
            }
        },
        'open_boundaries': {
            'link to': str((run_prep_dir/'open_boundaries/').resolve())},
        'rivers': {
            'link to': str((run_prep_dir/'rivers/').resolve())},
    }
    forcing.update(restart_filepaths)
    run_sets_dir = run_prep_dir/'../SS-run-sets/SalishSea/nemo3.6/nowcast'
    if run_type == 'nowcast-green':
        namelist_sections = (
            'namelist.time', 'namelist.domain', 'namelist.surface.green',
            'namelist.lateral', 'namelist.bottom', 'namelist.tracer',
            'namelist.dynamics', 'namelist.vertical', 'namelist.compute',
        )
    else:
        namelist_sections = (
            'namelist.time', 'namelist.domain', 'namelist.surface.blue',
            'namelist.lateral', 'namelist.bottom', 'namelist.tracer',
            'namelist.dynamics', 'namelist.vertical', 'namelist.compute',
        )
    namelists = {'namelist_cfg': []}
    for namelist in namelist_sections:
        if (run_prep_dir/namelist).exists():
            namelists['namelist_cfg'].append(
                str((run_prep_dir/namelist).resolve()))
        else:
            namelists['namelist_cfg'].append(
                str((run_sets_dir/namelist).resolve()))
    if run_type == 'nowcast-green':
        for namelist in ('namelist_top_cfg', 'namelist_pisces_cfg'):
            if (run_prep_dir/namelist).exists():
                namelists[namelist] = [str((run_prep_dir/namelist).resolve())]
            else:
                namelists[namelist] = [str((run_sets_dir/namelist).resolve())]
    run_desc = salishsea_cmd.api.run_description(
        run_id=run_id,
        config_name=NEMO_config_name,
        mpi_decomposition=host_run_config['mpi decomposition'],
        walltime=walltime,
        NEMO_code=str((run_prep_dir/'../NEMO-3.6-code/').resolve()),
        XIOS_code=str((run_prep_dir/'../XIOS/').resolve()),
        forcing_path=str((run_prep_dir/'../NEMO-forcing/').resolve()),
        runs_dir=str(run_prep_dir.resolve()),
        forcing=forcing,
        namelists=namelists,
    )
    run_desc['paths']['NEMO code config'] = str(
        (run_prep_dir/'../NEMO-3.6-code'/'NEMOGCM'/'CONFIG').resolve())
    run_desc['grid']['coordinates'] = Path(config['coordinates']).name
    run_desc['grid']['bathymetry'] = Path(
        config['run types'][run_type]['bathymetry']).name
    run_desc['output']['files'] = str((run_prep_dir/'iodef.xml').resolve())
    run_desc['output']['domain'] = str(
        (run_prep_dir/'../SS-run-sets/SalishSea/nemo3.6/domain_def.xml')
        .resolve())
    run_desc['output']['fields'] = str(
        (run_prep_dir/'../SS-run-sets/SalishSea/nemo3.6/nowcast/field_def.xml')
        .resolve())
    return run_desc


def _create_run_script(run_date, run_type, run_dir, run_desc_filepath,
    host_name, config):
    host_run_config = config['run'][host_name]
    dmy = run_date.format('DDMMMYY').lower()
    results_dir = Path(host_run_config['results'][run_type])
    script = _build_script(
        run_dir, run_type, run_desc_filepath, results_dir / dmy, host_name,
        config)
    run_script_filepath = run_dir/'SalishSeaNEMO.sh'
    with run_script_filepath.open('wt') as f:
        f.write(script)
    run_script_filepath.chmod(FilePerms(user='rwx', group='rwx', other='r'))
    logger.debug('{}: run script: {}'.format(run_type, run_script_filepath))
    return run_script_filepath


def _build_script(
    run_dir, run_type, run_desc_filepath, results_dir, host_name, config,
):
    run_desc = salishsea_cmd.lib.load_run_desc(str(run_desc_filepath))
    host_run_config = config['run'][host_name]
    nemo_processors = get_n_processors(run_desc)
    xios_processors = int(run_desc['output']['XIOS servers'])
    email = host_run_config.get('email', 'nobody@example.com')
    xios_host = config['run']['enabled hosts'][host_name].get('xios host')
    script = '#!/bin/bash\n'
    if host_run_config['job exec cmd'] == 'qsub':
        script = '\n'.join((script, '{pbs_common}'.format(
            pbs_common=salishsea_cmd.api.pbs_common(
                run_desc, nemo_processors + xios_processors, email,
                results_dir))))
    script = '\n'.join((
        script,
        '{defns}\n'
        '{execute}\n'
        '{fix_permissions}\n'
        '{cleanup}'
        .format(
            defns=_definitions(
                run_type, run_desc, run_desc_filepath, run_dir, results_dir,
                host_name, config),
            execute=_execute(nemo_processors, xios_processors, xios_host),
            fix_permissions=_fix_permissions(),
            cleanup=_cleanup(),
        )
    ))
    return script


def _definitions(
    run_type, run_desc, run_desc_filepath, run_dir, results_dir, host_name,
    config,
):
    enabled_host_config = config['run']['enabled hosts'][host_name]
    mpirun = 'mpirun'
    if enabled_host_config.get('mpi hosts file') is not None:
        mpirun = 'mpirun --hostfile {[mpi hosts file]}'.format(
            enabled_host_config)
    defns = (
        'RUN_ID="{run_id}"\n'
        'RUN_DESC="{run_desc_file}"\n'
        'WORK_DIR="{run_dir}"\n'
        'RESULTS_DIR="{results_dir}"\n'
        'MPIRUN="{mpirun}"\n'
        u'COMBINE="{salishsea_cmd} combine"\n'
        u'DEFLATE="{salishsea_cmd} deflate"\n'
        u'GATHER="{salishsea_cmd} gather"\n'
    ).format(
        run_id=run_desc['run_id'],
        run_desc_file=run_desc_filepath.name,
        run_dir=run_dir,
        results_dir=results_dir,
        mpirun=mpirun,
        salishsea_cmd=config['run'][host_name]['salishsea_cmd'],
        gather_opts='--delete-restart' if run_type == 'forecast2' else '',
    )
    return defns


def _execute(nemo_processors, xios_processors, xios_host):
    mpirun = (
        '${{MPIRUN}} -np {nemo_procs} --bind-to-core ./nemo.exe : '
        '-np {xios_procs} --bind-to-core ./xios_server.exe'.format(
            nemo_procs=nemo_processors, xios_procs=xios_processors))
    if xios_host is not None:
        mpirun = (
            '${{MPIRUN}} -np {nemo_procs} --bind-to-core ./nemo.exe : '
            '-host {xios_host} '
            '-np {xios_procs} --bind-to-core ./xios_server.exe'.format(
                nemo_procs=nemo_processors,
                xios_host=xios_host,
                xios_procs=xios_processors))
    script = (
        'mkdir -p ${RESULTS_DIR}\n'
        '\n'
        'cd ${WORK_DIR}\n'
        'echo "working dir: $(pwd)" >>${RESULTS_DIR}/stdout\n'
        '\n'
        'echo "Starting run at $(date)" >>${RESULTS_DIR}/stdout\n'
    )
    script += (
        '{mpirun} >>${{RESULTS_DIR}}/stdout 2>>${{RESULTS_DIR}}/stderr\n'
        .format(mpirun=mpirun))
    script += (
        'echo "Ended run at $(date)" >>${RESULTS_DIR}/stdout\n'
        '\n'
        'echo "Results combining started at $(date)" >>${RESULTS_DIR}/stdout\n'
        '${COMBINE} ${RUN_DESC} --debug >>${RESULTS_DIR}/stdout\n'
        'echo "Results combining ended at $(date)" >>${RESULTS_DIR}/stdout\n'
        '\n'
        'echo "Results deflation started at $(date)" >>${RESULTS_DIR}/stdout\n'
        '${DEFLATE} *_grid_[TUVW]*.nc *_ptrc_T*.nc --debug '
        '>>${RESULTS_DIR}/stdout\n'
        'echo "Results deflation ended at $(date)" >>${RESULTS_DIR}/stdout\n'
        '\n'
        'echo "Results gathering started at $(date)" >>${RESULTS_DIR}/stdout\n'
        '${GATHER} ${RESULTS_DIR} --debug >>${RESULTS_DIR}/stdout\n'
        'echo "Results gathering ended at $(date)" >>${RESULTS_DIR}/stdout\n'
    )
    return script


def _fix_permissions():
    script = (
        'chmod g+rwx ${RESULTS_DIR}\n'
        'chmod g+rw ${RESULTS_DIR}/*\n'
        'chmod o+rx ${RESULTS_DIR}\n'
        'chmod o+r ${RESULTS_DIR}/*\n'
    )
    return script


def _cleanup():
    script = (
        'echo "Deleting run directory" >>${RESULTS_DIR}/stdout\n'
        'rmdir $(pwd)\n'
        'echo "Finished at $(date)" >>${RESULTS_DIR}/stdout\n'
    )
    return script


def _launch_run_script(run_type, run_script_filepath, host_name, config):
    host_run_config = config['run'][host_name]
    logger.info('{}: launching {} on {}'.format(
        run_type, run_script_filepath, host_name))
    cmd = shlex.split(
        '{0[job exec cmd]} {1}'.format(host_run_config, run_script_filepath))
    logger.debug('{}: running command in subprocess: {}'.format(run_type, cmd))
    if host_run_config['job exec cmd'] == 'qsub':
        torque_id = subprocess.check_output(
            cmd, universal_newlines=True).strip()
        logger.debug('{}: TORQUE/PBD job id: {}'.format(run_type, torque_id))
        cmd = shlex.split('pgrep {}'.format(torque_id))
    else:
        subprocess.Popen(cmd)
        cmd = shlex.split(
            'pgrep --newest --exact --full "{}"'.format(' '.join(cmd)))
    run_process_pid = None
    while not run_process_pid:
        try:
            run_process_pid = int(
                subprocess.check_output(cmd, universal_newlines=True))
        except subprocess.CalledProcessError:
            # Process has not yet been spawned
            pass
    logger.debug('{} on {}: run pid: {}'.format(
        run_type, host_name, run_process_pid))
    return run_process_pid


def _launch_run_watcher(
    run_type, run_process_pid, host_name, config, shared_storage,
):
    enabled_host_config = config['run']['enabled hosts'][host_name]
    logger.info('launching {} watch_NEMO worker on {}'.format(
        run_type, host_name))
    cmd = shlex.split(
        '{0[python]} -m nowcast.workers.watch_NEMO {0[config file]} '
        '{host_name} {run_type} {run_process_pid}'
        .format(
            enabled_host_config, host_name=host_name, run_type=run_type,
            run_process_pid=run_process_pid))
    if shared_storage:
        cmd.append('--shared-storage')
    logger.debug('{}: running command in subprocess: {}'.format(run_type, cmd))
    watcher_process = subprocess.Popen(cmd, universal_newlines=True)
    logger.debug('{} on {}: watcher pid: {.pid}'.format(
        run_type, host_name, watcher_process))
    return watcher_process.pid


if __name__ == '__main__':
    main()  # pragma: no cover
