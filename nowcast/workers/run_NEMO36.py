# Copyright 2013-2015 The Salish Sea MEOPAR contributors
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
import os
from pathlib import Path
import shlex
import subprocess

import arrow
import yaml

import salishsea_cmd.api
from salishsea_tools.namelist import namelist2dict

from nowcast import lib
from nowcast.nowcast_worker import NowcastWorker


worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)


RUN_DURATIONS = {
    # run-type: days
    'nowcast': 1,
    'nowcast-green': 1,
    'forecast': 1.25,
    'forecast2': 1.25,
}


def main():
    worker = NowcastWorker(worker_name, description=__doc__)
    worker.arg_parser.add_argument(
        'host_name', help='Name of the host to execute the run on')
    worker.arg_parser.add_argument(
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
    salishsea_today = arrow.now('Canada/Pacific').floor('day')
    worker.arg_parser.add_argument(
        '--run-date', type=lib.arrow_date,
        default=salishsea_today,
        help='''
        Date to execute the run for; use YYYY-MM-DD format.
        Defaults to {}.
        '''.format(salishsea_today.format('YYYY-MM-DD')),
    )
    worker.run(run_NEMO, success, failure)


def success(parsed_args):
    logger.info(
        '{0.run_type} NEMO run for {0.run_date} on {0.host_name} started'
        .format(parsed_args), extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'success {.run_type}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical(
        '{0.run_type} NEMO run for {0.run_date} on {0.host_name} failed'
        .format(parsed_args), extra={
            'run_type': parsed_args.run_type,
            'host_name': parsed_args.host_name,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'failure {.run_type}'.format(parsed_args)
    return msg_type


## TODO: add msg_socket to args passed in _do_work & propagate to other workers
def run_NEMO(parsed_args, config, msg_socket):
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    if not run_type.startswith('nowcast'):
        run_info = lib.tell_manager(
            worker_name, 'need', config, logger, msg_socket, 'NEMO run')
        run_date = arrow.get(run_info['nowcast']['run date'])
    run_desc_filepath = _create_run_desc_file(
        run_date, run_type, host_name, config, msg_socket)
## TODO: figure out path for iodef.xml in absence of os.chdir()
    run_dir = salishsea_cmd.api.prepare(run_desc_filepath, 'iodef.xml')
    _log_msg(
        '{}: temporary run directory: {}'.format(run_type, run_dir),
        'debug', config, msg_socket)
    os.unlink(run_desc_filepath)
    run_script_filepath = _create_run_script(
        run_date, run_type, run_dir, run_desc_filepath, host_name, config,
        msg_socket)
    run_process = _launch_run_script(
        run_type, run_script_filepath, host_name, config, msg_socket)
    if run_type != 'nowcast-green':
        watcher_process = _launch_run_watcher(
            run_type, run_process, host_name, config, msg_socket)
        watcher_pid = watcher_process.pid
    else:
        watcher_pid = None
    return {run_type: {
        'run dir': run_dir,
        'pid': run_process.pid,
        'watcher pid': watcher_pid,
        'run date': run_date.format('YYYY-MM-DD'),
    }}


def _log_msg(msg, level, config, msg_socket):
    logger.log(level, msg)
    lib.tell_manager(
        worker_name, 'log.{}'.format(level), config, logger, msg_socket, msg)


def _create_run_desc_file(
    run_date, run_type, host_name, config, msg_socket,
):
    dmy = run_date.format('DDMMMYY').lower()
    run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
    run_days = {
        'nowcast': run_date,
        'nowcast-green': run_date,
        'forecast': run_date.replace(days=1),
        'forecast2': run_date.replace(days=2),
    }
    host_run_config = config['run'][host_name]
    run_prep_dir = Path(host_run_config['run_prep_dir'])
    restart_timestep = _update_time_namelist(
        run_date, run_type, host_run_config)
    run_desc = _run_description(
        run_days[run_type], run_type, run_id, restart_timestep, host_name,
        config)
    run_desc_filepath = run_prep_dir/'{}.yaml'.format(run_id)
    with open(run_desc_filepath, 'wt') as f:
        yaml.dump(run_desc, f, default_flow_style=False)
    _log_msg(
        '{}: run description file: {}'.format(run_type, run_desc_filepath),
        'debug', config, msg_socket)
    return run_desc_filepath


def _update_time_namelist(run_date, run_type, host_run_config):
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
    prev_run_namelist = namelist2dict(results_dir/dmy/'namelist')
    prev_it000 = prev_run_namelist['namrun'][0]['nn_it000']
    prev_itend = prev_run_namelist['namrun'][0]['nn_itend']
    prev_date0 = prev_run_namelist['namrun'][0]['nn_date0']
    run_prep_dir = Path(host_run_config['run_prep_dir'])
    namelist_domain = namelist2dict(
        run_prep_dir/'../SS-run-sets/SalishSea/nemo3.6/namelist.domain')
    rdt = namelist_domain['namdom'][0]['rn_rdt']
    timesteps_per_day = 86400 / rdt
    namelist_time = run_prep_dir/'namelist.time'
    with open(namelist_time, 'rt') as f:
        lines = f.readlines()
    new_lines, restart_timestep = _calc_new_namelist_lines(
        run_type, prev_it000, prev_itend, prev_date0, timesteps_per_day, lines)
    with open(namelist_time, 'wt') as f:
        f.writelines(new_lines)
    return restart_timestep


def _calc_new_namelist_lines(
    run_type, prev_it000, prev_itend, prev_date0, timesteps_per_day, lines,
):
    it000_line, it000 = _get_namelist_value('nn_it000', lines)
    itend_line, itend = _get_namelist_value('nn_itend', lines)
    run_duration = RUN_DURATIONS[run_type]
    new_it000 = (
        int(prev_it000 + (prev_itend - prev_it000 + 1) / run_duration)
        if run_type == 'forecast2'
        else prev_itend + 1)
    lines[it000_line] = lines[it000_line].replace(it000, str(new_it000))
    restart_timestep = new_it000 - 1
    new_itend = int(restart_timestep + (run_duration * timesteps_per_day))
    lines[itend_line] = lines[itend_line].replace(itend, str(new_itend))
    date0_line, date0 = _get_namelist_value('nn_date0', lines)
    date_format = 'YYYYMMDD'
    new_date0 = arrow.get(date0, date_format).replace(days=+1)
    lines[date0_line] = lines[date0_line].replace(
        date0, new_date0.format(date_format))
    return lines, restart_timestep


def _get_namelist_value(key, lines):
    line_index = [
        i for i, line in enumerate(lines)
        if line.strip() and line.split()[0] == key][-1]
    value = lines[line_index].split()[2]
    return line_index, value


def _run_description(
    run_date, run_type, run_id, restart_timestep, host_name, config
):
    host_run_config = config['run'][host_name]
    restart_dirs = {
        # run-type: results dir containing restart file(s)
        'nowcast': Path(host_run_config['results']['nowcast']),
        'nowcast-green': Path(host_run_config['results']['nowcast-green']),
        'forecast': Path(host_run_config['results']['nowcast']),
        'forecast2': Path(host_run_config['results']['forecast']),
    }
    prev_run_dmys = {
        # run-type: previous run's ddmmmyy results directory name
        'nowcast': run_date.replace(days=-1).format('DDMMMYY').lower(),
        'nowcast-green': run_date.replace(days=-1).format('DDMMMYY').lower(),
        'forecast': run_date.replace(days=-1).format('DDMMMYY').lower(),
        'forecast2': run_date.replace(days=-2).format('DDMMMYY').lower(),
    }
    restart_filepaths = {
        'restart.nc': {
            'link to': str(Path(
                restart_dirs[run_type]/prev_run_dmys[run_type] /
                'SalishSea_{:08d}_restart.nc'.format(restart_timestep)))
        }}
    if run_type == 'nowcast-green':
        restart_filepaths['restart_trc.nc'] = {
            'link to': str(Path(
                restart_dirs[run_type]/prev_run_dmys[run_type] /
                'SalishSea_{:08d}_restart_trc.nc'.format(restart_timestep)))
            }
    run_prep_dir = Path(host_run_config['run_prep_dir'])
    NEMO_config_name = config['run_types'][run_type]
    walltime = host_run_config.get('walltime')
    nowcast_dir = Path(host_run_config['nowcast_dir'])
    forcing = {
        'NEMO-atmos': {
            'link to': str(nowcast_dir/'NEMO-atmos'),
            'check link': {
                'type': 'atmospheric',
                'namelist filename': 'namelist_cfg',
            }},
        'open_boundaries': {'link to': str(nowcast_dir/'open_boundaries/')},
        'rivers': {'link to': str(nowcast_dir/'rivers/')},
    }
    forcing.update(restart_filepaths)
    run_sets_dir = run_prep_dir/'../SS-run-sets/SalishSea/nemo3.6/'
    namelists = {
        'namelist_cfg': [
            './namelist.time',
            str(run_sets_dir/'nowcast/namelist.domain'),
            str(run_sets_dir/'nowcast/namelist.surface'),
            str(run_sets_dir/'nowcast/namelist.lateral'),
            str(run_sets_dir/'nowcast/namelist.bottom'),
            str(run_sets_dir/'nowcast/namelist.tracer'),
            str(run_sets_dir/'nowcast/namelist.dynamics'),
            str(run_sets_dir/'nowcast/namelist.vertical'),
            str(run_sets_dir/'nowcast/namelist.compute'),
        ],
        'namelist_top_cfg': [str(run_sets_dir/'nowcast/namelist_top_cfg')],
        'namelist_pisces_cfg': [
            str(run_sets_dir/'nowcast/namelist_pisces_cfg')],
    }
    run_desc = salishsea_cmd.api.run_description(
        run_id=run_id,
        config_name=NEMO_config_name,
        mpi_decomposition=host_run_config['mpi decomposition'],
        walltime=walltime,
        NEMO_code=str(run_prep_dir/'../NEMO-3.6-code/'),
        XIOS_code=str(run_prep_dir/'../XIOS-code/'),
        forcing_path=str(run_prep_dir/'../NEMO-forcing/'),
        runs_dir=str(run_prep_dir/'../SalishSea/'),
        forcing=forcing,
        namelists=namelists,
    )
    try:
        run_desc['grid']['bathymetry'] = host_run_config['bathymetry']
    except KeyError:
        run_desc['grid']['bathymetry'] = config['bathymetry']
    run_desc['output']['domain'] = str(
        run_prep_dir/'../SS-run-sets/SalishSea/nemo3.6/domain_def.xml')
    run_desc['output']['fields'] = str(
        run_prep_dir/'../SS-run-sets/SalishSea/nemo3.6/nowcast/field_def.xml')
    return run_desc


def _create_run_script(
    run_date, run_type, run_dir, run_desc_filepath, host_name, config,
    msg_socket,
):
    namelist = namelist2dict(os.path.join(run_dir, 'namelist'))
    cores = namelist['nammpp'][0]['jpnij']
    host_run_config = config['run'][host_name]
    dmy = run_date.format('DDMMMYY').lower()
    results_dir = os.path.join(host_run_config['results'][run_type], dmy)
    script = _build_script(run_desc_filepath, cores, results_dir)
    run_script_filepath = os.path.join(run_dir, 'SalishSeaNEMO.sh')
    with open(run_script_filepath, 'wt') as f:
        f.write(script)
    lib.fix_perms(run_script_filepath, mode=lib.PERMS_RWX_RWX_R)
    _log_msg(
        '{}: run script: {}'.format(run_type, run_script_filepath),
        'debug', config, msg_socket)
    return run_script_filepath


def _launch_run_script(
    run_type, run_script_filepath, host_name, config, msg_socket,
):
    _log_msg(
        '{}: launching {} on {}'
        .format(run_type, run_script_filepath, host_name),
        'info', config, msg_socket)
    cmd = shlex.split(run_script_filepath)
    _log_msg(
        '{}: running command in subprocess: {}'.format(run_type, cmd),
        'debug', config, msg_socket)
    run_process = subprocess.Popen(cmd)
    _log_msg(
        '{}: run pid: {.pid}'.format(run_type, run_process),
        'debug', config, msg_socket)
    return run_process


def _launch_run_watcher(run_type, run_process, host_name, config, msg_socket):
    _log_msg(
        'launching watch_NEMO worker on {}'.format(run_type, host_name),
        'info', config, msg_socket)
    host_run_config = config['run'][host_name]
    cmd = [
        host_run_config['python'], '-m', 'nowcast.workers.watch_NEMO',
        host_run_config['config_file'], run_type, str(run_process.pid),
    ]
    _log_msg(
        '{}: running command in subprocess: {}'.format(run_type, cmd),
        'debug', config, msg_socket)
    watcher_process = subprocess.Popen(cmd)
    _log_msg(
        '{}: watcher pid: {.pid}'.format(run_type, watcher_process),
        'debug', config, msg_socket)
    return watcher_process


if __name__ == '__main__':
    main()
