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
"""Unit tests for SalishSeaCast watch_NEMO_agrif worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock

import arrow
import nemo_nowcast
import pytest

import nowcast.ssh_sftp
from nowcast.workers import watch_NEMO_agrif


@patch("nowcast.workers.watch_NEMO_agrif.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_NEMO_agrif.main()
        args, kwargs = m_worker.call_args
        assert args == ("watch_NEMO_agrif",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_NEMO_agrif.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_NEMO_agrif.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_job_id_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_NEMO_agrif.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("job_id",)
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_NEMO_agrif.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            watch_NEMO_agrif.watch_NEMO_agrif,
            watch_NEMO_agrif.success,
            watch_NEMO_agrif.failure,
        )


@patch("nowcast.workers.watch_NEMO_agrif.logger", autospec=True)
class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, m_logger):
        parsed_args = SimpleNamespace(host_name="orcinus", job_id="9305855.orca2.ibb")
        msg_type = watch_NEMO_agrif.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success"


@patch("nowcast.workers.watch_NEMO_agrif.logger", autospec=True)
class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, m_logger):
        parsed_args = SimpleNamespace(host_name="orcinus", job_id="9305855.orca2.ibb")
        msg_type = watch_NEMO_agrif.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure"


@patch("nowcast.workers.watch_NEMO_agrif.logger", autospec=True)
@patch(
    "nowcast.workers.watch_NEMO_agrif.ssh_sftp.sftp",
    return_value=(Mock(name="ssh_client"), Mock(name="sftp_client")),
    autospec=True,
)
@patch(
    "nowcast.workers.watch_NEMO_agrif._get_run_id",
    return_value="23apr18nowcast-agrif",
    autospec=True,
)
@patch("nowcast.workers.watch_NEMO_agrif._is_queued", return_value=False, autospec=True)
@patch(
    "nowcast.workers.watch_NEMO_agrif._get_tmp_run_dir",
    return_value="tmp_run_dir",
    autospec=True,
)
@patch(
    "nowcast.workers.watch_NEMO_agrif._get_run_info",
    return_value=SimpleNamespace(),
    autospec=True,
)
@patch(
    "nowcast.workers.watch_NEMO_agrif._is_running", return_value=False, autospec=True
)
class TestWatchNEMO_AGRIF:
    """Unit test for watch_NEMO_agrif() function."""

    def test_checklist(
        self,
        m_is_running,
        m_get_run_info,
        m_get_tmp_run_dir,
        m_is_queued,
        m_get_run_id,
        m_sftp,
        m_logger,
    ):
        parsed_args = SimpleNamespace(host_name="orcinus", job_id="9305855.orca2.ibb")
        config = {
            "run": {
                "enabled hosts": {
                    "orcinus": {
                        "ssh key": "SalishSeaNEMO-nowcast_id_rsa",
                        "scratch dir": "scratch/nowcast-agrif",
                    }
                }
            }
        }
        checklist = watch_NEMO_agrif.watch_NEMO_agrif(parsed_args, config)
        expected = {
            "nowcast-agrif": {
                "host": "orcinus",
                "job id": "9305855",
                "run date": "2018-04-23",
                "completed": True,
            }
        }
        assert checklist == expected


@patch("nowcast.workers.watch_NEMO_agrif.logger", autospec=True)
@patch(
    "nowcast.workers.watch_NEMO_agrif._get_queue_info",
    return_value="Job_Name = 23apr18nowcast-agrif\n",
    autospec=True,
)
class TestGetRunId:
    """Unit test for _get_run_id() function."""

    def test_get_run_id(self, m_get_queue_info, m_logger):
        ssh_client = Mock(name="ssh_client")
        run_id = watch_NEMO_agrif._get_run_id(ssh_client, "orcinus", "9305855")
        m_get_queue_info.assert_called_once_with(ssh_client, "orcinus", "9305855")
        assert m_logger.info.called
        assert run_id == "23apr18nowcast-agrif"


@patch("nowcast.workers.watch_NEMO_agrif.logger", autospec=True)
@patch("nowcast.workers.watch_NEMO_agrif._get_queue_info", autospec=True)
class TestIsQueued:
    """Unit test for _is_queued() function."""

    @pytest.mark.parametrize(
        "queue_info, expected", [("job_state = Q\n", True), ("job_state = R\n", False)]
    )
    def test_is_queued(self, m_get_queue_info, m_logger, queue_info, expected):
        m_get_queue_info.return_value = queue_info
        ssh_client = Mock(name="ssh_client")
        is_queued = watch_NEMO_agrif._is_queued(
            ssh_client, "orcinus", "9305855", "24apr18nowcast-agrif"
        )
        m_get_queue_info.assert_called_once_with(ssh_client, "orcinus", "9305855")
        if expected:
            assert m_logger.info.called
            assert is_queued
        else:
            assert not is_queued


@patch("nowcast.workers.watch_NEMO_agrif.logger", autospec=True)
@patch("nowcast.workers.watch_NEMO_agrif._get_queue_info", autospec=True)
class TestIsRunning:
    """Unit test for _is_running() function."""

    def test_job_not_on_queue(self, m_get_queue_info, m_logger):
        m_get_queue_info.return_value = "job_state = UNKNOWN\n"
        ssh_client = Mock(name="ssh_client")
        run_info = SimpleNamespace(
            it000=2_360_881, itend=2_363_040, date0=arrow.get("2018-04-24"), rdt=40
        )
        is_running = watch_NEMO_agrif._is_running(
            ssh_client,
            "orcinus",
            "9305855",
            "24apr18nowcast-agrif",
            Path("tmp_run_dir"),
            run_info,
        )
        m_get_queue_info.assert_called_once_with(
            ssh_client, "orcinus", "9305855", ignore_unknown_job=True
        )
        assert not is_running

    @pytest.mark.parametrize(
        "queue_info, expected", [("job_state = R\n", True), ("job_state = Q\n", False)]
    )
    @patch(
        "nowcast.workers.watch_NEMO_agrif.ssh_sftp.ssh_exec_command",
        return_value="2361000\n",
        autospec=True,
    )
    def test_is_running(
        self, m_ssh_exec_command, m_get_queue_info, m_logger, queue_info, expected
    ):
        m_get_queue_info.return_value = queue_info
        ssh_client = Mock(name="ssh_client")
        run_info = SimpleNamespace(
            it000=2_360_881, itend=2_363_040, date0=arrow.get("2018-04-24"), rdt=40
        )
        is_running = watch_NEMO_agrif._is_running(
            ssh_client,
            "orcinus",
            "9305855",
            "24apr18nowcast-agrif",
            Path("tmp_run_dir"),
            run_info,
        )
        m_get_queue_info.assert_called_once_with(
            ssh_client, "orcinus", "9305855", ignore_unknown_job=True
        )
        if expected:
            assert m_logger.info.called
            assert is_running
        else:
            assert not is_running

    @patch(
        "nowcast.workers.watch_NEMO_agrif.ssh_sftp.ssh_exec_command",
        side_effect=nowcast.ssh_sftp.SSHCommandError("cmd", "stdout", "stderr"),
        autospec=True,
    )
    def test_no_time_step_file(self, m_ssh_exec_command, m_get_queue_info, m_logger):
        m_get_queue_info.return_value = "job_state = R\n"
        ssh_client = Mock(name="ssh_client")
        run_info = SimpleNamespace(
            it000=2_360_881, itend=2_363_040, date0=arrow.get("2018-04-24"), rdt=40
        )
        is_running = watch_NEMO_agrif._is_running(
            ssh_client,
            "orcinus",
            "9305855",
            "24apr18nowcast-agrif",
            Path("tmp_run_dir"),
            run_info,
        )
        m_get_queue_info.assert_called_once_with(
            ssh_client, "orcinus", "9305855", ignore_unknown_job=True
        )
        assert m_logger.info.called
        assert is_running


@patch("nowcast.workers.watch_NEMO_agrif.logger", autospec=True)
class TestGetQueueInfo:
    """Unit tests for _get_queue_info() function."""

    @patch(
        "nowcast.workers.watch_NEMO_agrif.ssh_sftp.ssh_exec_command",
        return_value="job_state = R\n",
        autospec=True,
    )
    def test_get_queue_info(self, m_ssh_exec_cmd, m_logger):
        m_ssh_client = Mock(name="ssh_client")
        stdout = watch_NEMO_agrif._get_queue_info(m_ssh_client, "orcinus", "9305855")
        m_ssh_exec_cmd.assert_called_once_with(
            m_ssh_client,
            "/global/system/torque/bin/qstat -f -1 9305855",
            "orcinus",
            m_logger,
        )
        assert stdout == "job_state = R\n"

    @patch(
        "nowcast.workers.watch_NEMO_agrif.ssh_sftp.ssh_exec_command",
        side_effect=nowcast.ssh_sftp.SSHCommandError("cmd", "stdout", "stderr"),
        autospec=True,
    )
    def test_ssh_error(self, m_ssh_exec_cmd, m_logger):
        m_ssh_client = Mock(name="ssh_client")
        with pytest.raises(nemo_nowcast.WorkerError):
            watch_NEMO_agrif._get_queue_info(m_ssh_client, "orcinus", "9305855")

    @patch(
        "nowcast.workers.watch_NEMO_agrif.ssh_sftp.ssh_exec_command",
        side_effect=nowcast.ssh_sftp.SSHCommandError(
            "cmd", "stdout", "qstat: Unknown Job Id 9305855.orca2.ibb\n"
        ),
        autospec=True,
    )
    def test_ignore_unknown_job(self, m_ssh_exec_cmd, m_logger):
        m_ssh_client = Mock(name="ssh_client")
        stdout = watch_NEMO_agrif._get_queue_info(
            m_ssh_client, "orcinus", "9305855", ignore_unknown_job=True
        )
        assert stdout == "job_state = UNKNOWN\n"


@patch("nowcast.workers.watch_NEMO_agrif.logger", autospec=True)
@patch(
    "nowcast.workers.watch_NEMO_agrif.ssh_sftp.ssh_exec_command",
    return_value="scratch/07may18nowcast-agrif_xxx\n",
    autospec=True,
)
class TestGetTmpRunDir:
    """Unit test for _get_tmp_run_dir() functions."""

    def test_get_tmp_run_dir(self, m_ssh_exec_cmd, m_logger):
        m_ssh_client = Mock(name="ssh_client")
        tmp_run_dir = watch_NEMO_agrif._get_tmp_run_dir(
            m_ssh_client, "orcinus", Path("scratch"), "07may18nowcast-agrif"
        )
        m_ssh_exec_cmd.assert_called_once_with(
            m_ssh_client, "ls -d scratch/07may18nowcast-agrif_*", "orcinus", m_logger
        )
        assert m_logger.debug.called
        assert tmp_run_dir == Path("scratch/07may18nowcast-agrif_xxx")


@patch("nowcast.workers.watch_NEMO_agrif.logger", autospec=True)
@patch("nowcast.workers.run_NEMO_hindcast.f90nml.read", autospec=True)
class TestGetRunInfo:
    """Unit test for _get_run_info() function."""

    def test_get_run_info(self, m_f90nml_read, m_logger):
        m_sftp_client = Mock(name="sftp_client")
        p_named_tmp_file = patch(
            "nowcast.workers.watch_NEMO_agrif.tempfile.NamedTemporaryFile",
            autospec=True,
        )
        m_f90nml_read.return_value = {
            "namrun": {
                "nn_it000": 2_360_881,
                "nn_itend": 2_363_040,
                "nn_date0": 20_180_508,
            },
            "namdom": {"rn_rdt": 40.0},
        }
        with p_named_tmp_file as m_named_tmp_file:
            run_info = watch_NEMO_agrif._get_run_info(
                m_sftp_client, "orcinus", Path("scratch/07may18nowcst-agrif_xxx")
            )
        m_sftp_client.get.assert_called_once_with(
            "scratch/07may18nowcst-agrif_xxx/namelist_cfg",
            m_named_tmp_file().__enter__().name,
        )
        assert m_logger.debug.called
        assert run_info == SimpleNamespace(
            it000=2_360_881, itend=2_363_040, date0=arrow.get("2018-05-08"), rdt=40.0
        )
