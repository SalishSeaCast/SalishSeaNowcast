# Copyright 2013-2018 The Salish Sea MEOPAR Contributors
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
"""SalishSeaCast worker that monitors and reports on the progress of a
NEMO hindcast run on an HPC cluster that uses the SLURM scheduler.
"""
import logging
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace

import arrow
import f90nml
from nemo_nowcast import NowcastWorker, WorkerError

from nowcast import ssh_sftp

NAME = "watch_NEMO_hindcast"
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.watch_NEMO_hindcast --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument("host_name", help="Name of the host to monitor the run on")
    worker.cli.add_argument("--run-id", help="Run id to watch; e.g. 01dec14hindcast")
    worker.run(watch_NEMO_hindcast, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f"NEMO hindcast run on {parsed_args.host_name} completed",
        extra={"run_type": "hindcast", "host_name": parsed_args.host_name},
    )
    msg_type = "success"
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f"NEMO hindcast run on {parsed_args.host_name} watcher failed",
        extra={"run_type": "hindcast", "host_name": parsed_args.host_name},
    )
    msg_type = "failure"
    return msg_type


def watch_NEMO_hindcast(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    run_id = parsed_args.run_id
    ssh_key = Path(
        os.environ["HOME"],
        ".ssh",
        config["run"]["hindcast hosts"][host_name]["ssh key"],
    )
    users = config["run"]["hindcast hosts"][host_name]["users"]
    scratch_dir = Path(config["run"]["hindcast hosts"][host_name]["scratch dir"])
    try:
        ssh_client, sftp_client = ssh_sftp.sftp(host_name, os.fspath(ssh_key))
        job_id, run_id = _get_run_id(ssh_client, host_name, users, run_id)
        while _is_queued(ssh_client, host_name, users, job_id, run_id):
            time.sleep(60 * 5)
        tmp_run_dir = _get_tmp_run_dir(ssh_client, host_name, scratch_dir, run_id)
        run_info = _get_run_info(sftp_client, host_name, tmp_run_dir)
        while _is_running(
            ssh_client, host_name, users, job_id, run_id, tmp_run_dir, run_info
        ):
            time.sleep(60 * 5)
        while True:
            completion_state = _get_completion_state(
                ssh_client, host_name, users, job_id, run_id
            )
            if completion_state == "completed":
                break
            if completion_state in {"cancelled", "aborted"}:
                raise WorkerError
            time.sleep(60)
    finally:
        sftp_client.close()
        ssh_client.close()
    checklist = {
        "hindcast": {
            "host": host_name,
            "run id": run_id,
            "run date": arrow.get(run_id[:7], "DDMMMYY").format("YYYY-MM-DD"),
            "completed": completion_state == "completed",
        }
    }
    return checklist


def _get_run_id(ssh_client, host_name, users, run_id):
    """
    :param :py:class:`paramiko.client.SSHClient`
    :param str host_name:
    :param str users:
    :param str run_id:

    :return: slurm job id number, run id string
    :rtype: 2-tuple (int, str)
    """
    queue_info = _get_queue_info(ssh_client, host_name, users, run_id=run_id)
    job_id, run_id = queue_info.split()[:2]
    logger.info(f"watching {run_id} job {job_id} on {host_name}")
    return job_id, run_id


def _is_queued(ssh_client, host_name, users, job_id, run_id):
    """
    :param :py:class:`paramiko.client.SSHClient`
    :param str host_name:
    :param str users:
    :param int job_id:
    :param str run_id:

    :return: Flag indicating whether or not run is queued in PENDING state
    :rtype: boolean
    """
    queue_info = _get_queue_info(ssh_client, host_name, users, job_id=job_id)
    try:
        state, reason, start_time = queue_info.split()[2:]
    except AttributeError:
        # job has disappeared from the queue; maybe cancelled
        logger.error(f"{run_id} job {job_id} not found on {host_name} queue")
        raise WorkerError
    if state != "PENDING":
        return False
    msg = f"{run_id} job {job_id} pending due to {reason.lower()}"
    if start_time != "N/A":
        msg = f"{msg}, scheduled for {start_time}"
    logger.info(msg)
    return True


def _get_tmp_run_dir(ssh_client, host_name, scratch_dir, run_id):
    """
    :param :py:class:`paramiko.client.SSHClient`
    :param str host_name:
    :param :py:class:`pathlib.Path` scratch_dir:
    :param str run_id:

    :return: Temporary run directory
    :rtype: :py:class:`pathlib.Path`
    """
    try:
        stdout = ssh_sftp.ssh_exec_command(
            ssh_client, f"ls -d {scratch_dir/run_id}*", host_name, logger
        )
    except ssh_sftp.SSHCommandError as exc:
        for line in exc.stderr.splitlines():
            logger.error(line)
        raise WorkerError
    tmp_run_dir = Path(stdout.splitlines()[0].strip())
    logger.debug(f"found tmp run dir: {host_name}:{tmp_run_dir}")
    return tmp_run_dir


def _is_running(ssh_client, host_name, users, job_id, run_id, tmp_run_dir, run_info):
    """
    :param :py:class:`paramiko.client.SSHClient`
    :param str host_name:
    :param str users:
    :param int job_id:
    :param str run_id:
    :param :py:class:`pathlib.Path` tmp_run_dir:
    :param :py:class:`types.SimpleNamespace` run_info:

    :return: Flag indicating whether or not run is in RUNNING state
    :rtype: boolean
    """
    try:
        queue_info = _get_queue_info(ssh_client, host_name, users, job_id=job_id)
        state = queue_info.split()[2]
    except (WorkerError, AttributeError):
        # job has disappeared from the queue; finished or cancelled
        logger.info(f"{run_id} job {job_id} not found on {host_name} queue")
        state = "UNKNOWN"
    if state != "RUNNING":
        return False
    # Keep checking until we find a time.step file
    try:
        time_step_file = ssh_sftp.ssh_exec_command(
            ssh_client, f"cat {tmp_run_dir}/time.step", host_name, logger
        )
    except ssh_sftp.SSHCommandError:
        logger.info(
            f"{run_id} on {host_name}: time.step not found; continuing to watch..."
        )
        return True
    # Keep checking until we find a ocean.output file
    try:
        ocean_output_errors = ssh_sftp.ssh_exec_command(
            ssh_client,
            f"grep 'E R R O R' {tmp_run_dir}/ocean.output",
            host_name,
            logger,
        )
    except ssh_sftp.SSHCommandError:
        logger.info(
            f"{run_id} on {host_name}: ocean.output not found; continuing to watch..."
        )
        return True
    # Cancel run if "E R R O R" in ocean.output
    error_lines = ocean_output_errors.splitlines()
    if error_lines:
        logger.error(
            f"{run_id} on {host_name}: found {len(error_lines)} E R R O R lines in ocean.output"
        )
        scancel_cmd = f"/opt/software/slurm/bin/scancel --user {users}"
        cmd = f"{scancel_cmd} {job_id}"
        try:
            ssh_sftp.ssh_exec_command(ssh_client, cmd, host_name, logger)
        except ssh_sftp.SSHCommandError as exc:
            for line in exc.stderr.splitlines():
                logger.error(line)
            raise WorkerError
        return False
    # Calculate and log run progress based on value in time.step file
    time_step = int(time_step_file.splitlines()[0].strip())
    model_seconds = (time_step - run_info.it000) * run_info.rdt
    model_time = run_info.date0.replace(seconds=model_seconds).format(
        "YYYY-MM-DD HH:mm:ss UTC"
    )
    fraction_done = (time_step - run_info.it000) / (run_info.itend - run_info.it000)
    logger.info(
        f"{run_id} on {host_name}: timestep: "
        f"{time_step} = {model_time}, {fraction_done:.1%} complete"
    )
    return True


def _get_completion_state(ssh_client, host_name, users, job_id, run_id):
    """
    :param :py:class:`paramiko.client.SSHClient`
    :param users:
    :param str host_name:
    :param int job_id:
    :param str run_id:

    :return: completion state of the run: "unknown", "completed", "cancelled", or "aborted"
    :rtype: str
    """
    sacct_cmd = f"/opt/software/slurm/bin/sacct --user {users}"
    cmd = f"{sacct_cmd} --job {job_id}.batch --format=state"
    try:
        stdout = ssh_sftp.ssh_exec_command(ssh_client, cmd, host_name, logger)
    except ssh_sftp.SSHCommandError as exc:
        for line in exc.stderr.splitlines():
            logger.error(line)
        raise WorkerError
    if len(stdout.splitlines()) == 2:
        logger.debug(
            f"{job_id} batch step not found in saact report; continuing to look..."
        )
        return "unknown"
    state = stdout.splitlines()[2].strip()
    logger.info(f"{run_id} on {host_name}: completed")
    if state in {"COMPLETED", "CANCELLED"}:
        return state.lower()
    return "aborted"


def _get_queue_info(ssh_client, host_name, users, run_id=None, job_id=None):
    """
    :param :py:class:`paramiko.client.SSHClient`
    :param str host_name:
    :param str users:
    :param str run_id:
    :param int job_id:

    :return: None or 1 line of output from slurm squeue command that describes
             the run's state
    :rtype: str
    """
    squeue_cmd = f"/opt/software/slurm/bin/squeue --user {users}"
    queue_info_format = '--Format "jobid,name,state,reason,starttime"'
    cmd = (
        f"{squeue_cmd} {queue_info_format}"
        if job_id is None
        else f"{squeue_cmd} --job {job_id} {queue_info_format}"
    )
    try:
        stdout = ssh_sftp.ssh_exec_command(ssh_client, cmd, host_name, logger)
    except ssh_sftp.SSHCommandError as exc:
        for line in exc.stderr.splitlines():
            logger.error(line)
        raise WorkerError
    if len(stdout.splitlines()) == 1:
        if job_id is None:
            logger.error(f"no jobs found on {host_name} queue")
            raise WorkerError
        else:
            # Various callers handle job id not on queue in difference ways
            return
    for queue_info in stdout.splitlines()[1:]:
        if run_id is not None:
            if run_id in queue_info.strip().split()[1]:
                return queue_info.strip()
        else:
            if "hindcast" in queue_info.strip().split()[1]:
                return queue_info.strip()


def _get_run_info(sftp_client, host_name, tmp_run_dir):
    """
    :param :py:class:`paramiko.sftp_client.SFTPClient` sftp_client:
    :param str host_name:
    :param :py:class:`pathlib.Path` tmp_run_dir:

    :return: Namespace of run timing info:
               it000: 1st time step number
               itend: last time step number
               date0: run start date
               rdt: time step in seconds
    :rtype: :py:class:`types.SimpleNamespace`
    """
    with tempfile.NamedTemporaryFile("wt") as namelist_cfg:
        sftp_client.get(f"{tmp_run_dir}/namelist_cfg", namelist_cfg.name)
        logger.debug(f"downloaded {host_name}:{tmp_run_dir}/namelist_cfg")
        namelist = f90nml.read(namelist_cfg.name)
        run_info = SimpleNamespace(
            it000=namelist["namrun"]["nn_it000"],
            itend=namelist["namrun"]["nn_itend"],
            date0=arrow.get(str(namelist["namrun"]["nn_date0"]), "YYYYMMDD"),
            rdt=namelist["namdom"]["rn_rdt"],
        )
    return run_info


if __name__ == "__main__":
    main()  # pragma: no cover
