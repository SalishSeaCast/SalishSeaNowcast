#  Copyright 2013-2021 The Salish Sea MEOPAR contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""SalishSeaCast worker that builds a new directory of symlinks to model
results files for the rolling forecast datasets and replaces the previous
rolling forecast directory with the new one.
"""
import logging
import os
import shlex
import shutil
import subprocess
from pathlib import Path

import arrow
from nemo_nowcast import NowcastWorker

NAME = "update_forecast_datasets"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.update_forecast_datasets -h`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "model",
        choices={"fvcom", "nemo", "wwatch3"},
        help="""
        Model to update the rolling forecast datasets for:
        'fvcom' means the Vancouver Harbour Fraser River (VHFR) FVCOM model,
        'nemo' means the Salish Sea NEMO model,
        'wwatch3' means the Strait of Georgia WaveWatch3(TM) model.
        """,
    )
    worker.cli.add_argument(
        "run_type",
        choices={"forecast", "forecast2"},
        help="""
        Type of run to update rolling forecast datasets for:
        'forecast' means afternoon updated forecast runs,
        'forecast2' means early morning preliminary forecast runs,
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=(arrow.now().floor("day")),
        help="Date of the run to update rolling forecast datasets for.",
    )
    worker.run(update_forecast_datasets, success, failure)


def success(parsed_args):
    model = parsed_args.model
    run_type = parsed_args.run_type
    ymd = parsed_args.run_date.format("YYYY-MM-DD")
    logger.info(f"{model} {ymd} {run_type} rolling forecast datasets updated")
    msg_type = f"success {model} {run_type}"
    return msg_type


def failure(parsed_args):
    model = parsed_args.model
    run_type = parsed_args.run_type
    ymd = parsed_args.run_date.format("YYYY-MM-DD")
    logger.critical(f"{model} {ymd} {run_type} rolling forecast datasets update failed")
    msg_type = f"failure {model} {run_type}"
    return msg_type


def update_forecast_datasets(parsed_args, config, *args):
    model = parsed_args.model
    run_type = parsed_args.run_type
    run_date = parsed_args.run_date
    updated_dirs = []
    try:
        most_recent_fcst_dir = Path(
            config["rolling forecasts"][model]["most recent forecast dir"]
        )
        _symlink_most_recent_forecast(
            run_date, most_recent_fcst_dir, model, run_type, config
        )
        updated_dirs.append(os.fspath(most_recent_fcst_dir))
    except KeyError:
        # no most recent forecast dir for NEMO, and that's okay
        pass
    try:
        forecast_dir = Path(config["rolling forecasts"][model]["dest dir"])
        _update_rolling_forecast(run_date, forecast_dir, model, run_type, config)
        updated_dirs.append(os.fspath(forecast_dir))
    except KeyError:
        # no rolling forecast dir for VHFR FVCOM, and that's okay
        pass
    checklist = {model: {run_type: updated_dirs}}
    return checklist


def _symlink_most_recent_forecast(
    run_date, most_recent_fcst_dir, model, run_type, config
):
    ddmmmyy = run_date.format("DDMMMYY").lower()
    logger.info(
        f"updating {model} most_recent_forecast directory from {run_type}/{ddmmmyy} run"
    )
    for f in most_recent_fcst_dir.iterdir():
        f.unlink()
    logger.debug(f"deleted previous forecast symlinks from {most_recent_fcst_dir}")
    runs = {"fvcom": "vhfr fvcom runs", "wwatch3": "wave forecasts"}
    results_archive = {
        "nemo": Path(config["results archive"]["nowcast"]),
        "fvcom": Path(config[runs["fvcom"]]["results archive"]["forecast x2"]),
        "wwatch3": Path(config[runs["wwatch3"]]["results archive"][run_type]),
    }[model]
    for f in (results_archive / ddmmmyy).glob("*.nc"):
        if "restart" not in f.name:
            (most_recent_fcst_dir / f.name).symlink_to(f)
    logger.debug(
        f"symlinked *.nc files from {results_archive/ddmmmyy} in to {most_recent_fcst_dir}"
    )
    logger.info(
        f"updated {model} most_recent_forecast directory from {run_type}/{ddmmmyy} run"
    )


def _update_rolling_forecast(run_date, forecast_dir, model, run_type, config):
    ddmmmyy = run_date.format("DDMMMYY").lower()
    logger.info(f"updating {model} forecast directory for {run_type}/{ddmmmyy} run")
    new_forecast_dir = _create_new_forecast_dir(forecast_dir, model, run_type)
    days_from_past = config["rolling forecasts"]["days from past"]
    tmp_forecast_results_archive = Path(
        config["rolling forecasts"]["temporary results archives"], f"{model}_forecast"
    )
    try:
        shutil.rmtree(tmp_forecast_results_archive)
    except FileNotFoundError:
        # Temporary forecast results directory doesn't exist, and that's okay
        pass
    _add_past_days_results(
        run_date, days_from_past, new_forecast_dir, model, run_type, config
    )
    _add_forecast_results(
        run_date,
        new_forecast_dir,
        tmp_forecast_results_archive,
        model,
        run_type,
        config,
    )
    shutil.rmtree(os.fspath(forecast_dir))
    new_forecast_dir.replace(forecast_dir)
    logger.info(
        f"updated {model} forecast directory for {run_type}/{ddmmmyy} run: "
        f"{forecast_dir}"
    )


