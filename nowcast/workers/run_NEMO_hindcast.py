#  Copyright 2013 – present by the SalishSeaCast Project contributors
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
"""SalishSeaCast worker that prepares the YAML run description file and
bash run script for a NEMO hindcast run on an HPC cluster that uses the SLURM
scheduler, and queues the run.
"""
import logging
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

import arrow
import f90nml
import yaml
from nemo_nowcast import NowcastWorker, WorkerError

from nowcast import ssh_sftp

NAME = "run_NEMO_hindcast"
logger = logging.getLogger(NAME)


def main():
    """For command-line usage see:

    :command:`python -m nowcast.workers.run_NEMO_hindcast --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument("host_name", help="Name of the host to queue the run on")
    worker.cli.add_argument(
        "--full-month",
        action="store_true",
        help="""
        Configure the hindcast run to be a calendar month in duration.
        The default run duration is 10 days, or the number of days remaining
        in the calendar month of the run.
        """,
    )
    worker.cli.add_argument(
        "--prev-run-date", default=None, help="Start date of the previous hindcast run."
    )
    worker.cli.add_argument(
        "--walltime",
        default=None,
        help="""
        Walltime to request for the hindcast run.
        Defaults to 10 hours (10:00:00) for 10-ish day runs,
        and 30 hours (30:00:00) for --full-month runs.
        **IMPORTANT: Use seconds for walltime values greater than 23:59:59**
        """,
    )
    worker.run(run_NEMO_hindcast, success, failure)
    return worker


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(f"NEMO hindcast run queued on {parsed_args.host_name}")
    msg_type = "success"
    return msg_type


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(f"NEMO hindcast run failed to queue on {parsed_args.host_name}")
    msg_type = "failure"
    return msg_type


def run_NEMO_hindcast(parsed_args, config, *args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist items
    :rtype: dict
    """
    host_name = parsed_args.host_name
    ssh_key = Path(
        os.environ["HOME"],
        ".ssh",
        config["run"]["hindcast hosts"][host_name]["ssh key"],
    )
    try:
        ssh_client, sftp_client = ssh_sftp.sftp(host_name, ssh_key)
        if parsed_args.prev_run_date is None:
            # Assume that there is at least one job already queued or running
            # and get its run date from the queue manager
            prev_run_date, prev_job_id = _get_prev_run_queue_info(
                ssh_client, host_name, config
            )
        else:
            prev_run_date = arrow.get(parsed_args.prev_run_date)
            prev_job_id = None
        if parsed_args.full_month:
            # Calculate run date and number of run days for a full month run
            run_date = prev_run_date.shift(months=+1)
            run_days = (run_date.shift(months=+1) - run_date).days
        else:
            # Calculate run date and number of run days for a 5 day run
            if prev_run_date.day != 26:
                run_date = prev_run_date.shift(days=+5)
            else:
                run_date = prev_run_date.shift(months=+1).replace(day=1)
            if run_date.day != 26:
                run_days = 5
            else:
                run_days = (run_date.shift(months=+1).replace(day=1) - run_date).days
        if run_date.shift(days=+(run_days - 1)).naive > arrow.now().floor("day").naive:
            # Don't try to run into the future - this is a hindcast!!
            if parsed_args.full_month:
                logger.info(
                    f"not launching {run_date.format('YYYY-MM-DD')} run because it extends beyond today"
                )
                sftp_client.close()
                ssh_client.close()
                checklist = {"hindcast": {"host": host_name, "run id": "None"}}
                return checklist
            else:
                run_days = (
                    arrow.now().floor("day").naive - run_date.shift(days=-1).naive
                ).days
                logger.info(
                    f"launching {run_date.format('YYYY-MM-DD')} run for {run_days} days to end of today"
                )
        prev_namelist_info = _get_prev_run_namelist_info(
            ssh_client, sftp_client, host_name, prev_run_date, config
        )
        _edit_namelist_time(
            sftp_client, host_name, prev_namelist_info, run_date, run_days, config
        )
        walltime = (
            # NOTE: values >23:59:59 must be in seconds
            parsed_args.walltime or 30 * 60 * 60
            if parsed_args.full_month
            else parsed_args.walltime or "10:00:00"
        )
        _edit_run_desc(
            sftp_client,
            host_name,
            prev_run_date,
            prev_namelist_info,
            run_date,
            walltime,
            config,
        )
        run_id = f'{run_date.format("DDMMMYY").lower()}hindcast'
        _launch_run(ssh_client, host_name, run_id, prev_job_id, config)
    finally:
        sftp_client.close()
        ssh_client.close()
    checklist = {"hindcast": {"host": host_name, "run id": run_id}}
    return checklist


