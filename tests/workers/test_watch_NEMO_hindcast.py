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
"""Unit tests for SalishSeaCast watch_NEMO_hindcast worker.
"""
from pathlib import Path
import textwrap
from types import SimpleNamespace
from unittest.mock import call, Mock, patch

import arrow
import nemo_nowcast
import pytest

import nowcast.ssh_sftp
from nowcast.workers import watch_NEMO_hindcast


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                run:
                  hindcast hosts:
                    cedar:
                      ssh key: SalishSeaNEMO-nowcast_id_rsa
                      queue info cmd: /opt/software/slurm/bin/squeue
                      users: allen,dlatorne
                      scratch dir: scratch/hindcast
                
                    optimum:
                      ssh key: SalishSeaNEMO-nowcast_id_rsa
                      queue info cmd: /usr/bin/qstat
                      users: sallen,dlatorne
                      scratch dir: scratch/hindcast
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.watch_NEMO_hindcast.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_NEMO_hindcast.main()
        args, kwargs = m_worker.call_args
        assert args == ("watch_NEMO_hindcast",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_NEMO_hindcast.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_run_id_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_NEMO_hindcast.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("--run-id",)
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_NEMO_hindcast.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            watch_NEMO_hindcast.watch_NEMO_hindcast,
            watch_NEMO_hindcast.success,
            watch_NEMO_hindcast.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "watch_NEMO_hindcast" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["watch_NEMO_hindcast"]
        assert msg_registry["checklist key"] == "NEMO run"

    @pytest.mark.parametrize("msg", ("success", "failure", "crash"))
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["watch_NEMO_hindcast"]
        assert msg in msg_registry

    def test_run_hindcast_hosts_section(self, prod_config):
        run_hindcast_hosts = prod_config["run"]["hindcast hosts"]
        assert (
            run_hindcast_hosts["cedar-hindcast"]["ssh key"]
            == "SalishSeaNEMO-nowcast_id_rsa"
        )
        assert (
            run_hindcast_hosts["cedar-hindcast"]["queue info cmd"]
            == "/opt/software/slurm/bin/squeue"
        )
        assert run_hindcast_hosts["cedar-hindcast"]["users"] == "allen,dlatorne"
        assert (
            run_hindcast_hosts["cedar-hindcast"]["scratch dir"]
            == "/scratch/dlatorne/hindcast.201905"
        )

        assert (
            run_hindcast_hosts["optimum-hindcast"]["ssh key"]
            == "SalishSeaNEMO-nowcast_id_rsa"
        )
        assert (
            run_hindcast_hosts["optimum-hindcast"]["queue info cmd"] == "/usr/bin/qstat"
        )
        assert run_hindcast_hosts["optimum-hindcast"]["users"] == "sallen,dlatorne"
        assert (
            run_hindcast_hosts["optimum-hindcast"]["scratch dir"]
            == "/scratch/sallen/dlatorne/hindcast.201905"
        )


@pytest.mark.parametrize("host_name", ("cedar", "optimum"))
@patch("nowcast.workers.watch_NEMO_hindcast.logger", autospec=True)
class TestSuccess:
    """Unit test for success() function.
    """

    def test_success(self, m_logger, host_name):
        parsed_args = SimpleNamespace(host_name=host_name)
        msg_type = watch_NEMO_hindcast.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success"


@pytest.mark.parametrize("host_name", ("cedar", "optimum"))
@patch("nowcast.workers.watch_NEMO_hindcast.logger", autospec=True)
class TestFailure:
    """Unit test for failure() function.
    """

    def test_failure(self, m_logger, host_name):
        parsed_args = SimpleNamespace(host_name=host_name)
        msg_type = watch_NEMO_hindcast.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure"


@patch("nowcast.workers.watch_NEMO_hindcast.logger", autospec=True)
@patch(
    "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.sftp",
    return_value=(Mock(name="ssh_client"), Mock(name="sftp_client")),
    autospec=True,
)
class TestWatchNEMO_Hindcast:
    """Unit test for watch_NEMO_hindcast() function.
    """

    @patch("nowcast.workers.watch_NEMO_hindcast._SqueueHindcastJob", spec=True)
    def test_squeue_run_completed(self, m_job, m_sftp, m_logger, config):
        parsed_args = SimpleNamespace(host_name="cedar", run_id=None)
        m_job().host_name = parsed_args.host_name
        m_job().job_id, m_job().run_id = "9813234", "01jul18hindcast"
        m_job().is_queued.return_value = False
        m_job().tmp_run_dir = Path("tmp_run_dir")
        m_job().is_running.return_value = False
        m_job().get_completion_state.return_value = "completed"
        checklist = watch_NEMO_hindcast.watch_NEMO_hindcast(parsed_args, config)
        expected = {
            "hindcast": {
                "host": parsed_args.host_name,
                "run id": m_job().run_id,
                "run date": arrow.get(m_job().run_id[:7], "DDMMMYY").format(
                    "YYYY-MM-DD"
                ),
                "completed": True,
            }
        }
        assert checklist == expected

    @patch("nowcast.workers.watch_NEMO_hindcast._QstatHindcastJob", spec=True)
    def test_qstat_run_completed(self, m_job, m_sftp, m_logger, config):
        parsed_args = SimpleNamespace(host_name="optimum", run_id=None)
        m_job().host_name = parsed_args.host_name
        m_job().job_id, m_job().run_id = "62990.admin", "01jul18hindcast"
        m_job().is_queued.return_value = False
        m_job().tmp_run_dir = Path("tmp_run_dir")
        m_job().is_running.return_value = False
        m_job().get_completion_state.return_value = "completed"
        checklist = watch_NEMO_hindcast.watch_NEMO_hindcast(parsed_args, config)
        expected = {
            "hindcast": {
                "host": parsed_args.host_name,
                "run id": m_job().run_id,
                "run date": arrow.get(m_job().run_id[:7], "DDMMMYY").format(
                    "YYYY-MM-DD"
                ),
                "completed": True,
            }
        }
        assert checklist == expected

    @pytest.mark.parametrize("completion_state", ["cancelled", "aborted"])
    @patch("nowcast.workers.watch_NEMO_hindcast._SqueueHindcastJob", spec=True)
    def test_run_cancelled_or_aborted(
        self, m_job, m_sftp, m_logger, completion_state, config
    ):
        parsed_args = SimpleNamespace(host_name="cedar", run_id=None)
        m_job().host_name = parsed_args.host_name
        m_job().job_id, m_job().run_id = "9813234", "01jul18hindcast"
        m_job().is_queued.return_value = False
        m_job().tmp_run_dir = Path("tmp_run_dir")
        m_job().is_running.return_value = False
        m_job().get_completion_state.return_value = completion_state
        with pytest.raises(nemo_nowcast.WorkerError):
            watch_NEMO_hindcast.watch_NEMO_hindcast(parsed_args, config)


@patch("nowcast.workers.watch_NEMO_hindcast.logger", autospec=True)
class TestQstatHindcastJob:
    """Unit tests for _SqueueHindcastJob class."""

    def test_get_run_id(self, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job._get_queue_info = Mock(
            name="_get_queue_info",
            return_value=(
                "62991.admin.default.do dlatorne mpi 01jan13hindcast 22390 14 280 -- 06:00:00 R 00:20:53"
            ),
        )
        job.get_run_id()
        assert job.job_id == "62991.admin"
        assert job.run_id == "01jan13hindcast"
        assert m_logger.info.called

    def test_is_queued_job_not_found(self, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job._get_queue_info = Mock(name="_get_queue_info", return_value=None)
        with pytest.raises(nemo_nowcast.WorkerError):
            job.is_queued()
        assert m_logger.error.called

    def test_is_queued(self, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job._get_queue_info = Mock(
            name="_get_queue_info",
            return_value=(
                "62991.admin.default.do dlatorne mpi 01jan13hindcast 22390 14 280 -- 06:00:00 Q 00:20:53"
            ),
        )
        assert job.is_queued()
        assert m_logger.info.called

    def test_get_tmp_run_dir(self, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job.run_id = "21dec16hindcast"
        job._ssh_exec_command = Mock(
            name="_ssh_exec_command",
            return_value="/scratch/hindcast/01jan13hindcast_2019-07-06T122741.810587-0700",
        )
        job.get_tmp_run_dir()
        assert job.tmp_run_dir == Path(
            "/scratch/hindcast/01jan13hindcast_2019-07-06T122741.810587-0700"
        )
        assert m_logger.debug.called

    @patch("nowcast.workers.watch_NEMO_hindcast.f90nml.read", autospec=True)
    def test_get_run_info(self, m_f90nml_read, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job.tmp_run_dir = Path(
            "/scratch/hindcast/01jan13hindcast_2019-07-06T122741.810587-0700"
        )
        m_f90nml_read.return_value = {
            "namrun": {"nn_it000": 1, "nn_itend": 2160, "nn_date0": "20130101"},
            "namdom": {"rn_rdt": 40.0},
        }
        job.get_run_info()
        assert job.it000 == 1
        assert job.itend == 2160
        assert job.date0 == arrow.get("2013-01-01")
        assert job.rdt == 40.0
        assert m_logger.debug.call_count == 2

    def test_is_running_not_running(self, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job._get_job_state = Mock(name="_get_job_state", return_value="UNKNOWN")
        assert not job.is_running()

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command",
        side_effect=nowcast.ssh_sftp.SSHCommandError("cmd", "stdout", "stderr"),
        autospec=True,
    )
    def test_is_running_no_time_step_file(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job._get_job_state = Mock(name="_get_job_state", return_value="R")
        assert job.is_running()
        assert m_logger.info.called

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command",
        side_effect=[
            "1\n",
            nowcast.ssh_sftp.SSHCommandError("cmd", "stdout", "stderr"),
        ],
        autospec=True,
    )
    def test_is_running_no_ocean_output(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job._get_job_state = Mock(name="_get_job_state", return_value="R")
        job._report_progress = Mock(name="_report_progress")
        assert not job.is_running()
        assert m_logger.error.called

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command",
        side_effect=["1\n", "E R R O R\nE R R O R\n"],
        autospec=True,
    )
    def test_is_running_ocean_output_errors_cancel_run(
        self, m_ssh_exec_cmd, m_logger, config
    ):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job._get_job_state = Mock(name="_get_job_state", return_value="R")
        job._report_progress = Mock(name="_report_progress")
        job._ssh_exec_command = Mock(name="_ssh_exec_command")
        assert not job.is_running()
        assert m_logger.error.called
        job._ssh_exec_command.assert_called_once_with(
            f"/usr/bin/qdel {job.job_id}",
            f"{job.run_id} on {job.host_name}: cancelled {job.job_id}",
        )

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command",
        side_effect=["1\n", ""],
        autospec=True,
    )
    def test_is_running(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedoptimumar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_job_state = Mock(name="_get_job_state", return_value="R")
        job._report_progress = Mock(name="_report_progress")
        assert job.is_running()

    @pytest.mark.parametrize("exception", [nemo_nowcast.WorkerError, AttributeError])
    def test_get_job_state_unknown(self, m_logger, exception, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job._get_queue_info = Mock(name="_get_queue_info", return_value=None)
        state = job._get_job_state()
        assert m_logger.info.called
        assert state == "UNKNOWN"

    def test_get_job_state_running(self, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job._get_queue_info = Mock(
            name="_get_queue_info",
            return_value=(
                "62991.admin.default.do dlatorne mpi 01jan13hindcast 22390 14 280 -- 06:00:00 R 00:20:53"
            ),
        )
        state = job._get_job_state()
        assert state == "R"

    def test_report_progress(self, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job.run_id = "11jan13hindcast"
        job.it000 = 21601
        job.itend = 43200
        job.date0 = arrow.get("2013-01-11")
        job.rdt = 40.0
        job._report_progress("29697\n")
        m_logger.info.assert_called_once_with(
            f"11jan13hindcast on {job.host_name}: timestep: "
            f"29697 = 2013-01-14 17:57:20 UTC, 37.5% complete"
        )

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command",
        return_value="/scratch/hindcast/01jan13hindcast_2019-07-06T122741.810587-0700",
        autospec=True,
    )
    def test_ssh_exec_command(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        stdout = job._ssh_exec_command(f"ls -dtr {job.scratch_dir}/*hindcast*")
        assert (
            stdout == "/scratch/hindcast/01jan13hindcast_2019-07-06T122741.810587-0700"
        )
        assert not m_logger.info.called

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True
    )
    def test_get_queue_info_no_job_id_no_jobs(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        m_ssh_exec_cmd.return_value = ""
        with pytest.raises(nemo_nowcast.WorkerError):
            job._get_queue_info()

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True
    )
    def test_get_queue_info_job_id_no_jobs(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job.job_id = "62991.admin"
        m_ssh_exec_cmd.return_value = ""
        queue_info = job._get_queue_info()
        assert queue_info is None

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True
    )
    def test_get_queue_info_run_id(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job.run_id = "01jan13hindcast"
        m_ssh_exec_cmd.return_value = textwrap.dedent(
            """\
            
            admin.default.domain: 
                                                                                              Req'd    Req'd       Elap
            Job ID                  Username    Queue    Jobname          SessID  NDS   TSK   Memory   Time    S   Time
            ----------------------- ----------- -------- ---------------- ------ ----- ------ ------ --------- - ---------
            62991.admin.default.do  dlatorne    mpi      01jan13hindcast  22390  14    280    --     06:00:00  R 00:20:53
            """
        )
        queue_info = job._get_queue_info()
        assert (
            queue_info
            == "62991.admin.default.do  dlatorne    mpi      01jan13hindcast  22390  14    280    --     06:00:00  R 00:20:53"
        )

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True
    )
    def test_get_queue_info_run_id_ignore_completed(
        self, m_ssh_exec_cmd, m_logger, config
    ):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        job.run_id = "11jan13hindcast"
        m_ssh_exec_cmd.return_value = textwrap.dedent(
            """\
            
            admin.default.domain: 
                                                                                              Req'd    Req'd       Elap
            Job ID                  Username    Queue    Jobname          SessID  NDS   TSK   Memory   Time    S   Time
            ----------------------- ----------- -------- ---------------- ------ ----- ------ ------ --------- - ---------
            62991.admin.default.do  dlatorne    mpi      01jan13hindcast  22390  14    280    --     10:00:00  C      --
            62995.admin.default.do  dlatorne    mpi      11jan13hindcast  28434  14    280    --     10:00:00  R 00:20:53
            """
        )
        queue_info = job._get_queue_info()
        assert (
            queue_info
            == "62995.admin.default.do  dlatorne    mpi      11jan13hindcast  28434  14    280    --     10:00:00  R 00:20:53"
        )

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True
    )
    def test_get_queue_info_no_run_id(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        m_ssh_exec_cmd.return_value = textwrap.dedent(
            """\

            admin.default.domain: 
                                                                                              Req'd    Req'd       Elap
            Job ID                  Username    Queue    Jobname          SessID  NDS   TSK   Memory   Time    S   Time
            ----------------------- ----------- -------- ---------------- ------ ----- ------ ------ --------- - ---------
            62991.admin.default.do  dlatorne    mpi      01jan13hindcast  22390  14    280    --     06:00:00  R 00:20:53
            """
        )
        queue_info = job._get_queue_info()
        assert (
            queue_info
            == "62991.admin.default.do  dlatorne    mpi      01jan13hindcast  22390  14    280    --     06:00:00  R 00:20:53"
        )

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True
    )
    def test_get_queue_info_no_run_id_ignore_completed(
        self, m_ssh_exec_cmd, m_logger, config
    ):
        job = watch_NEMO_hindcast._QstatHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "optimum",
            config["run"]["hindcast hosts"]["optimum"]["users"],
            Path(config["run"]["hindcast hosts"]["optimum"]["scratch dir"]),
        )
        m_ssh_exec_cmd.return_value = textwrap.dedent(
            """\

            admin.default.domain: 
                                                                                              Req'd    Req'd       Elap
            Job ID                  Username    Queue    Jobname          SessID  NDS   TSK   Memory   Time    S   Time
            ----------------------- ----------- -------- ---------------- ------ ----- ------ ------ --------- - ---------
            62991.admin.default.do  dlatorne    mpi      01jan13hindcast  22390  14    280    --     10:00:00  C      --
            62995.admin.default.do  dlatorne    mpi      11jan13hindcast  28434  14    280    --     10:00:00  R 00:20:53
            """
        )
        queue_info = job._get_queue_info()
        assert (
            queue_info
            == "62995.admin.default.do  dlatorne    mpi      11jan13hindcast  28434  14    280    --     10:00:00  R 00:20:53"
        )


@patch("nowcast.workers.watch_NEMO_hindcast.logger", autospec=True)
class TestSqueueHindcastJob:
    """Unit tests for _SqueueHindcastJob class."""

    def test_get_run_id(self, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_queue_info = Mock(
            name="_get_queue_info",
            return_value="12426878 21dec16hindcast RUNNING None 2018-10-07T14:13:59",
        )
        job.get_run_id()
        assert job.job_id == "12426878"
        assert job.run_id == "21dec16hindcast"
        assert m_logger.info.called

    def test_is_queued_job_not_found(self, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_queue_info = Mock(name="_get_queue_info", return_value=None)
        with pytest.raises(nemo_nowcast.WorkerError):
            job.is_queued()
        assert m_logger.error.called

    def test_is_queued_not_pending(self, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_queue_info = Mock(
            name="_get_queue_info",
            return_value="12426878 21dec16hindcast RUNNING None 2018-10-07T14:13:59",
        )
        assert not job.is_queued()

    def test_is_queued_pending_due_to_resources(self, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_queue_info = Mock(
            name="_get_queue_info",
            return_value="12426878 21dec16hindcast PENDING resources N/A",
        )
        assert job.is_queued()
        assert m_logger.info.call_args[0][0].endswith("pending due to resources")

    def test_is_queued_pending_and_scheduled(self, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_queue_info = Mock(
            name="_get_queue_info",
            return_value="12426878 21dec16hindcast PENDING resources 2018-10-07T14:13:59",
        )
        assert job.is_queued()
        assert m_logger.info.call_args[0][0].endswith(
            "pending due to resources, scheduled for 2018-10-07T14:13:59"
        )

    def test_get_tmp_run_dir(self, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job.run_id = "21dec16hindcast"
        job._ssh_exec_command = Mock(
            name="_ssh_exec_command",
            return_value="/scratch/hindcast/21dec16hindcast_2018-10-06T195251.255493-0700",
        )
        job.get_tmp_run_dir()
        assert job.tmp_run_dir == Path(
            "/scratch/hindcast/21dec16hindcast_2018-10-06T195251.255493-0700"
        )
        assert m_logger.debug.called

    @patch("nowcast.workers.watch_NEMO_hindcast.f90nml.read", autospec=True)
    def test_get_run_info(self, m_f90nml_read, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job.tmp_run_dir = Path(
            "/scratch/hindcast/21dec16hindcast_2018-10-06T195251.255493-0700"
        )
        m_f90nml_read.return_value = {
            "namrun": {
                "nn_it000": 1_658_881,
                "nn_itend": 1_682_640,
                "nn_date0": "20161221",
            },
            "namdom": {"rn_rdt": 40.0},
        }
        job.get_run_info()
        assert job.it000 == 1_658_881
        assert job.itend == 1_682_640
        assert job.date0 == arrow.get("2016-12-21")
        assert job.rdt == 40.0
        assert m_logger.debug.call_count == 2

    def test_is_running_not_running(self, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_job_state = Mock(name="_get_job_state", return_value="UNKNOWN")
        assert not job.is_running()

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command",
        side_effect=nowcast.ssh_sftp.SSHCommandError("cmd", "stdout", "stderr"),
        autospec=True,
    )
    def test_is_running_no_time_step_file(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_job_state = Mock(name="_get_job_state", return_value="RUNNING")
        assert job.is_running()
        assert m_logger.info.called

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command",
        side_effect=[
            "1658943\n",
            nowcast.ssh_sftp.SSHCommandError("cmd", "stdout", "stderr"),
        ],
        autospec=True,
    )
    def test_is_running_no_ocean_output(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_job_state = Mock(name="_get_job_state", return_value="RUNNING")
        job._report_progress = Mock(name="_report_progress")
        assert not job.is_running()
        assert m_logger.error.called

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command",
        side_effect=["1658943\n", "E R R O R\nE R R O R\n"],
        autospec=True,
    )
    def test_is_running_ocean_output_errors_cancel_run(
        self, m_ssh_exec_cmd, m_logger, config
    ):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_job_state = Mock(name="_get_job_state", return_value="RUNNING")
        job._report_progress = Mock(name="_report_progress")
        job._ssh_exec_command = Mock(name="_ssh_exec_command")
        assert not job.is_running()
        assert m_logger.error.called
        job._ssh_exec_command.assert_called_once_with(
            f"/opt/software/slurm/bin/scancel {job.job_id}",
            f"{job.run_id} on {job.host_name}: cancelled {job.job_id}",
        )

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command",
        side_effect=["1658943\n", "E R R O R\n"],
        autospec=True,
    )
    def test_is_running_handle_stuck_job(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_job_state = Mock(name="_get_job_state", return_value="RUNNING")
        job._report_progress = Mock(name="_report_progress")
        job._ssh_exec_command = Mock(name="_ssh_exec_command")
        job._handle_stuck_job = Mock(name="_handle_stuck_job")
        job.is_queued = Mock(name="is_queued", return_value=False)
        job.get_tmp_run_dir = Mock(name="get_tmp_run_dir")
        job.get_run_info = Mock(name="get_run_info")
        assert job.is_running()
        assert m_logger.error.called
        job._ssh_exec_command.assert_called_once_with(
            f"/opt/software/slurm/bin/scancel {job.job_id}",
            f"{job.run_id} on {job.host_name}: cancelled {job.job_id}",
        )
        assert job._handle_stuck_job.called

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command",
        side_effect=["1658943\n", ""],
        autospec=True,
    )
    def test_is_running(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_job_state = Mock(name="_get_job_state", return_value="RUNNING")
        job._report_progress = Mock(name="_report_progress")
        assert job.is_running()

    @pytest.mark.parametrize("exception", [nemo_nowcast.WorkerError, AttributeError])
    def test_get_job_state_unknown(self, m_logger, exception, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_queue_info = Mock(name="_get_queue_info", return_value=None)
        state = job._get_job_state()
        assert m_logger.info.called
        assert state == "UNKNOWN"

    def test_get_job_state_running(self, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._get_queue_info = Mock(
            name="_get_queue_info",
            return_value="12426878 21dec16hindcast RUNNING N/A 2018-10-07T14:13:59",
        )
        state = job._get_job_state()
        assert state == "RUNNING"

    def test_report_progress(self, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job.run_id = "01oct18hindcast"
        job.it000 = 1_658_881
        job.itend = 1_682_640
        job.date0 = arrow.get("2016-12-21")
        job.rdt = 40.0
        job._report_progress("1658943\n")
        m_logger.info.assert_called_once_with(
            f"01oct18hindcast on {job.host_name}: timestep: "
            f"1658943 = 2016-12-21 00:41:20 UTC, 0.3% complete"
        )

    def test_handle_stuck_job(self, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job.run_id = "21dec16hindcast"
        job.tmp_run_dir = (
            "/scratch/hindcast/21dec16hindcast_2018-10-06T195251.255493-0700"
        )
        job._ssh_exec_command = Mock(
            name="_ssh_exec_command",
            side_effect=[
                "",
                "/scratch/hindcast/01jan17hindcast_2018-10-07T141411.374009-0700",
                "",
            ],
        )
        job._get_queue_info = Mock(
            name="_get_queue_info",
            return_value="12426878 21dec16hindcast PENDING resources 2018-10-07T14:13:59",
        )
        job._handle_stuck_job()
        assert job._ssh_exec_command.call_args_list == [
            call(
                "/opt/software/slurm/bin/sbatch "
                "/scratch/hindcast/21dec16hindcast_2018-10-06T195251.255493-0700/SalishSeaNEMO.sh",
                "21dec16hindcast on cedar: re-queued",
            ),
            call(f"ls -dtr {job.scratch_dir}/*hindcast*"),
            call(
                "/opt/software/slurm/bin/sbatch -d afterok:12426878 "
                "/scratch/hindcast/01jan17hindcast_2018-10-07T141411.374009-0700/SalishSeaNEMO.sh",
                "01jan17hindcast on cedar: re-queued",
            ),
        ]
        assert m_logger.debug.called

    def test_get_completion_state_unknown(self, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job._ssh_exec_command = Mock(
            name="_ssh_exec_command", return_value="State\n----------\n"
        )
        state = job.get_completion_state()
        assert state == "unknown"
        assert m_logger.debug.called

    @pytest.mark.parametrize(
        "job_state, expected",
        [
            ("COMPLETED", "completed"),
            ("CANCELLED", "cancelled"),
            ("ABORTED", "aborted"),
            ("FOO", "aborted"),
        ],
    )
    def test_get_completion_state(self, m_logger, job_state, expected, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        job.run_id = "01mar17hindcast"
        job._ssh_exec_command = Mock(
            name="_ssh_exec_command", return_value=f"State\n----------\n{job_state}\n"
        )
        state = job.get_completion_state()
        assert state == expected
        m_logger.info.assert_called_once_with(
            f"{job.run_id} on {job.host_name}: {job_state}"
        )

    @patch(
        "nowcast.workers.watch_NEMO_hindcast.ssh_sftp.ssh_exec_command",
        return_value="/scratch/hindcast/01jan17hindcast_2018-10-07T141411.374009-0700",
        autospec=True,
    )
    def test_ssh_exec_command(self, m_ssh_exec_cmd, m_logger, config):
        job = watch_NEMO_hindcast._SqueueHindcastJob(
            Mock(name="ssh_client"),
            Mock(name="sftp_client"),
            "cedar",
            config["run"]["hindcast hosts"]["cedar"]["users"],
            Path(config["run"]["hindcast hosts"]["cedar"]["scratch dir"]),
        )
        stdout = job._ssh_exec_command(f"ls -dtr {job.scratch_dir}/*hindcast*")
        assert (
            stdout == "/scratch/hindcast/01jan17hindcast_2018-10-07T141411.374009-0700"
        )
        assert not m_logger.info.called
