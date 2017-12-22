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
"""Salish Sea WaveWatch3 forecast worker that prepares the temporary run
directory and bash run script for a prelim-forecast or forecast run on the 
ONC cloud, and launches the run.
"""
import logging
import os
from pathlib import Path
import shlex
import subprocess
import uuid

import arrow
from nemo_nowcast import NowcastWorker
from nemo_nowcast.fileutils import FilePerms

NAME = 'run_ww3'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.run_ww3 --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'host_name', help='Name of the host to execute the run on'
    )
    worker.cli.add_argument(
        'run_type',
        choices={'forecast2', 'forecast'},
        help='''
        Type of run to execute:
        'forecast2' means preliminary forecast run (after NEMO forecast2 run),
        'forecast' means updated forecast run (after NEMO forecast run)
        ''',
    )
    worker.cli.add_date_option(
        '--run-date',
        default=arrow.now().floor('day'),
        help='Date to execute the run for.'
    )
    worker.run(run_ww3, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f'{parsed_args.run_type} WaveWatch3 run for '
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
        f'{parsed_args.run_type} WaveWatch3 run for '
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


def run_ww3(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args: 
    :param :py:class:`nemo_nowcast.Config` config:
    
    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    run_dir_path = _build_tmp_run_dir(run_date, run_type, config)
    logger.info(f'Created run directory {run_dir_path}')
    results_path = Path(config['wave forecasts']['results'][run_type])
    script = _build_run_script(
        run_date, run_type, run_dir_path, results_path, config
    )
    run_script_path = _write_run_script(run_type, script, run_dir_path)
    run_exec_cmd = _launch_run(run_type, run_script_path, host_name)
    checklist = {
        run_type: {
            'host': host_name,
            'run dir': os.fspath(run_dir_path),
            'run exec cmd': run_exec_cmd,
            'run date': run_date.format('YYYY-MM-DD'),
        }
    }
    return checklist


def _build_tmp_run_dir(run_date, run_type, config):
    """
    :param :py:class:`arrow.Arrow` run_date:
    :param str run_type:
    :param :py:class:`nemo_nowcast.Config` config:
    
    :return: Temporary run directory
    :rtype: :py:class:`pathlib.Path`
    """
    run_prep_path = Path(config['wave forecasts']['run prep dir'])
    run_dir_path = _make_run_dir(run_prep_path)
    _create_symlinks(run_date, run_type, run_prep_path, run_dir_path, config)
    _write_ww3_input_files(run_date, run_type, run_dir_path)
    return run_dir_path


def _make_run_dir(run_prep_dir):
    """
    :param :py:class:`pathlib.Path` run_prep_dir:
    
    :return: Temporary run directory
    :rtype: :py:class:`pathlib.Path`
    """
    run_dir_path = run_prep_dir / str(uuid.uuid1())
    run_dir_path.mkdir(mode=0o775)
    return run_dir_path


def _create_symlinks(run_date, run_type, run_prep_path, run_dir_path, config):
    """
    :param :py:class:`arrow.Arrow` run_date:
    :param str run_type:
    :param :py:class:`pathlib.Path` run_prep_path:
    :param :py:class:`pathlib.Path` run_dir_path:
    :param :py:class:`nemo_nowcast.Config` config:
    """
    for target in ('mod_def.ww3', 'wind', 'current'):
        (run_dir_path / target).symlink_to(run_prep_path / target)
    results_path = Path(config['wave forecasts']['results'][run_type])
    ddmmmyy = run_date.replace(days=-1).format('DDMMMYY').lower()
    prev_run_path = results_path / ddmmmyy
    (run_dir_path / 'restart.ww3').symlink_to(prev_run_path / 'restart001.ww3')


def _write_ww3_input_files(run_date, run_type, run_dir_path):
    """
    :param :py:class:`arrow.Arrow` run_date:
    :param str run_type: 
    :param :py:class:`pathlib.Path` run_dir_path:
    """
    ww3_input_files = {
        'ww3_prnc_wind.inp': _ww3_prnc_wind_contents,
        'ww3_prnc_current.inp': _ww3_prnc_current_contents,
        'ww3_shel.inp': _ww3_shel_contents,
        'ww3_ounf.inp': _ww3_ounf_contents,
        'ww3_ounp.inp': _ww3_ounp_contents,
    }
    for filename, contents_func in ww3_input_files.items():
        contents = contents_func(run_date, run_type)
        with (run_dir_path / filename).open('wt') as f:
            f.write(contents)
        logger.debug(f'created {run_dir_path/filename}')


def _ww3_prnc_wind_contents(run_date, run_type):
    """
    :param :py:class:`arrow.Arrow` run_date:
    :param str run_type: 
    
    :return: ww3_prnc_wind.inp file contents
    :rtype: str 
    """
    start_date = run_date.format('YYYYMMDD')
    contents = f'''$ WAVEWATCH III NETCDF Field preprocessor input \
ww3_prnc_wind.inp
$
$ Forcing type, grid type, time in file, header 
   'WND' 'LL' T T
$
$ Dimension variable names
  x y
$
$ Wind component variable names
  u_wind v_wind
$
$ Forcing source file path/name
$ File is produced by make_ww3_wind_file worker
  'wind/SoG_wind_{start_date}.nc'
'''

    return contents


def _ww3_prnc_current_contents(run_date, run_type):
    """
    :param :py:class:`arrow.Arrow` run_date:
    :param str run_type: 
    
    :return: ww3_prnc_current.inp file contents
    :rtype: str 
    """
    start_date = run_date.format('YYYYMMDD')
    contents = f'''$ WAVEWATCH III NETCDF Field preprocessor input \
ww3_prnc_current.inp
$
$ Forcing type, grid type, time in file, header 
  'CUR' 'LL' T T
$ Name of dimensions
$
  x y
$
$ Sea water current component variable names
  u_current v_current
$
$ Forcing source file path/name
$ File is produced by make_ww3_current_file worker
  'current/SoG_current_{start_date}.nc'
'''

    return contents


def _ww3_shel_contents(run_date, run_type):
    """
    :param :py:class:`arrow.Arrow` run_date:
    :param str run_type:
    
    :return: ww3_shel.inp file contents
    :rtype: str 
    """
    start_date = run_date.format('YYYYMMDD')
    restart_date = run_date.replace(days=+1).format('YYYYMMDD')
    end_date = run_date.replace(days=+2).format('YYYYMMDD')
    end_time = '120000' if run_type == 'forecast' else '060000'
    contents = f'''$ WAVEWATCH III shell input file
$
$ Forcing/inputs to use
  F F  Water levels w/ homogeneous field data
  T F  Currents w/ homogeneous field data
  T F  Winds w/ homogeneous field data
  F    Ice concentration
  F    Assimilation data : Mean parameters
  F    Assimilation data : 1-D spectra
  F    Assimilation data : 2-D spectra.
$
   {start_date} 000000  Start time (YYYYMMDD HHmmss)
   {end_date} {end_time}  End time (YYYYMMDD HHmmss)
$
$ Output server mode
  2  dedicated process
$
$ Field outputs
$ Start time (YYYYMMDD HHmmss), Interval (s), End time (YYYYMMDD HHmmss)
  {start_date} 000000 1800 {end_date} {end_time}
$ Fields
  N  by name
  HS LM WND CUR FP T02 DIR DP WCH WCC TWO FOC USS
$
$ Point outputs
$ Start time (YYYYMMDD HHmmss), Interval (s), End time (YYYYMMDD HHmmss)
  {start_date} 000000 600 {end_date} {end_time}
$ longitude, latitude, 10-char name
   236.52 48.66 'C46134PatB'
   236.27 49.34 'C46146HalB'
   235.01 49.91 'C46131SenS'
   0.0 0.0 'STOPSTRING'
$
$ Along-track output (required placeholder for unused feature)
$ Start time (YYYYMMDD HHmmss), Interval (s), End time (YYYYMMDD HHmmss)
  {start_date} 000000 0 {end_date} {end_time}
$
$ Restart files
$ Start time (YYYYMMDD HHmmss), Interval (s), End time (YYYYMMDD HHmmss)
  {restart_date} 000000 3600 {restart_date} 000000
$
$ Boundary data (required placeholder for unused feature)
$ Start time (YYYYMMDD HHmmss), Interval (s), End time (YYYYMMDD HHmmss)
  {start_date} 000000 0 {end_date} {end_time}
$
$ Separated wave field data (required placeholder for unused feature)
$ Start time (YYYYMMDD HHmmss), Interval (s), End time (YYYYMMDD HHmmss)
  {start_date} 000000 0 {end_date} {end_time}
$
$ Homogeneous field data (required placeholder for unused feature)
  ’STP’
'''

    return contents


def _ww3_ounf_contents(run_date, run_type):
    """
    :param run_date: :py:class:`arrow.Arrow`
    :param str run_type: 
    
    :return: ww3_ounf.inp file contents
    :rtype: str 
    """
    start_date = run_date.format('YYYYMMDD')
    contents = f'''$ WAVEWATCH III NETCDF Grid output post-processing
$
$ First output time (YYYYMMDD HHmmss), output increment (s), number of output times
  {start_date} 000000 1800 120
$
$ Fields
  N  by name
  HS LM WND CUR FP T02 DIR DP WCH WCC TWO FOC USS
$
$ netCDF4 output
$ real numbers
$ swell partitions
$ one file
  4 
  4
  0 1 2
  T
$
$ File prefix
$ number of characters in date
$ IX, IY range
$
  SoG_ww3_fields_
  8
  1 1000000 1 1000000
'''

    return contents


def _ww3_ounp_contents(run_date, run_type):
    """
    :param str run_type: 
    :param run_date: :py:class:`arrow.Arrow`

    :return: ww3_ounp.inp file contents
    :rtype: str 
    """
    start_date = run_date.format('YYYYMMDD')
    contents = f'''$ WAVEWATCH III NETCDF Point output post-processing
$
$ First output time (YYYYMMDD HHmmss), output increment (s), number of output times
  {start_date} 000000 600 360
$
$ All points defined in ww3_shel.inp
  -1
$ File prefix
$ number of characters in date
$ netCDF4 output
$ one file, max number of points to process
$ tables of mean parameters
$ WW3 global attributes
$ time,station dimension order
$ WMO standard output
  SoG_ww3_points_
  8
  4 
  T 100
  2
  0
  T
  6
'''

    start_date = run_date.format('YYYYMMDD')
    return contents


def _build_run_script(run_date, run_type, run_dir_path, results_path, config):
    """
    :param :py:class:`arrow.Arrow` run_date: 
    :param str run_type: 
    :param :py:class:`pathlib.Path` run_dir_path: 
    :param :py:class:`pathlib.Path` results_path: 
    :param :py:class:`nemo_nowcast.Config` config: 
    
    :return: wwatch3 run set-up and execution script
    :rtype: str 
    """
    script = (
        '#!/bin/bash\n'
        'set -e  # abort on first error\n'
        'set -u  # abort if undefinded variable is encountered\n'
    )
    script = '\n'.join((
        script, '{defns}\n'
        '{prepare}\n'
        '{execute}\n'
        '{netcdf_output}\n'
        '{cleanup}'.format(
            defns=_definitions(
                run_date, run_type, run_dir_path, results_path, config
            ),
            prepare=_prepare(),
            execute=_execute(run_date),
            netcdf_output=_netcdf_output(run_date),
            cleanup=_cleanup(),
        )
    ))
    return script


def _definitions(run_date, run_type, run_dir_path, results_path, config):
    """
    :param :py:class:`arrow.Arrow` run_date: 
    :param str run_type: 
    :param :py:class:`pathlib.Path` run_dir_path: 
    :param :py:class:`pathlib.Path` results_path: 
    :param :py:class:`nemo_nowcast.Config` config: 
    
    :return: Definitions section of wwatch3 run set-up and execution script
    :rtype: str 
    """
    ddmmmyy = run_date.format('DDMMMYY').lower()
    wwatch3_exe_path = config['wave forecasts']['wwatch3 exe path']
    salishsea_cmd = config['wave forecasts']['salishsea cmd']
    defns = (
        f'RUN_ID="{ddmmmyy}ww3-{run_type}"\n'
        f'WORK_DIR="{run_dir_path}"\n'
        f'RESULTS_DIR="{results_path/ddmmmyy}"\n'
        f'WW3_EXE="{wwatch3_exe_path}"\n'
        f'MPIRUN="mpirun --hostfile ${{HOME}}/mpi_hosts"\n'
        f'GATHER="{salishsea_cmd} gather"\n'
    )
    return defns


def _prepare():
    """
    :return: Preparations section of wwatch3 run set-up and execution script
    :rtype: str 
    """
    preparations = (
        'mkdir -p ${RESULTS_DIR}\n'
        '\n'
        'cd ${WORK_DIR}\n'
        'echo "working dir: $(pwd)" >>${RESULTS_DIR}/stdout\n'
        '\n'
        'echo "Starting wind.nc file creation at $(date)" '
        '>>${RESULTS_DIR}/stdout\n'
        'ln -s ww3_prnc_wind.inp ww3_prnc.inp && \\\n'
        '${WW3_EXE}/ww3_prnc '
        '>>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\\n'
        'rm -f ww3_prnc.inp\n'
        'echo "Ending wind.nc file creation at $(date)" '
        '>>${RESULTS_DIR}/stdout\n'
        '\n'
        'echo "Starting current.nc file creation at $(date)" '
        '>>${RESULTS_DIR}/stdout\n'
        'ln -s ww3_prnc_current.inp ww3_prnc.inp && \\\n'
        '${WW3_EXE}/ww3_prnc '
        '>>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\\n'
        'rm -f ww3_prnc.inp\n'
        'echo "Ending current.nc file creation at $(date)" '
        '>>${RESULTS_DIR}/stdout\n'
    )
    return preparations


def _execute(run_date):
    """
    :param :py:class:`arrow.Arrow` run_date:

    :return: Execution section of wwatch3 run set-up and execution script
    :rtype: str 
    """
    start_date = run_date.format('YYYYMMDD')
    execution = (
        'echo "Starting run at $(date)" >>${RESULTS_DIR}/stdout\n'
        '${MPIRUN} -np 85 --bind-to-core ${WW3_EXE}/ww3_shel \\\n'
        '  >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\\n'
        'mv log.ww3 ww3_shel.log && \\\n'
        'rm current.ww3 wind.ww3 && \\\n'
        f'rm current/SalishSea_1h_{start_date}_{start_date}_grid_[UV].nc && \\\n'
        f'rm current/SoG_current_{start_date}.nc && \\\n'
        f'rm wind/SoG_wind_{start_date}.nc\n'
        'echo "Ended run at $(date)" >>${RESULTS_DIR}/stdout\n'
    )
    return execution


def _netcdf_output(run_date):
    """
    :param :py:class:`arrow.Arrow` run_date: 
    
    :return: netCDF output files section of wwatch3 run set-up and execution 
             script
    :rtype: str 
    """
    start_yyyymmdd = run_date.format('YYYYMMDD')
    end_yyyymmdd = run_date.replace(days=+2).format('YYYYMMDD')
    fields_files = ' '.join(
        f'SoG_ww3_fields_{day.format("YYYYMMDD")}.nc'
        for day in
        arrow.Arrow.range('day', run_date, run_date.replace(days=+2))
    )
    points_files = ' '.join(
        f'SoG_ww3_points_{day.format("YYYYMMDD")}_tab.nc'
        for day in
        arrow.Arrow.range('day', run_date, run_date.replace(days=+2))
    )
    output_to_netcdf = (
        'echo "Starting netCDF4 fields output at $(date)" '
        '>>${RESULTS_DIR}/stdout\n'
        '${WW3_EXE}/ww3_ounf >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\\n'
        f'ncrcat -4 -L4 -o SoG_ww3_fields_{start_yyyymmdd}_{end_yyyymmdd}.nc \\\n'
        f'  {fields_files} \\\n'
        '  >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\\n'
        f'rm {fields_files} && \\\n'
        'rm out_grd.ww3\n'
        'echo "Ending netCDF4 fields output at $(date)" '
        '>>${RESULTS_DIR}/stdout\n'
        '\n'
        'echo "Starting netCDF4 points output at $(date)" '
        '>>${RESULTS_DIR}/stdout\n'
        '${WW3_EXE}/ww3_ounp >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\\n'
        f'ncrcat -4 -L4 -o SoG_ww3_points_{start_yyyymmdd}_{end_yyyymmdd}.nc \\\n'
        f'  {points_files} \\\n'
        '  >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\\n'
        f'rm {points_files} && \\\n'
        'rm out_pnt.ww3\n'
        'echo "Ending netCDF4 points output at $(date)" '
        '>>${RESULTS_DIR}/stdout\n'
    )
    return output_to_netcdf


def _cleanup():
    """
    :return: clean-up section of wwatch3 run set-up and execution script
    :rtype: str 
    """
    cleanup = (
        'echo "Results gathering started at $(date)" >>${RESULTS_DIR}/stdout\n'
        '${GATHER} ${RESULTS_DIR} --debug >>${RESULTS_DIR}/stdout\n'
        'echo "Results gathering ended at $(date)" >>${RESULTS_DIR}/stdout\n'
        '\n'
        'echo "Deleting run directory" >>${RESULTS_DIR}/stdout\n'
        'rmdir $(pwd)\n'
        'echo "Finished at $(date)" >>${RESULTS_DIR}/stdout\n'
    )
    return cleanup


def _write_run_script(run_type, script, run_dir_path):
    """
    :param str run_type: 
    :param str script: 
    :param :py:class:`pathlib.Path` run_dir_path: 
    
    :return: wwatch3 run set-up and execution script path
    :rtype: :py:class:`pathlib.Path`
    """
    run_script_path = run_dir_path / 'SoGWW3.sh'
    with run_script_path.open('wt') as f:
        f.write(script)
    run_script_path.chmod(FilePerms(user='rwx', group='rwx', other='r'))
    logger.debug(f'wwatch3-{run_type}: run script: {run_script_path}')
    return run_script_path


def _launch_run(run_type, run_script_path, host_name):
    """
    :param str run_type: 
    :param :py:class:`pathlib.Path` run_script_path: 
    :param str host_name:
     
    :return: wwatch3 run set-up and execution command
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
