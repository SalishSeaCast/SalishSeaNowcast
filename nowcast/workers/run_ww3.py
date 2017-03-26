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
import uuid
from pathlib import Path
import shlex
import subprocess

import arrow
from nemo_nowcast import (
    NowcastWorker,
    WorkerError,
)


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
        'host_name',
        help='Name of the host to execute the run on')
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
        '--run-date', default=arrow.now().floor('day'),
        help='Date to execute the run for.')
    worker.run(run_ww3, success, failure)


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


def run_ww3(parsed_args, config, *args):
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    run_dir_path = _build_tmp_run_dir(run_date, run_type, config)
    logger.info(f'Created run directory {run_dir_path}')
    run_pid = _launch_run()
    checklist = {
        run_type: {
            'host': host_name,
            'run date': run_date.format('YYYY-MM-DD'),
            'run dir': os.fspath(run_dir_path),
            'pid': run_pid,
        }
    }
    return checklist


def _build_tmp_run_dir(run_date, run_type, config):
    """
    :type run_date: :py:class:`arrow.Arrow`
    :type run_type: str
    :type config: :py:class:`nemo_nowcast.Config`
    :rtype: :py:class:`pathlib.Path`
    """
    run_prep_path = Path(config['wave forecasts']['run prep dir'])
    run_dir_path = _make_run_dir(run_prep_path)
    _create_symlinks(run_date, run_type, run_prep_path, run_dir_path, config)
    _write_ww3_input_files(run_date, run_dir_path)
    return run_dir_path


def _make_run_dir(run_prep_dir):
    """
    :type run_prep_dir: :py:class:`pathlib.Path`
    """
    run_dir_path = run_prep_dir/str(uuid.uuid1())
    run_dir_path.mkdir(mode=0o775)
    return run_dir_path


def _create_symlinks(run_date, run_type, run_prep_path, run_dir_path, config):
    """
    :type run_date: :py:class:`arrow.Arrow`
    :type run_type: str
    :type run_prep_path: :py:class:`pathlib.Path`
    :type run_dir_path: :py:class:`pathlib.Path`
    :type config: :py:class:`nemo_nowcast.Config`
    """
    for target in ('mod_def.ww3', 'wind', 'current'):
        (run_dir_path / target).symlink_to(run_prep_path / target)
    results_path = Path(config['wave forecasts']['results'][run_type])
    ddmmmyy = run_date.replace(days=-1).format('DDMMMYY').lower()
    prev_run_path = results_path / ddmmmyy
    (run_dir_path / 'restart.ww3').symlink_to(prev_run_path / 'restart001.ww3')


def _write_ww3_input_files(run_date, run_dir_path):
    """
    :type run_date: :py:class:`arrow.Arrow`
    :type run_dir_path: :py:class:`pathlib.Path`
    """
    ww3_input_files = {
        'ww3_prnc_wind.inp': _ww3_prnc_wind_contents,
        'ww3_prnc_current.inp': _ww3_prnc_current_contents,
        'ww3_shel.inp': _ww3_shel_contents,
        'ww3_ounf.inp': _ww3_ounf_contents,
        'ww3_ounp.inp': _ww3_ounp_contents,
    }
    for filename, contents_func in ww3_input_files.items():
        contents = contents_func(run_date)
        with (run_dir_path / filename).open('wt') as f:
            f.write(contents)


def _ww3_prnc_wind_contents(run_date):
    """
    :type run_date: :py:class:`arrow.Arrow`
    """
    start_date = run_date.format('YYYYMMDD')
    contents = f'''$ WAVEWATCH III NETCDF Field preprocessor input 
    ww3_prnc_wind.inp
$
$ Forcing type, grid type, time in file, header 
   'WND' 'LL' T T
$
$ Dimension variable names
  longitude latitude
$
$ Wind component variable names
  u_wind v_wind
$
$ Forcing source file path/name
$ File is produced by make_ww3_wind_file worker
  'wind/SoG_wind_{start_date}.nc'
'''
    return contents


