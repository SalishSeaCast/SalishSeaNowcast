
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

"""Salish Sea NEMO nowcast worker that prepares the YAML run description
file and bash run script for a nowcast, forecast or forecast2 run in the
cloud computing facility, and launches the run.
"""
from __future__ import division

import argparse
import datetime
import logging
import os
import shlex
import subprocess
import traceback

import yaml
import zmq

import salishsea_cmd.api
import salishsea_cmd.lib
from salishsea_tools.namelist import namelist2dict
from salishsea_tools.nowcast import lib


worker_name = lib.get_module_name()

logger = logging.getLogger(worker_name)

context = zmq.Context()


TIMESTEPS_PER_DAY = 8640
NOWCAST_DURATION = 1  # day
FORECAST_DURATION = 1.25  # days
FORECAST2_START = 2  # days after nowcast start, it needs to an integer
FORECAST2_DURATION = 1.25  # days


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

    lib.configure_logging(config, logger, parsed_args.debug, email=False)
    logger.debug('running in process {}'.format(os.getpid()))
    logger.debug('read config from {.config_file}'.format(parsed_args))
    # Add nowcast-style handlers to salishsea_cmd api and prepare loggers
    for module in 'api prepare'.split():
        cmd_logger = logging.getLogger('salishsea_cmd.{}'.format(module))
        lib.configure_logging(
            config, cmd_logger, parsed_args.debug, email=False)

    lib.install_signal_handlers(logger, context)
    socket = lib.init_zmq_req_rep_worker(
        context, config, logger, config['zmq']['server'])
    # Do the work
    host_name = config['run']['cloud host']
    try:
        checklist = run_NEMO(host_name, parsed_args.run_type, config, socket)
        logger.info(
            '{.run_type} NEMO run in {host_name} started'
            .format(parsed_args, host_name=host_name))
        # Exchange success messages with the nowcast manager process
        lib.tell_manager(
            worker_name, 'success', config, logger, socket, checklist)
    except lib.WorkerError:
        logger.critical(
            '{.run_type} NEMO run in {host_name} failed'
            .format(parsed_args, host_name=host_name))
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
    logger.debug('task completed; shutting down')


def configure_argparser(prog, description, parents):
    parser = argparse.ArgumentParser(
        prog=prog, description=description, parents=parents)
    parser.add_argument(
        'run_type', choices=set(('nowcast', 'forecast', 'forecast2')),
        help='Type of run to execute.'
    )
    return parser


