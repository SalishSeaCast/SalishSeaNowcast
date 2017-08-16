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
description file and bash run script for a nowcast, nowcast-green, nowcast-dev,
forecast or forecast2 run on the ONC cloud or salish,
and launches the run.
"""
import logging
import os
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
import salishsea_cmd.lib
import salishsea_cmd.run
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
    worker.cli.add_date_option(
        '--run-date', default=arrow.now().floor('day'),
        help='Date to execute the run for.')
    worker.run(run_NEMO, success, failure)


def success(parsed_args):
    logger.info(
        f'{parsed_args.run_type} NEMO run for '
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'on {parsed_args.host_name} started',
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = f'success {parsed_args.run_type}'
    return msg_type


def failure(parsed_args):
    logger.critical(
        f'{parsed_args.run_type} NEMO run for '
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'on {parsed_args.host_name} failed',
        extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = f'failure {parsed_args.run_type}'
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
    run_dir = Path(salishsea_cmd.api.prepare(run_desc_filepath))
    logger.debug(f'{run_type}: temporary run directory: {run_dir}')
    run_script_filepath = _create_run_script(
        run_date, run_type, run_dir, run_desc_filepath, host_name, config)
    run_desc_filepath.unlink()
    run_exec_cmd, run_id = _launch_run_script(
        run_type, run_script_filepath, host_name, config)
    return {run_type: {
        'host': host_name,
        'run dir': os.fspath(run_dir),
        'run exec cmd': run_exec_cmd,
        'run id': run_id,
        'run date': run_date.format('YYYY-MM-DD'),
    }}


def _create_run_desc_file(run_date, run_type, host_name, config):
    dmy = run_date.format('DDMMMYY').lower()
    run_id = f'{dmy}{run_type}'
    run_days = {
        'nowcast': run_date,
        'nowcast-green': run_date,
        'nowcast-dev': run_date,
        'forecast': run_date.replace(days=1),
        'forecast2': run_date.replace(days=2),
    }
    run_duration = config['run types'][run_type]['duration']
    host_config = config['run']['enabled hosts'][host_name]
    run_prep_dir = Path(host_config['run prep dir'])
    restart_timestep = _update_time_namelist(
        run_date, run_type, run_duration, host_config, run_prep_dir)
    run_desc = _run_description(
        run_days[run_type], run_type, run_id, restart_timestep, host_name,
        config)
    run_desc_filepath = run_prep_dir / f'{run_id}.yaml'
    with run_desc_filepath.open('wt') as f:
        yaml.dump(run_desc, f, default_flow_style=False)
    logger.debug(f'{run_type}: run description file: {run_desc_filepath}')
    return run_desc_filepath


def _update_time_namelist(
    run_date, run_type, run_duration, host_config, run_prep_dir
):
    prev_runs = {
        # run-type: based-on run-type, date offset
        'nowcast': ('nowcast', -1),
        'nowcast-green': ('nowcast-green', -1),
        'nowcast-dev': ('nowcast-dev', -1),
        'forecast': ('nowcast', 0),
        'forecast2': ('forecast', 0),
    }
    prev_run_type, date_offset = prev_runs[run_type]
    results_dir = Path(host_config['run types'][prev_run_type]['results'])
    dmy = run_date.replace(days=date_offset).format('DDMMMYY').lower()
    prev_run_namelist = namelist2dict(os.fspath(results_dir/dmy/'namelist_cfg'))
    prev_it000 = prev_run_namelist['namrun'][0]['nn_it000']
    rdt = prev_run_namelist['namdom'][0]['rn_rdt']
    timesteps_per_day = 86400 / rdt
    namelist_time = run_prep_dir / 'namelist.time'
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
        stocklist, f'{next_restart_timestep},')
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
    host_config = config['run']['enabled hosts'][host_name]
    restart_from = {
        'nowcast': 'nowcast',
        'nowcast-green': 'nowcast-green',
        'nowcast-dev': 'nowcast-dev',
        'forecast': 'nowcast',
        'forecast2': 'forecast',
    }
    try:
        restart_dir = Path(
            host_config['run types'][restart_from[run_type]]['results'])
    except KeyError:
        logger.critical(
            f'no results directory for {run_type} in {host_name} run config')
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
        'restart.nc':
            os.fspath(
                Path(restart_dir/prev_run_dmys[run_type] /
                     f'SalishSea_{restart_timestep:08d}_restart.nc'
                     ).resolve())
    }
    if run_type == 'nowcast-green':
        restart_filepaths['restart_trc.nc'] = (
            os.fspath(
                Path(
                    restart_dir/prev_run_dmys[run_type] /
                    f'SalishSea_{restart_timestep:08d}_restart_trc.nc')
                .resolve())
        )
    run_prep_dir = Path(host_config['run prep dir'])
    NEMO_config_name = config['run types'][run_type]['config name']
    forcing = {
        'NEMO-atmos': {
            'link to': os.fspath((run_prep_dir/'NEMO-atmos').resolve()),
            'check link': {
                'type': 'atmospheric',
                'namelist filename': 'namelist_cfg',
            }
        },
        'ssh': {
            'link to': os.fspath((run_prep_dir/'ssh/').resolve())},
        'tides': {
            'link to': os.fspath((run_prep_dir/'tides/').resolve())},
        'tracers': {
            'link to': os.fspath((run_prep_dir/'tracers/').resolve())},
        'LiveOcean': {
            'link to': os.fspath((run_prep_dir/'LiveOcean/').resolve())},
        'open_boundaries': {
            'link to': os.fspath((run_prep_dir/'open_boundaries/').resolve())},
        'rivers': {
            'link to': os.fspath((run_prep_dir/'rivers/').resolve())},
    }
    run_sets_dir = Path(host_config['run types'][run_type]['run sets dir'])
    namelists = {
        'namelist_cfg': [os.fspath((run_prep_dir/'namelist.time').resolve())]
    }
    namelist_sections = (
        'namelist.domain', 'namelist.surface',
        'namelist.lateral', 'namelist.bottom', 'namelist.tracer',
        'namelist.dynamics', 'namelist.vertical', 'namelist.compute',
    )
    for namelist in namelist_sections:
        namelists['namelist_cfg'].append(
            os.fspath((run_sets_dir/namelist).resolve()))
    if run_type == 'nowcast-green':
        for namelist in ('namelist_top_cfg', 'namelist_pisces_cfg'):
            namelists[namelist] = [
                os.fspath((run_sets_dir/namelist).resolve())]
    run_desc = salishsea_cmd.api.run_description(
        run_id=run_id,
        config_name=NEMO_config_name,
        mpi_decomposition=(
            host_config['run types'][run_type]['mpi decomposition']),
        walltime=(host_config['run types'][run_type].get('walltime')),
        NEMO_code_config=os.fspath(
            (run_prep_dir / '../NEMO-3.6-code' / 'NEMOGCM' / 'CONFIG')
            .resolve()),
        XIOS_code=os.fspath((run_prep_dir / '../XIOS-2/').resolve()),
        forcing_path=os.fspath((run_prep_dir / '../NEMO-forcing/').resolve()),
        runs_dir=os.fspath(run_prep_dir.resolve()),
        forcing=forcing,
        namelists=namelists,
    )
    grid_dir = Path(host_config['grid dir'])
    run_desc['grid']['coordinates'] = os.fspath(
        grid_dir / config['coordinates'])
    run_desc['grid']['bathymetry'] = os.fspath(
        grid_dir / config['run types'][run_type]['bathymetry'])
    lpe_filename = config['run types'][run_type]['land processor elimination']
    run_desc['grid']['land processor elimination'] = (
        False if host_name == 'salish-nowcast'
        else os.fspath(grid_dir / lpe_filename))
    run_desc['restart'] = restart_filepaths
    run_desc['output'].update({
        'iodefs': os.fspath((run_sets_dir/'iodef.xml').resolve()),
        'domaindefs': os.fspath((run_sets_dir/'domain_def.xml').resolve()),
        'fielddefs': os.fspath((run_sets_dir/'field_def.xml').resolve()),
    })
    del run_desc['output']['domain']
    del run_desc['output']['fields']
    if (run_sets_dir/'file_def.xml').exists():
        run_desc['output']['filedefs'] = os.fspath(
            (run_sets_dir/'file_def.xml').resolve())
    run_desc['vcs revisions'] = {
        'hg': [
            os.fspath((run_prep_dir/'../NEMO-Cmd').resolve()),
            os.fspath((run_prep_dir/'../NEMO_Nowcast').resolve()),
            os.fspath((run_prep_dir/'../rivers').resolve()),
            os.fspath((run_prep_dir/'../SalishSeaCmd').resolve()),
            os.fspath((run_prep_dir/'../SS-run-sets').resolve()),
            os.fspath((run_prep_dir/'../tides').resolve()),
            os.fspath((run_prep_dir/'../tracers').resolve()),
            os.fspath((run_prep_dir/'../tools').resolve()),
            os.fspath((run_prep_dir/'../XIOS-ARCH').resolve()),
        ]
    }
    return run_desc


def _create_run_script(
    run_date, run_type, run_dir, run_desc_filepath, host_name, config
):
    host_config = config['run']['enabled hosts'][host_name]
    dmy = run_date.format('DDMMMYY').lower()
    results_dir = Path(host_config['run types'][run_type]['results'])
    script = _build_script(
        run_dir, run_type, run_desc_filepath, results_dir / dmy, host_name,
        config)
    run_script_filepath = run_dir/'SalishSeaNEMO.sh'
    with run_script_filepath.open('wt') as f:
        f.write(script)
    run_script_filepath.chmod(FilePerms(user='rwx', group='rwx', other='r'))
    logger.debug(f'{run_type}: run script: {run_script_filepath}')
    return run_script_filepath


def _build_script(
    run_dir, run_type, run_desc_filepath, results_dir, host_name, config,
):
    run_desc = salishsea_cmd.lib.load_run_desc(run_desc_filepath)
    host_config = config['run']['enabled hosts'][host_name]
    nemo_processors = salishsea_cmd.lib.get_n_processors(run_desc, run_dir)
    xios_processors = int(run_desc['output']['XIOS servers'])
    email = host_config.get('email', 'nobody@example.com')
    xios_host = host_config.get('xios host')
    script = '#!/bin/bash\n'
    if host_config['job exec cmd'] == 'qsub':
        script = '\n'.join((script, '{pbs_common}'.format(
            pbs_common=salishsea_cmd.run._pbs_common(
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
    host_config = config['run']['enabled hosts'][host_name]
    mpirun = 'mpirun'
    if host_config.get('mpi hosts file') is not None:
        mpirun = f'mpirun --hostfile {host_config["mpi hosts file"]}'
    defns = (
        'RUN_ID="{run_id}"\n'
        'RUN_DESC="{run_desc_file}"\n'
        'WORK_DIR="{run_dir}"\n'
        'RESULTS_DIR="{results_dir}"\n'
        'MPIRUN="{mpirun}"\n'
        'COMBINE="{salishsea_cmd} combine"\n'
        'GATHER="{salishsea_cmd} gather"\n'
    ).format(
        run_id=run_desc['run_id'],
        run_desc_file=run_desc_filepath.name,
        run_dir=run_dir,
        results_dir=results_dir,
        mpirun=mpirun,
        salishsea_cmd=host_config['salishsea_cmd'],
    )
    return defns


def _execute(nemo_processors, xios_processors, xios_host):
    mpirun = (
        f'${{MPIRUN}} -np {nemo_processors} --bind-to-core ./nemo.exe : '
        f'-np {xios_processors} --bind-to-core ./xios_server.exe')
    if xios_host is not None:
        mpirun = (
            f'${{MPIRUN}} -np {nemo_processors} --bind-to-core ./nemo.exe : '
            f'-host {xios_host} -np {xios_processors} --bind-to-core '
            f'./xios_server.exe')
    script = (
        'mkdir -p ${RESULTS_DIR}\n'
        '\n'
        'cd ${WORK_DIR}\n'
        'echo "working dir: $(pwd)" >>${RESULTS_DIR}/stdout\n'
        '\n'
        'echo "Starting run at $(date)" >>${RESULTS_DIR}/stdout\n'
    )
    script += (
        f'{mpirun} >>${{RESULTS_DIR}}/stdout 2>>${{RESULTS_DIR}}/stderr\n')
    script += (
        'echo "Ended run at $(date)" >>${RESULTS_DIR}/stdout\n'
        '\n'
        'echo "Results combining started at $(date)" >>${RESULTS_DIR}/stdout\n'
        '${COMBINE} ${RUN_DESC} --debug >>${RESULTS_DIR}/stdout\n'
        'echo "Results combining ended at $(date)" >>${RESULTS_DIR}/stdout\n'
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
    host_config = config['run']['enabled hosts'][host_name]
    logger.info(f'{run_type}: launching {run_script_filepath} on {host_name}')
    cmd = f'{host_config["job exec cmd"]} {run_script_filepath}'
    run_exec_cmd = cmd
    logger.debug(
        f'{run_type}: running command in subprocess: {shlex.split(cmd)}')
    if host_config['job exec cmd'] == 'qsub':
        proc = subprocess.run(
            shlex.split(cmd), stdout=subprocess.PIPE,
            check=True, universal_newlines=True)
        torque_id = proc.stdout.strip()
        logger.debug(f'{run_type}: TORQUE/PBD job id: {torque_id}')
        cmd = shlex.split(f'pgrep {torque_id}')
        run_id = torque_id
    else:
        run_id = None
        subprocess.Popen(shlex.split(cmd))
        cmd = shlex.split(f'pgrep --newest --exact --full "{cmd}"')
    run_process_pid = None
    while not run_process_pid:
        try:
            proc = subprocess.run(
                cmd, stdout=subprocess.PIPE, check=True,
                universal_newlines=True)
            run_process_pid = int(proc.stdout)
        except subprocess.CalledProcessError:
            # Process has not yet been spawned
            pass
    logger.debug(f'{run_type} on {host_name}: run pid: {run_process_pid}')
    return run_exec_cmd, run_id


if __name__ == '__main__':
    main()  # pragma: no cover