def _get_prev_run_queue_info(ssh_client, host_name, config):
    """
    :param :py:class:`paramiko.client.SSHClient`
    :param str host_name:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Run date of the previous hindcast run found on the queue,
             slurm job id number
    :rtype: 2-tuple (:py:class:`arrow.Arrow`, int)
    """
    queue_info_cmd = config["run"]["hindcast hosts"][host_name]["queue info cmd"]
    queue_info_func = {
        "/usr/bin/qstat": _get_qstat_queue_info,
        "/opt/software/slurm/bin/squeue": _get_squeue_queue_info,
    }[queue_info_cmd]
    users = config["run"]["hindcast hosts"][host_name]["users"]
    queue_info_lines = queue_info_func(ssh_client, host_name, queue_info_cmd, users)
    for queue_info in queue_info_lines:
        if "hindcast" in queue_info.strip().split()[1]:
            job_id, run_id = queue_info.strip().split()
            logger.info(f"using {run_id} job {job_id} on {host_name} as previous run")
            prev_run_date = arrow.get(run_id[:7], "DDMMMYY")
            return prev_run_date, job_id
    logger.error(f"no hindcast jobs found on {host_name} queue")
    raise WorkerError


def _get_qstat_queue_info(ssh_client, host_name, queue_info_cmd, users):
    """
    :param :py:class:`paramiko.client.SSHClient`
    :param str host_name:
    :param str queue_info_cmd:
    :param str users:

    :return: Lines from queue info cmd output showing job ids and run ids for users
    :rtype: list
    """
    stdout = ssh_sftp.ssh_exec_command(
        ssh_client, f"{queue_info_cmd} -u {users}", host_name, logger
    )
    if len(stdout.splitlines()) == 5:
        logger.error(f"no jobs found on {host_name} queue")
        raise WorkerError
    queue_info_lines = stdout.splitlines()[5:]
    queue_info_lines.reverse()
    queue_info_lines = [
        f"{line.split()[0].rsplit('.', 2)[0]} {line.split()[3]}"
        for line in queue_info_lines
    ]
    return queue_info_lines


def _get_squeue_queue_info(ssh_client, host_name, queue_info_cmd, users):
    """
    :param :py:class:`paramiko.client.SSHClient`
    :param str host_name:
    :param stgr queue_info_cmd:
    :param str users:

    :return: Lines from queue info cmd output showing job ids and run ids for users
    :rtype: list
    """
    stdout = ssh_sftp.ssh_exec_command(
        ssh_client,
        f'{queue_info_cmd} --user {users} --Format "jobid,name" --sort=i',
        host_name,
        logger,
    )
    if len(stdout.splitlines()) == 1:
        logger.error(f"no jobs found on {host_name} queue")
        raise WorkerError
    queue_info_lines = stdout.splitlines()[1:]
    queue_info_lines.reverse()
    return queue_info_lines


def _get_prev_run_namelist_info(
    ssh_client, sftp_client, host_name, prev_run_date, config
):
    """
    :param :py:class:`paramiko.client.SSHClient`
    :param :py:class:`paramiko.sftp_client.SFTPClient` sftp_client:
    :param str host_name:
    :param :py:class:`arrow.Arrow` prev_run_date:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Namespace of run timing info:
               itend: last time step number
               rdt: time step in seconds
    :rtype: :py:class:`types.SimpleNamespace`
    """
    scratch_dir = Path(config["run"]["hindcast hosts"][host_name]["scratch dir"])
    dmy = prev_run_date.format("DDMMMYY").lower()
    stdout = ssh_sftp.ssh_exec_command(
        ssh_client, f"ls -d {scratch_dir/dmy}*/namelist_cfg", host_name, logger
    )
    prev_namelist_cfg = stdout.strip()
    logger.info(f"found previous run namelist: {host_name}:{prev_namelist_cfg}")
    with tempfile.NamedTemporaryFile("wt") as namelist_cfg:
        sftp_client.get(prev_namelist_cfg, namelist_cfg.name)
        namelist = f90nml.read(namelist_cfg.name)
        prev_namelist_info = SimpleNamespace(
            itend=namelist["namrun"]["nn_itend"], rdt=namelist["namdom"]["rn_rdt"]
        )
    return prev_namelist_info


def _edit_namelist_time(
    sftp_client, host_name, prev_namelist_info, run_date, run_days, config
):
    """
    :param :py:class:`paramiko.sftp_client.SFTPClient` sftp_client:
    :param str host_name:
    :param :py:class:`types.SimpleNamespace` prev_namelist_info:
    :param :py:class:`arrow.Arrow` run_date:
    :param int run_days:
    :param :py:class:`nemo_nowcast.Config` config:
    """
    timesteps_per_day = 24 * 60 * 60 / prev_namelist_info.rdt
    itend = prev_namelist_info.itend + run_days * timesteps_per_day
    nn_stocklist = [0] * 10
    if run_days < 28:
        nn_stocklist[0] = int(itend)
    else:
        nn_stocklist[0:3] = [
            int(prev_namelist_info.itend + timesteps_per_day * 10),
            int(prev_namelist_info.itend + timesteps_per_day * 20),
            int(itend),
        ]
    patch = {
        "namrun": {
            "nn_it000": prev_namelist_info.itend + 1,
            "nn_itend": int(itend),
            "nn_date0": int(run_date.format("YYYYMMDD")),
            "nn_stocklist": nn_stocklist,
        }
    }
    run_prep_dir = Path(config["run"]["hindcast hosts"][host_name]["run prep dir"])
    namelist_time_tmpl = f"{run_prep_dir}/namelist.time"
    sftp_client.get(namelist_time_tmpl, "/tmp/hindcast.namelist.time")
    logger.debug(f"downloaded {host_name}:{run_prep_dir}/namelist.time")
    f90nml.patch(
        "/tmp/hindcast.namelist.time", patch, "/tmp/patched_hindcast.namelist.time"
    )
    logger.debug("patched namelist.time")
    sftp_client.put(
        "/tmp/patched_hindcast.namelist.time", f"{run_prep_dir}/namelist.time"
    )
    logger.debug(f"uploaded new {host_name}:{run_prep_dir}/namelist.time")


