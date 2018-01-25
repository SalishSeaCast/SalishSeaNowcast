# Copyright 2013-2017 The Salish Sea MEOPAR Contributors
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
"""Salish Sea nowcast worker that builds a new directory of symlinks to model
results files for the rolling forecast datasets and replaces the previous
rolling forecast directory with the new one.
"""
import logging
import os
from pathlib import Path
import shlex
import subprocess
import shutil

import arrow
from nemo_nowcast import NowcastWorker

NAME = 'update_forecast_datasets'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.update_forecast_datasets -h`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        'model',
        choices={'nemo'},
        help='Model to update the rolling forecast datasets for.',
    )
    worker.cli.add_argument(
        'run_type',
        choices={'forecast', 'forecast2'},
        help='''
        Type of run to update rolling forecast datasets for:
        'forecast' means afternoon updated forecast runs,
        'forecast2' means early morning preliminary forecast runs,
        '''
    )
    worker.cli.add_date_option(
        '--run-date',
        default=(arrow.now().floor('day')),
        help='Date of the run to update rolling forecast datasets for.'
    )
    worker.run(update_forecast_datasets, success, failure)


def success(parsed_args):
    model = parsed_args.model
    run_type = parsed_args.run_type
    ymd = parsed_args.run_date.format('YYYY-MM-DD')
    logger.info(
        f'{model} {ymd} {run_type} rolling forecast datasets updated',
        extra={
            'run_date': ymd,
            'model': model,
            'run_type': run_type,
        }
    )
    msg_type = f'success {model} {run_type}'
    return msg_type


def failure(parsed_args):
    model = parsed_args.model
    run_type = parsed_args.run_type
    ymd = parsed_args.run_date.format('YYYY-MM-DD')
    logger.critical(
        f'{model} {ymd} {run_type} rolling forecast datasets update failed',
        extra={
            'run_date': ymd,
            'model': model,
            'run_type': run_type,
        }
    )
    msg_type = f'failure {model} {run_type}'
    return msg_type


def update_forecast_datasets(parsed_args, config, *args):
    model = parsed_args.model
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    ddmmmyy = run_date.format('DDMMMYY').lower()
    logger.info(
        f'updating {model} forecast directory for {run_type}/{ddmmmyy} run'
    )
    forecast_dir = Path(config['rolling forecasts'][model]['dest dir'])
    new_forecast_dir = _create_new_forecast_dir(forecast_dir, model, run_type)
    days_from_past = config['rolling forecasts']['days from past']
    _add_past_days_results(
        run_date, days_from_past, new_forecast_dir, model, run_type, config
    )
    _add_forecast_results(run_date, new_forecast_dir, model, run_type, config)
    shutil.rmtree(os.fspath(forecast_dir))
    new_forecast_dir.replace(forecast_dir)
    logger.info(
        f'updated {model} forecast directory for {run_type}/{ddmmmyy} run: '
        f'{forecast_dir}'
    )
    checklist = {model: {run_type: os.fspath(forecast_dir)}}
    return checklist


def _create_new_forecast_dir(forecast_dir, model, run_type):
    new_forecast_dir = forecast_dir.with_name(f'{forecast_dir.name}_new')
    new_forecast_dir.mkdir()
    logger.debug(
        f'created new {model} forecast directory for {run_type} run: '
        f'{new_forecast_dir}'
    )
    return new_forecast_dir


def _add_past_days_results(
    run_date, days_from_past, new_forecast_dir, model, run_type, config
):
    nowcast_days = arrow.Arrow.range(
        'day', run_date.replace(days=-days_from_past), run_date
    )
    results_archive = Path(config['results archive']['nowcast'])
    for day in nowcast_days:
        _symlink_results(
            results_archive, day, new_forecast_dir, day, model, run_type
        )


def _add_forecast_results(run_date, new_forecast_dir, model, run_type, config):
    if run_type == 'forecast':
        results_archive = Path(config['results archive'][run_type])
        _symlink_results(
            results_archive,
            run_date,
            new_forecast_dir,
            run_date.replace(days=+1),
            model,
            run_type
        )
        return
    # For preliminary forecast (run_type == 'forecast2'):
    # Use 1st 24h of forecast run for run_date+1.
    tmp_forecast_results_archive = Path(f'/tmp/{model}_forecast')
    _extract_1st_forecast_day(
        tmp_forecast_results_archive, run_date, model, config
    )
    _symlink_results(
        tmp_forecast_results_archive,
        run_date.replace(days=+1),
        new_forecast_dir,
        run_date.replace(days=+1),
        model,
        run_type
    )
    # Use forecast2 run for run_date+2
    results_archive = Path(config['results archive'][run_type])
    _symlink_results(
        results_archive,
        run_date,
        new_forecast_dir,
        run_date.replace(days=+2),
        model,
        run_type
    )


def _extract_1st_forecast_day(
    tmp_forecast_results_archive, run_date, model, config
):
    try:
        shutil.rmtree(tmp_forecast_results_archive)
    except FileNotFoundError:
        # Temporary forecast results directory doesn't exist, and that's okay
        pass
    # Create the destination directory
    ddmmmyy = run_date.format('DDMMMYY').lower()
    ddmmmyy_p1 = run_date.replace(days=+1).format('DDMMMYY').lower()
    day_dir = tmp_forecast_results_archive / ddmmmyy_p1
    day_dir.mkdir(parents=True)
    logger.debug(
        f'created new {model} temporary forecast directory: {day_dir}'
    )
    results_archive = Path(config['results archive']['forecast'])
    for forecast_file in (results_archive / ddmmmyy).glob('*.nc'):
        if forecast_file.name.startswith('SalishSea_1d'):
            continue
        if forecast_file.name.endswith('restart.nc'):
            continue
        forecast_file_24h = (
            tmp_forecast_results_archive / ddmmmyy_p1 / forecast_file.name
        )
        cmd = (
            f'/usr/bin/ncks -d time_counter,0,23 '
            f'{forecast_file} {forecast_file_24h}'
        )
        logger.debug(f'running {cmd} in subprocess')
        subprocess.run(shlex.split(cmd))
        logger.debug(
            f'extracted 1st 24h of {forecast_file} to {forecast_file_24h}'
        )


def _symlink_results(
    results_archive, results_day, forecast_dir, forecast_day, model, run_type
):
    # Create the destination directory
    ddmmmyy = forecast_day.format('DDMMMYY').lower()
    day_dir = forecast_dir / ddmmmyy
    day_dir.mkdir()
    logger.debug(
        f'created new {model} forecast directory for {run_type} run: {day_dir}'
    )
    # Symlink the results files into the destination directory
    ddmmmyy = results_day.format('DDMMMYY').lower()
    for f in (results_archive / ddmmmyy).glob('*.nc'):
        (day_dir / f.name).symlink_to(f)
    logger.debug(
        f'symlinked *.nc files from {results_archive/ddmmmyy} in to {day_dir}'
    )


if __name__ == '__main__':
    main()  # pragma: no cover