def _ww3_prnc_current_contents(run_date):
    """
    :type run_date: :py:class:`arrow.Arrow`
    """
    start_date = run_date.format('YYYYMMDD')
    contents = f'''$ WAVEWATCH III NETCDF Field preprocessor input ww3_prnc_current.inp
$
$ Forcing type, grid type, time in file, header 
  'CUR' 'LL' T T
$ Name of dimensions
$
  longitude latitude
$
$ Sea water current component variable names
  UCUR VCUR
$
$ Forcing source file path/name
$ File is produced by make_ww3_current_file worker
  'current/SoG_current_{start_date}.nc'
'''
    return contents


def _ww3_shel_contents(run_date):
    """
    :type run_date: :py:class:`arrow.Arrow`
    """
    start_date = run_date.format('YYYYMMDD')
    end_date = run_date.replace(days=+2).format('YYYYMMDD')
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
   {end_date} 233000  End time (YYYYMMDD HHmmss)
$
$ Output server mode
  2  dedicated process
$
$ Field outputs
$ Start time (YYYYMMDD HHmmss), Interval (s), End time (YYYYMMDD HHmmss)
  {start_date} 000000 1800 {end_date} 233000
$ Fields
  N  by name
  HS LM WND CUR FP T02 DIR DP WCH WCC TWO FCO USS
$
$ Point outputs
$ Start time (YYYYMMDD HHmmss), Interval (s), End time (YYYYMMDD HHmmss)
  {start_date} 000000 1800 {end_date} 233000
$ longitude, latitude, 10-char name
   236.52 48.66 'C46134PatB'
   236.27 49.34 'C46146HalB'
   235.01 49.91 'C46131SenS'
   0.0 0.0 'STOPSTRING'
$
$ Along-track output (required placeholder for unused feature)
$ Start time (YYYYMMDD HHmmss), Interval (s), End time (YYYYMMDD HHmmss)
  {start_date} 000000 0 {end_date} 233000
$
$ Restart files
$ Start time (YYYYMMDD HHmmss), Interval (s), End time (YYYYMMDD HHmmss)
  {end_date} 233000 3600 {end_date} 233000
$
$ Boundary data (required placeholder for unused feature)
$ Start time (YYYYMMDD HHmmss), Interval (s), End time (YYYYMMDD HHmmss)
  {start_date} 000000 0 {end_date} 233000
$
$ Separated wave field data (required placeholder for unused feature).
$ Start time (YYYYMMDD HHmmss), Interval (s), End time (YYYYMMDD HHmmss)
  {start_date} 000000 0 {end_date} 233000
$
$ Homogeneous field data (required placeholder for unused feature)
  ’STP’
'''
    return contents


def _ww3_ounf_contents(run_date):
    """
    :type run_date: :py:class:`arrow.Arrow`
    """
    start_date = run_date.format('YYYYMMDD')
    contents = f'''$ WAVEWATCH III NETCDF Grid output post-processing
$
$ First output time (YYYYMMDD HHmmss), output increment (s), number of output times
  {start_date} 000000 1800 144
$
$ Fields
  N  by name
  HS LM WND CUR FP T02 DIR DP WCH WCC TWO FCO USS
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
  SoG_ww3_
  8
  1 1000000 1 1000000
'''
    return contents


def _ww3_ounp_contents(run_date):
    """
    :type run_date: :py:class:`arrow.Arrow`
    """
    contents = f'''$ WAVEWATCH III NETCDF Point output post-processing
$
$ First output time (YYYYMMDD HHmmss), output increment (s), number of output times
  {start_date} 000000 1800 144
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
  SoG_ww3_
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


def _launch_run():
    run_pid = ''
    return run_pid


if __name__ == '__main__':
    main()  # pragma: no cover