def _edit_run_desc(
    sftp_client,
    host_name,
    prev_run_date,
    prev_namelist_info,
    run_date,
    walltime,
    config,
    yaml_tmpl=Path("/tmp/hindcast_template.yaml"),
):
    """
    :param :py:class:`paramiko.sftp_client.SFTPClient` sftp_client:
    :param str host_name:
    :param :py:class:`arrow.Arrow` prev_run_date:
    :param :py:class:`types.SimpleNamespace` prev_namelist_info:
    :param :py:class:`arrow.Arrow` run_date:
    :param str walltime:
    :param :py:class:`nemo_nowcast.Config` config:
    :param :py:class:`pathlib.Path` yaml_tmpl:
    """
    run_prep_dir = Path(config["run"]["hindcast hosts"][host_name]["run prep dir"])
    sftp_client.get(f"{run_prep_dir}/hindcast_template.yaml", f"{yaml_tmpl}")
    with yaml_tmpl.open("rt") as run_desc_tmpl:
        run_desc = yaml.safe_load(run_desc_tmpl)
    logger.debug(f"downloaded {host_name}:{run_prep_dir}/{yaml_tmpl.name}")
    run_id = f'{run_date.format("DDMMMYY").lower()}hindcast'
    run_desc["run_id"] = run_id
    logger.debug(f"set run_id to {run_id}")
    run_desc["walltime"] = walltime
    logger.debug(f"set walltime to {walltime}")
    scratch_dir = Path(config["run"]["hindcast hosts"][host_name]["scratch dir"])
    prev_run_dir = scratch_dir / (prev_run_date.format("DDMMMYY").lower())
    restart_file = f"{prev_run_dir}/SalishSea_{prev_namelist_info.itend:08d}_restart.nc"
    run_desc["restart"]["restart.nc"] = restart_file
    logger.debug(f"set restart.nc to {restart_file}")
    restart_trc_file = (
        f"{prev_run_dir}/SalishSea_{prev_namelist_info.itend:08d}_restart_trc.nc"
    )
    run_desc["restart"]["restart_trc.nc"] = restart_trc_file
    logger.debug(f"set restart_trc.nc to {restart_trc_file}")
    with yaml_tmpl.open("wt") as run_desc_tmpl:
        yaml.safe_dump(run_desc, run_desc_tmpl, default_flow_style=False)
    sftp_client.put(f"{yaml_tmpl}", f"{run_prep_dir}/{run_id}.yaml")
    logger.debug(f"uploaded {host_name}:{run_prep_dir}/{run_id}.yaml")


def _launch_run(ssh_client, host_name, run_id, prev_job_id, config):
    """
    :param :py:class:`paramiko.client.SSHClient`
    :param str host_name:
    :param str run_id:
    :param int or None prev_job_id:
    :param :py:class:`nemo_nowcast.Config` config:
    """
    salishsea_cmd = config["run"]["hindcast hosts"][host_name]["salishsea cmd"]
    salishsea_exec = salishsea_cmd["executable"]
    run_options = salishsea_cmd["run options"] or ""
    run_envvars = salishsea_cmd["envvars"] or {}
    salishsea_prefix = (
        "; ".join(f"export {key}={value}" for key, value in run_envvars.items())
        if run_envvars
        else ""
    )
    salishsea_exec = (
        f"{salishsea_prefix}; {salishsea_exec}" if salishsea_prefix else salishsea_exec
    )
    run_prep_dir = Path(config["run"]["hindcast hosts"][host_name]["run prep dir"])
    run_desc = run_prep_dir / f"{run_id}.yaml"
    scratch_dir = Path(config["run"]["hindcast hosts"][host_name]["scratch dir"])
    results_dir = scratch_dir / run_id[:7]
    cmd = f"{salishsea_exec} run {run_desc} {results_dir} {run_options}"
    if prev_job_id:
        cmd = f"{cmd} --waitjob {prev_job_id} --nocheck-initial-conditions"
    try:
        ssh_sftp.ssh_exec_command(ssh_client, cmd, host_name, logger)
    except ssh_sftp.SSHCommandError as exc:
        for line in exc.stderr.splitlines():
            logger.error(line)
        raise WorkerError
    logger.info(f"{run_id} run submitted to scheduler on {host_name}")


if __name__ == "__main__":
    main()  # pragma: no cover
