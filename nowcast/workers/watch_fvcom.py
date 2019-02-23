#  Copyright 2013-2019 The Salish Sea MEOPAR contributors
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
"""Salish Sea nowcast worker that monitors and reports on the
progress of an FVCOM run on the ONC cloud computing facility.
"""
import logging
import os
from pathlib import Path
import shlex
import subprocess

import time
from nemo_nowcast import NowcastWorker

NAME = "watch_fvcom"
logger = logging.getLogger(NAME)

POLL_INTERVAL = 5 * 60  # seconds


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.watch_fvcom --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument("host_name", help="Name of the host to monitor the run on")
    worker.cli.add_argument(
        "run_type",
        choices={"nowcast", "forecast"},
        help="""
        Type of run to monitor:
        'nowcast' means nowcast run (after NEMO nowcast run)
        """,
    )
    worker.run(watch_fvcom, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f"{parsed_args.run_type} FVCOM VH-FR run "
        f"on {parsed_args.host_name} completed"
    )
    msg_type = f"success {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f"{parsed_args.run_type} FVCOM VH-FR run " f"on {parsed_args.host_name} failed"
    )
    msg_type = f"failure {parsed_args.run_type}"
    return msg_type


def watch_fvcom(parsed_args, config, tell_manager):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:
    :param :py:func:`nemo_nowcast.NowcastWorker.tell_manager` tell_manager:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    run_type = parsed_args.run_type
    run_info = tell_manager("need", "FVCOM run").payload
    pid = _find_run_pid(run_info[run_type])
    logger.debug(f"{run_type} on {host_name}: run pid: {pid}")
    run_dir = Path(run_info[run_type]["run dir"])
    # Watch for the run process to end
    while _pid_exists(pid):
        try:
            with (run_dir / "fvcom.log").open("rt") as f:
                lines = f.readlines()
            lines.reverse()
            for line in lines:
                if line.strip().startswith("!") and line.strip().endswith("|"):
                    time_step, model_time, time_to_finish, _ = (
                        line.strip().strip("!").split(maxsplit=3)
                    )
                    msg = (
                        f"{run_type} on {host_name}: timestep: "
                        f'{time_step} = {model_time[:-7].replace("T", " ")} '
                        f"UTC estimated time to finish: {time_to_finish}"
                    )
                    break
            else:
                # fvcom.log file found, but no run status line found
                msg = (
                    f"{run_type} on {host_name}: no run progress found in "
                    f"fvcom.log ; continuing to watch..."
                )
        except FileNotFoundError:
            # fvcom.log file not found; assume that run is young and it
            # hasn't been created yet, or has finished and it has been
            # moved to the results directory
            msg = (
                f"{run_type} on {host_name}: fvcom.log not found; "
                f"continuing to watch..."
            )
        logger.info(msg)
        time.sleep(POLL_INTERVAL)
    return {
        run_type: {
            "host": host_name,
            "run date": run_info[run_type]["run date"],
            "completed": True,
        }
    }


def _find_run_pid(run_info):
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


if __name__ == "__main__":
    main()  # pragma: no cover