def run_NEMO(host_name, run_type, config, socket):
    host = config['run'][host_name]

    # Create the run description data structure and dump it to a YAML file
    if run_type == 'nowcast':
        run_date = datetime.date.today()
    else:
        # Get date that nowcast was run on
        run_info = lib.tell_manager(
            worker_name, 'need', config, logger, socket, 'NEMO run')
        run_date = datetime.datetime.strptime(
            run_info['nowcast']['run_date'], '%Y-%m-%d').date()
    dmy = run_date.strftime('%d%b%y').lower()
    run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
    run_days = {
        'nowcast': run_date,
        'forecast': run_date + datetime.timedelta(days=1),
        'forecast2': run_date + datetime.timedelta(days=2),
    }
    os.chdir(host['run_prep_dir'])
    restart_timestep = update_time_namelist(host, run_type, run_date)
    run_desc = run_description(
        host, run_type, run_days[run_type], run_id, restart_timestep)
    run_desc_file = '{}.yaml'.format(run_id)
    with open(run_desc_file, 'wt') as f:
        yaml.dump(run_desc, f, default_flow_style=False)
    msg = '{}: run description file: {}'.format(run_type, run_desc_file)
    logger.debug(msg)
    lib.tell_manager(worker_name, 'log.debug', config, logger, socket, msg)

    # Create and populate the temporary run directory
    run_dir = salishsea_cmd.api.prepare(run_desc_file, 'iodef.xml')
    msg = '{}: temporary run directory: {}'.format(run_type, run_dir)
    logger.debug(msg)
    lib.tell_manager(worker_name, 'log.debug', config, logger, socket, msg)
    os.unlink(run_desc_file)

    # Create the bash script to execute the run and gather the results
    namelist = namelist2dict(os.path.join(run_dir, 'namelist'))
    cores = namelist['nammpp'][0]['jpnij']
    results_dir = os.path.join(host['results'][run_type], dmy)
    os.chdir(run_dir)
    script = build_script(run_desc_file, cores, results_dir)
    with open('SalishSeaNEMO.sh', 'wt') as f:
        f.write(script)
    lib.fix_perms('SalishSeaNEMO.sh', mode=lib.PERMS_RWX_RWX_R)
    msg = (
        '{}: run script: {}'
        .format(run_type, os.path.join(run_dir, 'SalishSeaNEMO.sh')))
    logger.debug(msg)
    lib.tell_manager(worker_name, 'log.debug', config, logger, socket, msg)

    # Launch the bash script
    msg = (
        '{}: launching ./SalishSeaNEMO.sh run script on {}'
        .format(run_type, host_name))
    logger.info(msg)
    lib.tell_manager(worker_name, 'log.info', config, logger, socket, msg)
    cmd = shlex.split('./SalishSeaNEMO.sh')
    msg = '{}: running command in subprocess: {}'.format(run_type, cmd)
    logger.debug(cmd)
    lib.tell_manager(worker_name, 'log.debug', config, logger, socket, msg)
    run_process = subprocess.Popen(cmd)
    msg = '{}: run pid: {.pid}'.format(run_type, run_process)
    logger.debug(msg)
    lib.tell_manager(worker_name, 'log.debug', config, logger, socket, msg)

    # Launch the run watcher worker
    msg = 'launching watch_NEMO worker on {}'.format(run_type, host_name)
    logger.info(msg)
    lib.tell_manager(worker_name, 'log.info', config, logger, socket, msg)
    cmd = shlex.split(
        'python -m salishsea_tools.nowcast.workers.watch_NEMO '
        '/home/ubuntu/MEOPAR/nowcast/nowcast.yaml '
        '{run_type} {pid}'.format(run_type=run_type, pid=run_process.pid)
    )
    msg = '{}: running command in subprocess: {}'.format(run_type, cmd)
    logger.debug(cmd)
    lib.tell_manager(worker_name, 'log.debug', config, logger, socket, msg)
    watcher_process = subprocess.Popen(cmd)
    msg = '{}: watcher pid: {.pid}'.format(run_type, watcher_process)
    logger.debug(msg)
    lib.tell_manager(worker_name, 'log.debug', config, logger, socket, msg)
    return {run_type: {
        'run dir': run_dir,
        'pid': run_process.pid,
        'watcher pid': watcher_process.pid,
        'run_date': run_date.strftime('%Y-%m-%d'),
    }}


def update_time_namelist(host, run_type, run_day):
    namelist = os.path.join(host['run_prep_dir'], 'namelist.time')
    with open(namelist, 'rt') as f:
        lines = f.readlines()
    new_lines, restart_timestep = calc_new_namelist_lines(
        lines, run_type, run_day)
    with open(namelist, 'wt') as f:
        f.writelines(new_lines)
    return restart_timestep


def calc_new_namelist_lines(
    lines, run_type, run_day, timesteps_per_day=TIMESTEPS_PER_DAY,
):
    # Read indices & values of it000 and itend from namelist;
    # they are the lines we will update, actual values are irrelevant
    it000_line, it000 = get_namelist_value('nn_it000', lines)
    itend_line, itend = get_namelist_value('nn_itend', lines)
    # Read the date that the sequence of runs was started on;
    # used to calculate it000 and itend for the run we are preparing
    date0_line, date0 = get_namelist_value('nn_date0', lines)
    date0 = datetime.date(*map(int, [date0[:4], date0[4:6], date0[-2:]]))
    dt = run_day - date0
    new_values = {
        'nowcast': (
            int(dt.days * timesteps_per_day + 1),
            int((dt.days + NOWCAST_DURATION) * timesteps_per_day),
        ),
        'forecast': (
            int((dt.days + NOWCAST_DURATION) * timesteps_per_day + 1),
            int((dt.days + NOWCAST_DURATION + FORECAST_DURATION)
                * timesteps_per_day),
        ),
        'forecast2': (
            int((dt.days + FORECAST2_START) * timesteps_per_day + 1),
            int((dt.days + FORECAST2_START + FORECAST2_DURATION)
                * timesteps_per_day),
        ),
    }
    new_it000, new_itend = new_values[run_type]
    # Increment 1st and last time steps to values for the run
    lines[it000_line] = lines[it000_line].replace(it000, str(new_it000))
    lines[itend_line] = lines[itend_line].replace(itend, str(new_itend))
    # Calculate the restart file time step
    restart_timestep = new_it000 - 1
    return lines, restart_timestep


def get_namelist_value(key, lines):
    line_index = [
        i for i, line in enumerate(lines)
        if line.strip() and line.split()[0] == key][-1]
    value = lines[line_index].split()[2]
    return line_index, value