def _create_new_forecast_dir(forecast_dir, model, run_type):
    new_forecast_dir = forecast_dir.with_name(f"{forecast_dir.name}_new")
    new_forecast_dir.mkdir()
    logger.debug(
        f"created new {model} forecast directory for {run_type} run: "
        f"{new_forecast_dir}"
    )
    return new_forecast_dir


def _add_past_days_results(
    run_date, days_from_past, new_forecast_dir, model, run_type, config
):
    results_archive = (
        Path(config["results archive"]["nowcast"])
        if model == "nemo"
        else Path(config["wave forecasts"]["results archive"]["nowcast"])
    )
    first_date = (
        run_date.shift(days=-days_from_past)
        if run_type == "forecast"
        else run_date.shift(days=-(days_from_past - 1))
    )
    wwatch3_forecast2 = model == "wwatch3" and run_type == "forecast2"
    last_date = run_date.shift(days=-1) if wwatch3_forecast2 else run_date
    for day in arrow.Arrow.range("day", first_date, last_date):
        _symlink_results(results_archive, day, new_forecast_dir, day, model, run_type)


def _add_forecast_results(
    run_date, new_forecast_dir, tmp_forecast_results_archive, model, run_type, config
):
    results_archive = (
        Path(config["results archive"][run_type])
        if model == "nemo"
        else Path(config["wave forecasts"]["results archive"][run_type])
    )
    if run_type == "forecast":
        _symlink_results(
            results_archive,
            run_date,
            new_forecast_dir,
            run_date.shift(days=+1),
            model,
            run_type,
        )
        return
    # For preliminary forecast (run_type == 'forecast2'):
    # Use 1st 24h of forecast run from previous day.
    _extract_1st_forecast_day(tmp_forecast_results_archive, run_date, model, config)
    day = run_date.shift(days=-1) if model == "wwatch3" else run_date
    _symlink_results(
        tmp_forecast_results_archive,
        day.shift(days=+1),
        new_forecast_dir,
        day.shift(days=+1),
        model,
        run_type,
    )
    # Use forecast2 run for rest of forecast
    _symlink_results(
        results_archive,
        run_date,
        new_forecast_dir,
        day.shift(days=+2),
        model,
        run_type,
    )


def _extract_1st_forecast_day(tmp_forecast_results_archive, run_date, model, config):
    # Create the destination directory
    ddmmmyy_m1 = run_date.shift(days=-1).format("DDMMMYY").lower()
    ddmmmyy = run_date.format("DDMMMYY").lower()
    ddmmmyy_p1 = run_date.shift(days=+1).format("DDMMMYY").lower()
    model_params = {
        "nemo": {
            "day dir": tmp_forecast_results_archive / ddmmmyy_p1,
            "results archive": Path(config["results archive"]["forecast"]),
            "forecast day": ddmmmyy,
            "time variable": "time_counter",
        },
        "wwatch3": {
            "day dir": tmp_forecast_results_archive / ddmmmyy,
            "results archive": Path(
                config["wave forecasts"]["results archive"]["forecast"]
            ),
            "forecast day": ddmmmyy_m1,
            "time variable": "time",
        },
    }
    day_dir = model_params[model]["day dir"]
    try:
        day_dir.mkdir(parents=True)
    except FileExistsError:
        # Day directory exists, and that's okay
        pass
    logger.debug(f"created new {model} temporary forecast directory: {day_dir}")
    results_archive = model_params[model]["results archive"]
    forecast_day = model_params[model]["forecast day"]
    for forecast_file in (results_archive / forecast_day).glob("*.nc"):
        if forecast_file.name.startswith("SalishSea_1d"):
            continue
        if forecast_file.name.endswith("restart.nc"):
            continue
        forecast_file_24h = day_dir / forecast_file.name
        forecast_time_intervals = {
            "nemo": 24 if forecast_file.name.startswith("SalishSea_1h") else 24 * 6,
            "wwatch3": 24 * 2
            if forecast_file.name.startswith("SoG_ww3_fields")
            else 24 * 6,
        }
        forecast_times = forecast_time_intervals[model]
        time_var = model_params[model]["time variable"]
        cmd = (
            f"/usr/bin/ncks -d {time_var},0,{forecast_times-1} "
            f"{forecast_file} {forecast_file_24h}"
        )
        logger.debug(f"running {cmd} in subprocess")
        subprocess.run(shlex.split(cmd))
        logger.debug(f"extracted 1st 24h of {forecast_file} to {forecast_file_24h}")


def _symlink_results(
    results_archive, results_day, forecast_dir, forecast_day, model, run_type
):
    # Create the destination directory
    ddmmmyy = forecast_day.format("DDMMMYY").lower()
    day_dir = forecast_dir / ddmmmyy
    day_dir.mkdir()
    logger.debug(
        f"created new {model} forecast directory for {run_type} run: {day_dir}"
    )
    # Symlink the results files into the destination directory
    ddmmmyy = results_day.format("DDMMMYY").lower()
    for f in (results_archive / ddmmmyy).glob("*.nc"):
        (day_dir / f.name).symlink_to(f)
    logger.debug(f"symlinked *.nc files from {results_archive/ddmmmyy} in to {day_dir}")


if __name__ == "__main__":
    main()  # pragma: no cover
