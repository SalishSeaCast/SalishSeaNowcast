#  Copyright 2013-2020 The Salish Sea MEOPAR contributors
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
"""Salish Sea NEMO nowcast worker that monitors and reports on the
progress of a run on the ONC cloud computing facility or salish.
"""
import logging
import os
from pathlib import Path
import shlex
import subprocess
import time

import arrow
import f90nml
from nemo_nowcast import NowcastWorker

NAME = "watch_NEMO"
logger = logging.getLogger(NAME)

POLL_INTERVAL = 5 * 60  # seconds


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.watch_NEMO --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument("host_name", help="Name of the host to monitor the run on")
    worker.cli.add_argument(
        "run_type",
        choices={"nowcast", "nowcast-green", "nowcast-dev", "forecast", "forecast2"},
        help="""
        Type of run to monitor:
        'nowcast' means nowcast physics run,
        'nowcast-green' means nowcast green ocean run,
        'forecast' means updated forecast run,
        'forecast2' means preliminary forecast run,
        """,
    )
    worker.run(watch_NEMO, success, failure)


def success(parsed_args):
    logger.info("{0.run_type} NEMO run on {0.host_name} completed".format(parsed_args))
    msg_type = "success {.run_type}".format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical("{0.run_type} NEMO run on {0.host_name} failed".format(parsed_args))
    msg_type = "failure {.run_type}".format(parsed_args)
    return msg_type


def watch_NEMO(parsed_args, config, tell_manager):
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_info = tell_manager("need", "NEMO run").payload
    run_date = arrow.get(run_info[run_type]["run date"])
    pid = _find_run_pid(run_info[run_type])
    logger.debug(f"{run_type} on {host_name}: run pid: {pid}")
    # Get run time steps and date info from namelist
    run_dir = Path(run_info[run_type]["run dir"])
    namelist = f90nml.read(run_dir / "namelist_cfg")
    it000 = namelist["namrun"]["nn_it000"]
    itend = namelist["namrun"]["nn_itend"]
    date0 = arrow.get(str(namelist["namrun"]["nn_date0"]), "YYYYMMDD")
    rdt = namelist["namdom"]["rn_rdt"]
    # Watch for the run process to end
    while _pid_exists(pid):
        try:
            with (run_dir / "time.step").open("rt") as f:
                time_step = int(f.read().strip())
            model_seconds = (time_step - it000) * rdt
            model_time = date0.shift(seconds=model_seconds).format(
                "YYYY-MM-DD HH:mm:ss UTC"
            )
            fraction_done = (time_step - it000) / (itend - it000)
            msg = (
                f"{run_type} on {host_name}: timestep: "
                f"{time_step} = {model_time}, {fraction_done:.1%} complete"
            )
        except FileNotFoundError:
            # time.step file not found; assume that run is young and it
            # hasn't been created yet, or has finished and it has been
            # moved to the results directory
            msg = (
                f"{run_type} on {host_name}: time.step not found; "
                f"continuing to watch..."
            )
        logger.info(msg)
        time.sleep(POLL_INTERVAL)
    checklist = {
        run_type: {"host": host_name, "run date": run_date.format("YYYY-MM-DD")}
    }
    run_duration = config["run types"][run_type]["duration"]
    timesteps_per_day = 86400 / rdt
    restart_timestep = (
        int(it000 + int(run_duration) * timesteps_per_day) - 1
        if run_type in ("forecast", "forecast2")
        else itend
    )
    checklist[run_type]["completed"] = _confirm_run_success(
        host_name, run_type, run_date, run_dir, itend, restart_timestep, config
    )
    return checklist


def _find_run_pid(run_info):
    if run_info["run exec cmd"].startswith("qsub"):
        torque_id = run_info["run id"]
        cmd = shlex.split(f"pgrep {torque_id}")
        logger.debug(f"searching processes for {torque_id}")
    else:
        run_exec_cmd = run_info["run exec cmd"]
        cmd = shlex.split(f'pgrep --newest --exact --full "{run_exec_cmd}"')
        logger.debug(f'searching processes for "{run_exec_cmd}"')
    pid = None
    while pid is None:
        try:
            proc = subprocess.run(
                cmd, stdout=subprocess.PIPE, check=True, universal_newlines=True
            )
            pid = int(proc.stdout)
        except subprocess.CalledProcessError:
            # Process has not yet been spawned
            pass
    return pid


