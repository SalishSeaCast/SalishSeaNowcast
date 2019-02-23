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
"""SalishSeaCast worker that monitors and reports on the progress of a
NEMO hindcast run on an HPC cluster that uses the SLURM scheduler.
"""
import logging
import os
from pathlib import Path
import tempfile
import time

import arrow
import attr
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
    logger.info(f"NEMO hindcast run on {parsed_args.host_name} watcher terminated")
    msg_type = "success"
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(f"NEMO hindcast run on {parsed_args.host_name} watcher failed")
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
        job = _HindcastJob(
            ssh_client, sftp_client, host_name, users, scratch_dir, run_id
        )
        job.get_run_id()
        while job.is_queued():
            time.sleep(60 * 5)
        job.get_tmp_run_dir()
        job.get_run_info()
        while job.is_running():
            time.sleep(60 * 5)
        while True:
            completion_state = job.get_completion_state()
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
            "host": job.host_name,
            "run id": job.run_id,
            "run date": arrow.get(job.run_id[:7], "DDMMMYY").format("YYYY-MM-DD"),
            "completed": completion_state == "completed",
        }
    }
    return checklist


@attr.s
class _HindcastJob:
    """Interact with the hindcast job on the HPC host.
    """

    ssh_client = attr.ib()
    sftp_client = attr.ib()
    host_name = attr.ib(type=str)
    users = attr.ib()
    scratch_dir = attr.ib(type=Path)
    run_id = attr.ib(default=None, type=str)
    job_id = attr.ib(default=None, type=str)
    tmp_run_dir = attr.ib(default=None, type=Path)
    it000 = attr.ib(default=None, type=int)
    itend = attr.ib(default=None, type=int)
    date0 = attr.ib(default=None, type=arrow.Arrow)
    rdt = attr.ib(default=None, type=float)

    def get_run_id(self):
        """Query the slurm queue to get the slurm job id, and the salishsea run id
        of the hindcast run.
        """
        queue_info = self._get_queue_info()
        self.job_id, self.run_id = queue_info.split()[:2]
        logger.info(f"watching {self.run_id} job {self.job_id} on {self.host_name}")

    def is_queued(self):
        """Query the slurm queue to get the state of the hindcast run.

        :return: Flag indicating whether or not run is queued in PENDING state
        :rtype: boolean
        """
        queue_info = self._get_queue_info()
        try:
            state, reason, start_time = queue_info.split()[2:]
        except AttributeError:
            # job has disappeared from the queue; maybe cancelled
            logger.error(
                f"{self.run_id} job {self.job_id} not found on {self.host_name} queue"
            )
            raise WorkerError
        if state != "PENDING":
            return False
        msg = f"{self.run_id} job {self.job_id} pending due to {reason.lower()}"
        if start_time != "N/A":
            msg = f"{msg}, scheduled for {start_time}"
        logger.info(msg)
        return True

    def get_tmp_run_dir(self):
        """Query the HPC host file system to get the temporary run directory of the
        hindcast job.
        """
        cmd = f"ls -d {self.scratch_dir/self.run_id}*"
        stdout = self._ssh_exec_command(cmd)
        self.tmp_run_dir = Path(stdout.splitlines()[0].strip())
        logger.debug(f"found tmp run dir: {self.host_name}:{self.tmp_run_dir}")

    def get_run_info(self):
        """Download the hindcast job namelist_cfg file from the HPC host and extract
        NEMO run parameters from it:

        * it000: starting time step number
        * itend: ending time step number
        * date0: calendar date of the start of the run
        * rdt: baroclinic time step
        """
        with tempfile.NamedTemporaryFile("wt") as namelist_cfg:
            self.sftp_client.get(f"{self.tmp_run_dir}/namelist_cfg", namelist_cfg.name)
            logger.debug(f"downloaded {self.host_name}:{self.tmp_run_dir}/namelist_cfg")
            namelist = f90nml.read(namelist_cfg.name)
            self.it000 = namelist["namrun"]["nn_it000"]
            self.itend = namelist["namrun"]["nn_itend"]
            self.date0 = arrow.get(str(namelist["namrun"]["nn_date0"]), "YYYYMMDD")
            self.rdt = namelist["namdom"]["rn_rdt"]
        logger.debug(
            f"{self.run_id} on {self.host_name}: "
            f"it000={self.it000}, itend={self.itend}, date0={self.date0}, rdt={self.rdt}"
        )

    def is_running(self):
        """Query the slurm queue to get the state of the hindcast run.

        While the job is running, report its progress via a log message.
        If one or more "E R R O R" lines are found in the ocean.output file,
        cancel the job.
        If exactly one "E R R O R" line is found, assume that the run got "stuck" and
        handle it accordingly.

        :return: Flag indicating whether or not run is in RUNNING state
        :rtype: boolean
        """
        if self._get_job_state() != "RUNNING":
            return False
        # Keep checking until we find a time.step file
        try:
            time_step_file = ssh_sftp.ssh_exec_command(
                self.ssh_client,
                f"cat {self.tmp_run_dir}/time.step",
                self.host_name,
                logger,
            )
        except ssh_sftp.SSHCommandError:
            logger.info(
                f"{self.run_id} on {self.host_name}: time.step not found; continuing to watch..."
            )
            return True
        self._report_progress(time_step_file)
        # grep ocean.output file for "E R R O R" lines
        try:
            ocean_output_errors = ssh_sftp.ssh_exec_command(
                self.ssh_client,
                f"grep 'E R R O R' {self.tmp_run_dir}/ocean.output",
                self.host_name,
                logger,
            )
        except ssh_sftp.SSHCommandError:
            logger.error(f"{self.run_id} on {self.host_name}: ocean.output not found")
            return False
        error_lines = ocean_output_errors.splitlines()
        if not error_lines:
            return True
        # Cancel run if "E R R O R" in ocean.output
        logger.error(
            f"{self.run_id} on {self.host_name}: "
            f"found {len(error_lines)} 'E R R O R' line(s) in ocean.output"
        )
        cmd = f"/opt/software/slurm/bin/scancel {self.job_id}"
        self._ssh_exec_command(
            cmd, f"{self.run_id} on {self.host_name}: cancelled {self.job_id}"
        )
        if len(error_lines) != 1:
            # More than 1 "E R R O R" line mean the run failed irrevocably
            return False
        # Exactly 1 "E R R O R" line means the run is "stuck" and it can be re-queued
        self._handle_stuck_job()
        while self.is_queued():
            time.sleep(60 * 5)
        self.get_tmp_run_dir()
        self.get_run_info()
        return True

    def _get_job_state(self):
        """Query the slurm queue to get the state of the hindcast run.

        :return: Run state reported by slurm or "UNKNOWN" if the job is not on the queue.
        :rtype: str
        """
        try:
            queue_info = self._get_queue_info()
            state = queue_info.split()[2]
        except (WorkerError, AttributeError):
            # job has disappeared from the queue; finished or cancelled
            logger.info(
                f"{self.run_id} job {self.job_id} not found on {self.host_name} queue"
            )
            state = "UNKNOWN"
        return state

    def _report_progress(self, time_step_file):
        """Calculate and log run progress based on value in time.step file.
        """
        time_step = int(time_step_file.splitlines()[0].strip())
        model_seconds = (time_step - self.it000) * self.rdt
        model_time = self.date0.replace(seconds=model_seconds).format(
            "YYYY-MM-DD HH:mm:ss UTC"
        )
        fraction_done = (time_step - self.it000) / (self.itend - self.it000)
        logger.info(
            f"{self.run_id} on {self.host_name}: timestep: "
            f"{time_step} = {model_time}, {fraction_done:.1%} complete"
        )

    def _handle_stuck_job(self):
        """Exactly 1 "E R R O R" line is usually a symptom of a run that got stuck
        because a processor was unable to read from a forcing file but NEMO didn't
        bubble the error up to cause the run to fail, so the run will time out
        with no further advancement of the time step.
        So, we re-queue the run for another try, then we re-queue the next hindcast run
        (if we find its temporary run directory) with a dependency on the re-queued
        stuck run.
        """
        # Re-queue the stuck run and update slurm run id
        sbatch = f"/opt/software/slurm/bin/sbatch"
        cmd = f"{sbatch} {self.tmp_run_dir}/SalishSeaNEMO.sh"
        self._ssh_exec_command(cmd, f"{self.run_id} on {self.host_name}: re-queued")
        self.job_id = None
        self.get_run_id()
        # Find next run, and requeue it with afterok dependence on newly queued run
        cmd = f"ls -dtr {self.scratch_dir}/*hindcast*"
        stdout = self._ssh_exec_command(cmd)
        next_tmp_run_dir = Path(stdout.splitlines()[0].strip())
        next_run_id = next_tmp_run_dir.name[:15]
        logger.debug(f"found next run tmp run dir: {self.host_name}:{next_tmp_run_dir}")
        cmd = f"{sbatch} -d afterok:{self.job_id} {next_tmp_run_dir}/SalishSeaNEMO.sh"
        self._ssh_exec_command(cmd, f"{next_run_id} on {self.host_name}: re-queued")

    def get_completion_state(self):
        """Query the slurm resource use records to get the completion state of the
        hindcast run.

        :return: Completion state of the run: "unknown", "completed", "cancelled",
                 or "aborted".
        :rtype: str
        """
        sacct_cmd = f"/opt/software/slurm/bin/sacct --user {self.users}"
        cmd = f"{sacct_cmd} --job {self.job_id}.batch --format=state"
        stdout = self._ssh_exec_command(cmd)
        if len(stdout.splitlines()) == 2:
            logger.debug(
                f"{self.job_id} batch step not found in saact report; continuing to look..."
            )
            return "unknown"
        state = stdout.splitlines()[2].strip()
        logger.info(f"{self.run_id} on {self.host_name}: {state}")
        if state in {"COMPLETED", "CANCELLED"}:
            return state.lower()
        return "aborted"

    def _ssh_exec_command(self, cmd, success_msg=""):
        """Execute cmd on the HPC host, returning its stdout.

        If cmd is successful, and success_msg is provided, log success_msg at the
        INFO level.

        If cmd fails, log stderr from the HPC host at the ERROR level, and raise
        WorkerError.

        :param str cmd:
        :param str success_msg:

        :raise: WorkerError

        :return: Standard output from the executed command.
        :rtype: str with newline separators
        """
        try:
            stdout = ssh_sftp.ssh_exec_command(
                self.ssh_client, cmd, self.host_name, logger
            )
            if success_msg:
                logger.info(success_msg)
            return stdout
        except ssh_sftp.SSHCommandError as exc:
            for line in exc.stderr.splitlines():
                logger.error(line)
            raise WorkerError

    def _get_queue_info(self):
        """Query the slurm queue to get the state of the hindcast run.

        :return: None or 1 line of output from slurm squeue command that describes
                 the run's state
        :rtype: str
        """
        squeue_cmd = f"/opt/software/slurm/bin/squeue --user {self.users}"
        queue_info_format = '--Format "jobid,name,state,reason,starttime"'
        cmd = (
            f"{squeue_cmd} {queue_info_format}"
            if self.job_id is None
            else f"{squeue_cmd} --job {self.job_id} {queue_info_format}"
        )
        stdout = self._ssh_exec_command(cmd)
        if len(stdout.splitlines()) == 1:
            if self.job_id is None:
                logger.error(f"no jobs found on {self.host_name} queue")
                raise WorkerError
            else:
                # Various callers handle job id not on queue in difference ways
                return
        for queue_info in stdout.splitlines()[1:]:
            if self.run_id is not None:
                if self.run_id in queue_info.strip().split()[1]:
                    return queue_info.strip()
            else:
                if "hindcast" in queue_info.strip().split()[1]:
                    return queue_info.strip()


if __name__ == "__main__":
    main()  # pragma: no cover