def run_description(host, run_type, run_day, run_id, restart_timestep):
    # Relative paths from MEOPAR/nowcast/

    if run_type != 'forecast2':
        restart_dir = host['results']['nowcast']
        prev_run_id = run_day - datetime.timedelta(days=1)
    else:
        restart_dir = host['results']['forecast']
        prev_run_id = run_day - datetime.timedelta(days=2)
    init_conditions = os.path.join(
        restart_dir,
        prev_run_id.strftime('%d%b%y').lower(),
        'SalishSea_{:08d}_restart.nc'.format(restart_timestep),
    )
    forcing_home = host['run_prep_dir']
    run_desc = salishsea_cmd.api.run_description(
        NEMO_code=os.path.abspath(os.path.join(forcing_home, '../NEMO-code/')),
        forcing=os.path.abspath(
            os.path.join(forcing_home, '../NEMO-forcing/')),
        runs_dir=os.path.abspath(os.path.join(forcing_home, '../SalishSea/')),
        init_conditions=os.path.abspath(init_conditions),
    )
    run_desc['run_id'] = run_id
    # Paths to run-specific forcing directories
    run_desc['forcing']['atmospheric'] = os.path.abspath(
        os.path.join(forcing_home, 'NEMO-atmos'))
    run_desc['forcing']['open boundaries'] = os.path.abspath(
        os.path.join(forcing_home, 'open_boundaries'))
    run_desc['forcing']['rivers'] = os.path.abspath(
        os.path.join(forcing_home, 'rivers'))
    # Paths to namelist section files
    run_desc['namelists'] = [
        os.path.abspath('namelist.time'),
        os.path.abspath('../SS-run-sets/SalishSea/namelist.domain'),
        os.path.abspath('../SS-run-sets/SalishSea/namelist.surface.nowcast'),
        os.path.abspath('../SS-run-sets/SalishSea/namelist.lateral.nowcast'),
        os.path.abspath('../SS-run-sets/SalishSea/namelist.bottom'),
        os.path.abspath('../SS-run-sets/SalishSea/namelist.tracers'),
        os.path.abspath('../SS-run-sets/SalishSea/namelist.dynamics'),
        os.path.abspath(
            '../SS-run-sets/SalishSea/namelist.compute.{}'
            .format(host['mpi decomposition'])),
    ]
    return run_desc


def build_script(run_desc_file, procs, results_dir):
    run_desc = salishsea_cmd.lib.load_run_desc(run_desc_file)
    script = (
        u'#!/bin/bash\n'
        u'\n'
    )
    # Variable definitions
    script += (
        u'{defns}\n'
        .format(
            defns=_definitions(
                run_desc['run_id'], run_desc_file, results_dir,
                procs))
    )
    # Run NEMO
    script += (
        u'mkdir -p ${RESULTS_DIR}\n'
        u'\n'
        u'echo "Starting run at $(date)" >>${RESULTS_DIR}/stdout\n'
        u'${MPIRUN} ./nemo.exe >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr\n'
        u'echo "Ended run at $(date)" >>${RESULTS_DIR}/stdout\n'
        u'\n'
    )
    # Gather per-processor results files and deflate the finished netCDF4
    # files
    script += (
        u'echo "Results gathering and deflation started at $(date)" >>${RESULTS_DIR}/stdout\n'
        u'${GATHER} ${GATHER_OPTS} ${RUN_DESC} ${RESULTS_DIR} >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr\n'
        u'echo "Results gathering and deflation ended at $(date) >>${RESULTS_DIR}/stdout"\n'
        u'\n'
    )
    # Delete the (now empty) working directory
    script += (
        u'echo "Deleting run directory >>${RESULTS_DIR}/stdout"\n'
        u'rmdir $(pwd)\n'
    )
    return script


def _definitions(run_id, run_desc_file, results_dir, procs):
    mpirun = 'mpirun -n {procs}'.format(procs=procs)
    mpirun = ' '.join((mpirun, '--hostfile', '${HOME}/mpi_hosts'))
    defns = (
        u'RUN_ID="{run_id}"\n'
        u'RUN_DESC="{run_desc_file}"\n'
        u'RESULTS_DIR="{results_dir}"\n'
        u'MPIRUN="{mpirun}"\n'
        u'GATHER="{salishsea_cmd} gather"\n'
        u'GATHER_OPTS="--no-compress"\n'
    ).format(
        run_id=run_id,
        run_desc_file=run_desc_file,
        results_dir=results_dir,
        mpirun=mpirun,
        salishsea_cmd='${HOME}/.local/bin/salishsea',
    )
    return defns


if __name__ == '__main__':
    main()