def _pid_exists(pid):
    """Check whether pid exists in the current process table.

    From: http://stackoverflow.com/a/6940314
    """
    if pid < 0:
        return False
    if pid == 0:
        # According to "man 2 kill" PID 0 refers to every process
        # in the process group of the calling process.
        # On certain systems 0 is a valid PID but we have no way
        # to know that in a portable fashion.
        raise ValueError("invalid PID 0")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # PermissionError clearly means there's a process to deny access to
        return True
    except OSError:
        raise
    return True


def _confirm_run_success(
    host_name, run_type, run_date, run_dir, itend, restart_timestep, config
):
    run_succeeded = True
    run_config = config["run"]["enabled hosts"][host_name]["run types"][run_type]
    dmy = run_date.format("DDMMMYY").lower()
    results_dir = Path(run_config["results"], dmy)
    if not results_dir.exists():
        run_succeeded = False
        logger.critical(f"No results directory for {host_name} run: {results_dir}")
        # Continue the rest of the checks in the temporary run directory
        results_dir = run_dir
    if (results_dir / "output.abort.nc").exists():
        run_succeeded = False
        logger.critical(
            f"{host_name} {run_type}/{dmy} run aborted: "
            f'{results_dir/"output.abort.nc"}'
        )
    try:
        with (results_dir / "time.step").open("rt") as f:
            time_step = int(f.read().strip())
        if time_step != itend:
            run_succeeded = False
            logger.critical(
                f"{host_name} {run_type}/{dmy} run failed: "
                f"final time step is {time_step} not {itend}"
            )
    except FileNotFoundError:
        run_succeeded = False
        logger.critical(f"{host_name} {run_type}/{dmy} run failed; no time.step file")
        pass
    restart_file = results_dir / f"SalishSea_{restart_timestep:08d}_restart.nc"
    if not restart_file.exists():
        run_succeeded = False
        logger.critical(
            f"{host_name} {run_type}/{dmy} run failed; "
            f"no physics restart file: {restart_file}"
        )
    if run_type == "nowcast-green":
        tracer_restart_file = (
            results_dir / f"SalishSea_{restart_timestep:08d}_restart_trc.nc"
        )
        if not tracer_restart_file.exists():
            run_succeeded = False
            logger.critical(
                f"{host_name} {run_type}/{dmy} run failed; "
                f"no tracers restart file: {tracer_restart_file}"
            )
    try:
        with (results_dir / "ocean.output").open("rt") as f:
            for line in f:
                if "E R R O R" in line:
                    run_succeeded = False
                    logger.critical(
                        f"{host_name} {run_type}/{dmy} run failed; "
                        f'1 or more E R R O R in: {results_dir/"ocean.output"}'
                    )
                    break
    except FileNotFoundError:
        run_succeeded = False
        logger.critical(
            f"{host_name} {run_type}/{dmy} run failed; no ocean.output file"
        )
        pass
    try:
        with (results_dir / "solver.stat").open("rt") as f:
            for line in f:
                if "NaN" in line:
                    run_succeeded = False
                    logger.critical(
                        f"{host_name} {run_type}/{dmy} run failed; "
                        f'NaN in: {results_dir/"solver.stat"}'
                    )
                    break
    except FileNotFoundError:
        run_succeeded = False
        logger.critical(f"{host_name} {run_type}/{dmy} run failed; no solver.stat file")
        pass
    if run_type == "nowcast-green":
        try:
            with (results_dir / "tracer.stat").open("rt") as f:
                for line in f:
                    if "NaN" in line:
                        run_succeeded = False
                        logger.critical(
                            f"{host_name} {run_type}/{dmy} run failed; "
                            f'NaN in: {results_dir/"solver.stat"}'
                        )
                        break
        except FileNotFoundError:
            run_succeeded = False
            logger.critical(
                f"{host_name} {run_type}/{dmy} run failed; no tracer.stat file"
            )
            pass
    return run_succeeded


if __name__ == "__main__":
    main()  # pragma: no cover
