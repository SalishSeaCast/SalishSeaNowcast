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

"""Salish Sea NEMO-3.6 nowcast worker that prepares the YAML run
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
import salishsea_cmd.api
from salishsea_tools.namelist import namelist2dict
import yaml

from nowcast import lib


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
        choices={'nowcast', 'nowcast-green', 'forecast', 'forecast2'},
        help='''
        Type of run to execute:
        'nowcast' means nowcast physics run,
        'nowcast-green' means nowcast green ocean run,
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
        run_date, run_type, host_name, config, tell_manager,
        parsed_args.shared_storage)
    run_dir = Path(salishsea_cmd.api.prepare(str(run_desc_filepath)))
    _log_msg(
        '{}: temporary run directory: {}'.format(run_type, run_dir),
        'debug', tell_manager, parsed_args.shared_storage)
    run_script_filepath = _create_run_script(
        run_date, run_type, run_dir, run_desc_filepath, host_name, config,
        tell_manager, parsed_args.shared_storage)
    run_desc_filepath.unlink()
    run_process_pid = _launch_run_script(
        run_type, run_script_filepath, host_name, config, tell_manager,
        parsed_args.shared_storage)
    watcher_process_pid = _launch_run_watcher(
        run_type, run_process_pid, host_name, config, tell_manager,
        shared_storage=parsed_args.shared_storage)
    return {run_type: {
        'host': host_name,
        'run dir': str(run_dir),
        'pid': run_process_pid,
        'watcher pid': watcher_process_pid,
        'run date': run_date.format('YYYY-MM-DD'),
    }}


def _log_msg(msg, level, tell_manager, shared_storage):
    tell_manager('log.{}'.format(level), msg)
    if not shared_storage:
        # Emit message to local logging system
        logger.log(getattr(logging, level.upper()), msg)


def _create_run_desc_file(
    run_date, run_type, host_name, config, tell_manager, shared_storage,
):
    dmy = run_date.format('DDMMMYY').lower()
    run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
    run_days = {
        'nowcast': run_date,
        'nowcast-green': run_date,
        'forecast': run_date.replace(days=1),
        'forecast2': run_date.replace(days=2),
    }
    run_duration = config['run types'][run_type]['duration']
    host_run_config = config['run'][host_name]
    restart_timestep = _update_time_namelist(
        run_date, run_type, run_duration, host_run_config)
    run_desc = _run_description(
        run_days[run_type], run_type, run_id, restart_timestep, host_name,
        config, tell_manager, shared_storage)
    run_prep_dir = Path(host_run_config['run prep dir'])
    run_desc_filepath = run_prep_dir/'{}.yaml'.format(run_id)
    with run_desc_filepath.open('wt') as f:
        yaml.dump(run_desc, f, default_flow_style=False)
    _log_msg('{}: run description file: {}'.format(run_type, run_desc_filepath),
        'debug', tell_manager, shared_storage)
    return run_desc_filepath


def _update_time_namelist(run_date, run_type, run_duration, host_run_config):
    prev_runs = {
        # run-type: based-on run-type, date offset
        'nowcast': ('nowcast', -1),
        'nowcast-green': ('nowcast-green', -1),
        'forecast': ('nowcast', 0),
        'forecast2': ('forecast', 0),
    }
    prev_run_type, date_offset = prev_runs[run_type]
    results_dir = Path(host_run_config['results'][prev_run_type])
    dmy = run_date.replace(days=date_offset).format('DDMMMYY').lower()
    prev_run_namelist = namelist2dict(str(results_dir/dmy/'namelist_cfg'))
    prev_it000 = prev_run_namelist['namrun'][0]['nn_it000']
    prev_itend = prev_run_namelist['namrun'][0]['nn_itend']
    rdt = prev_run_namelist['namdom'][0]['rn_rdt']
    timesteps_per_day = 86400 / rdt
    namelist_time = Path(host_run_config['run prep dir'], 'namelist.time')
    with namelist_time.open('rt') as f:
        lines = f.readlines()
    new_lines, restart_timestep = _calc_new_namelist_lines(
        run_date, run_type, run_duration, prev_it000, prev_itend,
        timesteps_per_day, lines)
    with namelist_time.open('wt') as f:
        f.writelines(new_lines)
    return restart_timestep


def _calc_new_namelist_lines(
    run_date, run_type, run_duration, prev_it000, prev_itend, timesteps_per_day,
    lines,
):
    it000_line, it000 = _get_namelist_value('nn_it000', lines)
    itend_line, itend = _get_namelist_value('nn_itend', lines)
    lines[it000_line] = lines[it000_line].replace(it000, str(prev_itend + 1))
    restart_timestep = prev_itend
    new_itend = int(restart_timestep + (run_duration * timesteps_per_day))
    lines[itend_line] = lines[itend_line].replace(itend, str(new_itend))
    date0_line, date0 = _get_namelist_value('nn_date0', lines)
    run_date_offset = {
        'nowcast': 0,
        'nowcast-green': 0,
        'forecast': 1,
        'forecast2': 2,
    }
    new_date0 = run_date.replace(days=run_date_offset[run_type])
    lines[date0_line] = lines[date0_line].replace(
        date0, new_date0.format('YYYYMMDD'))
    return lines, restart_timestep


def _get_namelist_value(key, lines):
    line_index = [
        i for i, line in enumerate(lines)
        if line.strip() and line.split()[0] == key][-1]
    value = lines[line_index].split()[2]
    return line_index, value


def _run_description(
    run_date, run_type, run_id, restart_timestep, host_name, config,
    tell_manager, shared_storage,
):
    host_run_config = config['run'][host_name]
    restart_from = {
        'nowcast': 'nowcast',
        'nowcast-green': 'nowcast-green',
        'forecast': 'nowcast',
        'forecast2': 'forecast',
    }
    try:
        restart_dir = Path(host_run_config['results'][restart_from[run_type]])
    except KeyError:
        _log_msg(
            'no results directory for {run_type} in {host_name} run config'
            .format(run_type=run_type, host_name=host_name),
            'critical', tell_manager, shared_storage)
        raise WorkerError
    prev_run_dmys = {
        # run-type: previous run's ddmmmyy results directory name
        'nowcast': run_date.replace(days=-1).format('DDMMMYY').lower(),
        'nowcast-green': run_date.replace(days=-1).format('DDMMMYY').lower(),
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
    nowcast_dir = Path(host_run_config['nowcast dir'])
    forcing = {
        'NEMO-atmos': {
            'link to': str((nowcast_dir/'NEMO-atmos').resolve()),
            'check link': {
                'type': 'atmospheric',
                'namelist filename': 'namelist_cfg',
            }
        },
        'open_boundaries': {
            'link to': str((nowcast_dir/'open_boundaries/').resolve())},
        'rivers': {
            'link to': str((nowcast_dir/'rivers/').resolve())},
    }
    forcing.update(restart_filepaths)
    run_sets_dir = run_prep_dir/'../SS-run-sets/SalishSea/nemo3.6/nowcast'
    namelist_sections = (
        'namelist.time', 'namelist.domain', 'namelist.surface',
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
    run_desc['grid']['coordinates'] = config['coordinates']
    run_desc['grid']['bathymetry'] = config['run types'][run_type]['bathymetry']
    run_desc['output']['files'] = str((run_prep_dir/'iodef.xml').resolve())
    run_desc['output']['domain'] = str(
        (run_prep_dir/'../SS-run-sets/SalishSea/nemo3.6/domain_def.xml')
        .resolve())
    run_desc['output']['fields'] = str(
        (run_prep_dir/'../SS-run-sets/SalishSea/nemo3.6/nowcast/field_def.xml')
        .resolve())
    return run_desc


def _create_run_script(
    run_date, run_type, run_dir, run_desc_filepath, host_name, config,
    tell_manager, shared_storage,
):
    host_run_config = config['run'][host_name]
    dmy = run_date.format('DDMMMYY').lower()
    results_dir = Path(host_run_config['results'][run_type])
    script = _build_script(
        run_dir, run_desc_filepath, results_dir/dmy, host_run_config)
    run_script_filepath = run_dir/'SalishSeaNEMO.sh'
    with run_script_filepath.open('wt') as f:
        f.write(script)
    lib.fix_perms(str(run_script_filepath), mode=lib.PERMS_RWX_RWX_R)
    _log_msg('{}: run script: {}'.format(run_type, run_script_filepath),
        'debug', tell_manager, shared_storage)
    return run_script_filepath


def _build_script(run_dir, run_desc_filepath, results_dir, host_run_config):
    run_desc = salishsea_cmd.lib.load_run_desc(str(run_desc_filepath))
    jpni, jpnj = map(int, run_desc['MPI decomposition'].split('x'))
    nemo_processors = jpni * jpnj
    xios_processors = int(run_desc['output']['XIOS servers'])
    email = host_run_config.get('email', 'nobody@example.com')
    script = u'#!/bin/bash\n'
    if host_run_config['job exec cmd'] == 'qsub':
        script = u'\n'.join((script, u'{pbs_common}'.format(
            pbs_common=salishsea_cmd.api.pbs_common(
                run_desc, nemo_processors + xios_processors, email,
                results_dir))))
    script = u'\n'.join((
        script,
        u'{defns}\n'
        u'{execute}\n'
        u'{fix_permissions}\n'
        u'{cleanup}'
        .format(
            defns=_definitions(
                run_desc, run_desc_filepath, run_dir, results_dir,
                host_run_config),
            execute=_execute(nemo_processors, xios_processors),
            fix_permissions=_fix_permissions(),
            cleanup=_cleanup(),
        )
    ))
    return script


def _definitions(
    run_desc, run_desc_filepath, run_dir, results_dir, host_run_config,
):
    defns = (
        u'RUN_ID="{run_id}"\n'
        u'RUN_DESC="{run_desc_file}"\n'
        u'WORK_DIR="{run_dir}"\n'
        u'RESULTS_DIR="{results_dir}"\n'
        u'GATHER="{salishsea_cmd} gather"\n'
    ).format(
        run_id=run_desc['run_id'],
        run_desc_file=run_desc_filepath.name,
        run_dir=run_dir,
        results_dir=results_dir,
        salishsea_cmd=host_run_config['salishsea_cmd'],
    )
    return defns


def _execute(nemo_processors, xios_processors):
    mpirun = u'mpirun -np {procs} ./nemo.exe'.format(procs=nemo_processors)
    if xios_processors:
        mpirun = u' '.join((
            mpirun, ':', '-np', str(xios_processors), './xios_server.exe'))
    script = (
        u'cd ${WORK_DIR}\n'
        u'echo "working dir: $(pwd)"\n'
        u'\n'
        u'echo "Starting run at $(date)"\n'
        u'mkdir -p ${RESULTS_DIR}\n')
    script += u'{mpirun}\n'.format(mpirun=mpirun)
    script += (
        u'echo "Ended run at $(date)"\n'
        u'\n'
        u'echo "Results gathering started at $(date)"\n'
        u'${GATHER} ${RUN_DESC} ${RESULTS_DIR}\n'
        u'echo "Results gathering ended at $(date)"\n'
    )
    return script


def _fix_permissions():
    script = (
        u'chmod g+rwx ${RESULTS_DIR}\n'
        u'chmod g+rw ${RESULTS_DIR}/*\n'
        u'chmod o+rx ${RESULTS_DIR}\n'
        u'chmod o+r ${RESULTS_DIR}/*\n'
    )
    return script


def _cleanup():
    script = (
        u'echo "Deleting run directory"\n'
        u'rmdir $(pwd)\n'
    )
    return script


def _launch_run_script(
    run_type, run_script_filepath, host_name, config, tell_manager,
    shared_storage,
):
    host_run_config = config['run'][host_name]
    _log_msg('{}: launching {} on {}'
        .format(
            run_type, run_script_filepath, host_name), 'info', tell_manager,
            shared_storage)
    cmd = shlex.split(
        '{0[job exec cmd]} {1}'.format(host_run_config, run_script_filepath))
    _log_msg('{}: running command in subprocess: {}'.format(
        run_type, cmd),
        'debug', tell_manager, shared_storage)
    if host_run_config['job exec cmd'] == 'qsub':
        torque_id = subprocess.check_output(
            cmd, universal_newlines=True).strip()
        _log_msg('{}: TORQUE/PBD job id: {}'.format(
            run_type, torque_id),
            'debug', tell_manager, shared_storage)
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
    _log_msg('{} on {}: run pid: {}'.format(
        run_type, host_name, run_process_pid), 'debug', tell_manager,
        shared_storage)
    return run_process_pid


def _launch_run_watcher(
    run_type, run_process_pid, host_name, config, tell_manager, shared_storage,
):
    enabled_host_config = config['run']['enabled hosts'][host_name]
    _log_msg('launching {} watch_NEMO worker on {}'
        .format(run_type, host_name), 'info', tell_manager, shared_storage)
    cmd = shlex.split(
        '{0[python]} -m nowcast.workers.watch_NEMO {0[config file]} '
        '{host_name} {run_type} {run_process_pid}'
        .format(
            enabled_host_config, host_name=host_name, run_type=run_type,
            run_process_pid=run_process_pid))
    if shared_storage:
        cmd.append('--shared-storage')
    _log_msg('{}: running command in subprocess: {}'
        .format(run_type, cmd), 'debug', tell_manager, shared_storage)
    watcher_process = subprocess.Popen(cmd, universal_newlines=True)
    _log_msg('{} on {}: watcher pid: {.pid}'.format(
        run_type, host_name, watcher_process),
        'debug', tell_manager, shared_storage)
    return watcher_process.pid


if __name__ == '__main__':
    main()  # pragma: no cover
