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

# SPDX-License-Identifier: Apache-2.0


"""Unit tests for SalishSeaCast watch_NEMO worker."""
import subprocess
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, Mock, patch

import arrow
import nemo_nowcast
import pytest
from nemo_nowcast import NowcastWorker, Message

from nowcast.workers import watch_NEMO


@pytest.fixture
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                run types:
                  nowcast:
                    duration: 1  # day
                  nowcast-green:
                    duration: 1  # day
                  forecast:
                    duration: 1.5  # days
                  forecast2:
                    duration: 1.25  # days
                run:
                  enabled hosts:
                    arbutus.cloud:
                      run types:
                        nowcast:
                          results: results/SalishSea/nowcast/
                        nowcast-green:
                          results: results/SalishSea/nowcast-green/
                        forecast:
                          results: results/SalishSea/forecast/
                        forecast2:
                          results: results/SalishSea/forecast2/
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(watch_NEMO, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = watch_NEMO.main()
        assert worker.name == "watch_NEMO"
        assert worker.description.startswith(
            "SalishSeaCast worker that monitors and reports on the progress of a run on the cloud"
        )

    def test_add_host_name_arg(self, mock_worker):
        worker = watch_NEMO.main()
        assert worker.cli.parser._actions[3].dest == "host_name"
        assert worker.cli.parser._actions[3].help

    def test_add_run_type_arg(self, mock_worker):
        worker = watch_NEMO.main()
        assert worker.cli.parser._actions[4].dest == "run_type"
        expected = {"nowcast", "nowcast-green", "forecast", "forecast2"}
        assert worker.cli.parser._actions[4].choices == expected
        assert worker.cli.parser._actions[4].help


@patch("nowcast.workers.watch_NEMO.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function."""

    @pytest.mark.parametrize(
        "run_type, host_name",
        [
            ("nowcast", "arbutus.cloud-nowcast"),
            ("nowcast-green", "arbutus.cloud-nowcast"),
            ("forecast", "arbutus.cloud-nowcast"),
            ("forecast2", "arbutus.cloud-nowcast"),
        ],
    )
    def test_success(self, m_logger, run_type, host_name):
        parsed_args = SimpleNamespace(host_name=host_name, run_type=run_type)
        msg_type = watch_NEMO.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize(
    "run_type, host_name",
    [
        ("nowcast", "arbutus.cloud-nowcast"),
        ("nowcast-green", "arbutus.cloud-nowcast"),
        ("forecast", "arbutus.cloud-nowcast"),
        ("forecast2", "arbutus.cloud-nowcast"),
    ],
)
@patch("nowcast.workers.watch_NEMO.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, m_logger, run_type, host_name):
        parsed_args = SimpleNamespace(host_name=host_name, run_type=run_type)
        msg_type = watch_NEMO.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {run_type}"


@pytest.mark.parametrize(
    "run_type, host_name",
    [
        ("nowcast", "arbutus.cloud-nowcast"),
        ("nowcast-green", "arbutus.cloud-nowcast"),
        ("forecast", "arbutus.cloud-nowcast"),
        ("forecast2", "arbutus.cloud-nowcast"),
    ],
)
@patch("nowcast.workers.watch_NEMO.logger", autospec=True)
@patch("nowcast.workers.watch_NEMO._find_run_pid", autospec=True)
@patch("nowcast.workers.watch_NEMO._pid_exists", autospec=True)
@patch("nowcast.workers.watch_NEMO.f90nml.read", autospec=True)
@patch(
    "nowcast.workers.watch_NEMO._confirm_run_success", return_value=True, autospec=True
)
class TestWatchNEMO:
    """Unit tests for watch_NEMO function."""

    def test_checklist(
        self,
        m_confirm,
        m_nml_read,
        m_pid_exists,
        m_find_run_pid,
        m_logger,
        run_type,
        host_name,
        config,
    ):
        m_nml_read.return_value = {
            "namrun": {"nn_it000": 1, "nn_itend": 2160, "nn_date0": 20_171_113},
            "namdom": {"rn_rdt": 40},
        }
        m_pid_exists.return_value = False
        parsed_args = SimpleNamespace(host_name=host_name, run_type=run_type)
        tell_manager = Mock(
            spec=NowcastWorker.tell_manager,
            return_value=Message(
                "manager",
                "ack",
                payload={
                    run_type: {
                        "run dir": "tmp_run_dir",
                        "run exec cmd": "bash SalishSeaNEMO.sh",
                        "run date": "2017-11-13",
                    }
                },
            ),
        )
        checklist = watch_NEMO.watch_NEMO(parsed_args, config, tell_manager)
        expected = {
            run_type: {"host": host_name, "run date": "2017-11-13", "completed": True}
        }
        assert checklist == expected

    def test_time_step_not_found(
        self,
        m_confirm,
        m_nml_read,
        m_pid_exists,
        m_find_run_pid,
        m_logger,
        run_type,
        host_name,
        config,
        tmpdir,
    ):
        tmp_run_dir = tmpdir.ensure_dir("tmp_run_dir")
        m_nml_read.return_value = {
            "namrun": {"nn_it000": 1, "nn_itend": 2160, "nn_date0": 20_171_113},
            "namdom": {"rn_rdt": 40},
        }
        m_pid_exists.side_effect = (True, False)
        parsed_args = SimpleNamespace(host_name=host_name, run_type=run_type)
        tell_manager = Mock(
            spec=NowcastWorker.tell_manager,
            return_value=Message(
                "manager",
                "ack",
                payload={
                    run_type: {
                        "run dir": tmp_run_dir,
                        "run exec cmd": "bash SalishSeaNEMO.sh",
                        "run date": "2017-11-13",
                    }
                },
            ),
        )
        watch_NEMO.POLL_INTERVAL = 0
        watch_NEMO.watch_NEMO(parsed_args, config, tell_manager)
        m_logger.info.assert_called_once_with(
            f"{run_type} on {host_name}: "
            f"time.step not found; continuing to watch..."
        )

    def test_time_step_found(
        self,
        m_confirm,
        m_nml_read,
        m_pid_exists,
        m_find_run_pid,
        m_logger,
        run_type,
        host_name,
        config,
        tmpdir,
    ):
        tmp_run_dir = tmpdir.ensure_dir("tmp_run_dir")
        time_step = tmp_run_dir.ensure("time.step")
        time_step.write("1081\n")
        m_nml_read.return_value = {
            "namrun": {
                "nn_it000": 1,
                "nn_itend": 2160,
                "nn_date0": 20_171_113,
                "nn_stocklist": "2160, 0, 0, 0, 0, 0, 0, 0, 0, 0",
            },
            "namdom": {"rn_rdt": 40},
        }
        m_pid_exists.side_effect = (True, False)
        parsed_args = SimpleNamespace(host_name=host_name, run_type=run_type)
        tell_manager = Mock(
            spec=NowcastWorker.tell_manager,
            return_value=Message(
                "manager",
                "ack",
                payload={
                    run_type: {
                        "run dir": tmp_run_dir,
                        "run exec cmd": "bash SalishSeaNEMO.sh",
                        "run date": "2017-11-13",
                    }
                },
            ),
        )
        watch_NEMO.POLL_INTERVAL = 0
        watch_NEMO.watch_NEMO(parsed_args, config, tell_manager)
        m_logger.info.assert_called_once_with(
            f"{run_type} on {host_name}: "
            f"timestep: 1081 = 2017-11-13 12:00:00 UTC, 50.0% complete"
        )

    def test_confirm_run_success(
        self,
        m_confirm,
        m_nml_read,
        m_pid_exists,
        m_find_run_pid,
        m_logger,
        run_type,
        host_name,
        config,
    ):
        m_nml_read.return_value = {
            "namrun": {"nn_it000": 1, "nn_itend": 2160, "nn_date0": 20_171_113},
            "namdom": {"rn_rdt": 40},
        }
        m_pid_exists.return_value = False
        parsed_args = SimpleNamespace(host_name=host_name, run_type=run_type)
        tell_manager = Mock(
            spec=NowcastWorker.tell_manager,
            return_value=Message(
                "manager",
                "ack",
                payload={
                    run_type: {
                        "run dir": "tmp_run_dir",
                        "run exec cmd": "bash SalishSeaNEMO.sh",
                        "run date": "2017-11-13",
                    }
                },
            ),
        )
        checklist = watch_NEMO.watch_NEMO(parsed_args, config, tell_manager)
        expected = {
            run_type: {"host": host_name, "run date": "2017-11-13", "completed": True}
        }
        m_confirm.assert_called_once_with(
            host_name,
            run_type,
            arrow.get("2017-11-13"),
            Path("tmp_run_dir"),
            2160,
            2160,
            config,
        )


@patch("nowcast.workers.watch_NEMO.logger", autospec=True)
@patch("nowcast.workers.watch_NEMO.subprocess.run", autospec=True)
class TestFindRunPid:
    """Unit tests for _find_run_pid() function."""

    def test_find_qsub_run_pid(self, m_run, m_logger):
        run_info = {"run exec cmd": "qsub SalishSeaNEMO.sh", "run id": "4446.master"}
        m_run.return_value = Mock(stdout="4343")
        watch_NEMO._find_run_pid(run_info)
        assert m_run.call_args_list == [
            call(
                ["pgrep", "4446.master"],
                stdout=subprocess.PIPE,
                check=True,
                universal_newlines=True,
            )
        ]

    def test_find_bash_run_pid(self, m_run, m_logger):
        run_info = {"run exec cmd": "bash SalishSeaNEMO.sh", "run id": None}
        m_run.return_value = Mock(stdout="4343")
        watch_NEMO._find_run_pid(run_info)
        assert m_run.call_args_list == [
            call(
                ["pgrep", "--newest", "--exact", "--full", "bash SalishSeaNEMO.sh"],
                stdout=subprocess.PIPE,
                check=True,
                universal_newlines=True,
            )
        ]


class TestPidExists:
    """Unit tests for _pid_exists() function."""

    def test_negative_pid(self):
        pid_exists = watch_NEMO._pid_exists(-1)
        assert not pid_exists

    def test_zero_pid(self):
        with pytest.raises(ValueError):
            watch_NEMO._pid_exists(0)

    @patch("nowcast.workers.watch_NEMO.os.kill", return_value=None, autospec=True)
    def test_pid_exists(self, m_kill):
        pid_exists = watch_NEMO._pid_exists(42)
        assert pid_exists

    @patch(
        "nowcast.workers.watch_NEMO.os.kill",
        side_effect=ProcessLookupError,
        autospec=True,
    )
    def test_no_such_pid(self, m_kill):
        pid_exists = watch_NEMO._pid_exists(42)
        assert not pid_exists

    @patch(
        "nowcast.workers.watch_NEMO.os.kill", side_effect=PermissionError, autospec=True
    )
    def test_pid_permission_error(self, m_kill):
        pid_exists = watch_NEMO._pid_exists(42)
        assert pid_exists

    @patch("nowcast.workers.watch_NEMO.os.kill", side_effect=OSError, autospec=True)
    def test_oserror(self, m_kill):
        with pytest.raises(OSError):
            watch_NEMO._pid_exists(42)


@patch("nowcast.workers.watch_NEMO.logger", autospec=True)
class TestConfirmRunSuccess:
    """Unit tests for _confirm_run_success() function."""

    @pytest.mark.parametrize(
        "run_type, itend, restart_timestep",
        [
            ("nowcast", 2160, 2160),
            ("nowcast-green", 2160, 2160),
            ("forecast", 3240, 2160),
            ("forecast2", 2700, 2160),
        ],
    )
    def test_run_succeeded(
        self, m_logger, run_type, itend, restart_timestep, config, tmpdir
    ):
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (True, False, True, True)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open().__enter__().read.return_value = f"{itend}\n"
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    run_type,
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    itend,
                    restart_timestep,
                    config,
                )
        assert run_succeeded

    @pytest.mark.parametrize(
        "run_type, itend, restart_timestep",
        [
            ("nowcast", 2160, 2160),
            ("nowcast-green", 2160, 2160),
            ("forecast", 3240, 2160),
            ("forecast2", 2700, 2160),
        ],
    )
    def test_no_results_dir(self, m_logger, run_type, itend, restart_timestep, config):
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (False, False, True, True)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open().__enter__().read.return_value = f"{itend}\n"
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    run_type,
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    itend,
                    restart_timestep,
                    config,
                )
        assert not run_succeeded

    @pytest.mark.parametrize(
        "run_type, itend, restart_timestep",
        [
            ("nowcast", 2160, 2160),
            ("nowcast-green", 2160, 2160),
            ("forecast", 3240, 2160),
            ("forecast2", 2700, 2160),
        ],
    )
    def test_output_abort_file_exists(
        self,
        m_logger,
        run_type,
        itend,
        restart_timestep,
        config,
    ):
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (True, True, True, True)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open().__enter__().read.return_value = f"{itend}\n"
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    "nowcast",
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    itend,
                    restart_timestep,
                    config,
                )
        assert not run_succeeded

    @pytest.mark.parametrize(
        "run_type, itend, restart_timestep",
        [
            ("nowcast", 2160, 2160),
            ("nowcast-green", 2160, 2160),
            ("forecast", 3240, 2160),
            ("forecast2", 2700, 2160),
        ],
    )
    def test_no_time_step_file(
        self, m_logger, run_type, itend, restart_timestep, config
    ):
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (True, False, True, True)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open.side_effect = FileNotFoundError
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    run_type,
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    itend,
                    restart_timestep,
                    config,
                )
        assert "time.step" in m_logger.critical.call_args_list[0][0][0]
        assert not run_succeeded

    @pytest.mark.parametrize(
        "run_type, itend, restart_timestep",
        [
            ("nowcast", 2160, 2160),
            ("nowcast-green", 2160, 2160),
            ("forecast", 3240, 2160),
            ("forecast2", 2700, 2160),
        ],
    )
    def test_wrong_final_time_step(
        self, m_logger, run_type, itend, restart_timestep, config
    ):
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (True, False, True, True)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open().__enter__().read.return_value = "43\n"
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    "nowcast",
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    itend,
                    restart_timestep,
                    config,
                )
        assert not run_succeeded

    @pytest.mark.parametrize(
        "run_type, itend, restart_timestep",
        [
            ("nowcast", 2160, 2160),
            ("nowcast-green", 2160, 2160),
            ("forecast", 3240, 2160),
            ("forecast2", 2700, 2160),
        ],
    )
    def test_no_physics_restart_file(
        self, m_logger, run_type, itend, restart_timestep, config
    ):
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (True, False, False, True)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open().__enter__().read.return_value = f"{itend}\n"
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    run_type,
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    itend,
                    restart_timestep,
                    config,
                )
        expected = f"SalishSea_{restart_timestep:08d}_restart.nc"
        assert expected in m_logger.critical.call_args[0][0]
        assert not run_succeeded

    def test_no_tracers_restart_file(self, m_logger, config):
        restart_timestep = 2160
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (True, False, True, False)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open().__enter__().read.return_value = "2160\n"
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    "nowcast-green",
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    2160,
                    restart_timestep,
                    config,
                )
        expected = f"SalishSea_{restart_timestep:08d}_restart_trc.nc"
        assert expected in m_logger.critical.call_args[0][0]
        assert not run_succeeded

    @pytest.mark.parametrize(
        "run_type, itend, restart_timestep",
        [
            ("nowcast", 2160, 2160),
            ("nowcast-green", 2160, 2160),
            ("forecast", 3240, 2160),
            ("forecast2", 2700, 2160),
        ],
    )
    def test_no_ocean_output_file(
        self, m_logger, run_type, itend, restart_timestep, config
    ):
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (True, False, True, True)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open.side_effect = FileNotFoundError
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    run_type,
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    itend,
                    restart_timestep,
                    config,
                )
        assert "ocean.output" in m_logger.critical.call_args_list[1][0][0]
        assert not run_succeeded

    @pytest.mark.parametrize(
        "run_type, itend, restart_timestep",
        [
            ("nowcast", 2160, 2160),
            ("nowcast-green", 2160, 2160),
            ("forecast", 3240, 2160),
            ("forecast2", 2700, 2160),
        ],
    )
    def test_error_in_ocean_output(
        self, m_logger, run_type, itend, restart_timestep, config
    ):
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (True, False, True, True)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open().__enter__().read.return_value = f"{itend}\n"
                m_open().__enter__().__iter__.return_value = ["foo E R R O R bar\n"]
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    run_type,
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    itend,
                    restart_timestep,
                    config,
                )
        assert not run_succeeded

    @pytest.mark.parametrize(
        "run_type, itend, restart_timestep",
        [
            ("nowcast", 2160, 2160),
            ("nowcast-green", 2160, 2160),
            ("forecast", 3240, 2160),
            ("forecast2", 2700, 2160),
        ],
    )
    def test_no_solver_stat_file(
        self, m_logger, run_type, itend, restart_timestep, config
    ):
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (True, False, True, True)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open.side_effect = FileNotFoundError
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    run_type,
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    itend,
                    restart_timestep,
                    config,
                )
        assert "solver.stat" in m_logger.critical.call_args_list[2][0][0]
        assert not run_succeeded

    @pytest.mark.parametrize(
        "run_type, itend, restart_timestep",
        [
            ("nowcast", 2160, 2160),
            ("nowcast-green", 2160, 2160),
            ("forecast", 3240, 2160),
            ("forecast2", 2700, 2160),
        ],
    )
    def test_nan_in_solver_stat(
        self, m_logger, run_type, itend, restart_timestep, config
    ):
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (True, False, True, True)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open().__enter__().read.return_value = f"{itend}\n"
                m_open().__enter__().__iter__.return_value = (
                    "foo bar\n",
                    "it : 43 ssh2: NaN Umax: 0.2450101238E+01\n",
                )
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    run_type,
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    itend,
                    restart_timestep,
                    config,
                )
        assert not run_succeeded

    def test_nan_in_tracer_stat(self, m_logger, config):
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (True, False, True, True)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open().__enter__().read.return_value = "2160\n"
                m_open().__enter__().__iter__.return_value = (
                    "foo bar\n",
                    "it : 43 ssh2: 0.8313118488E+05 Umax: 0.2450101238E+01\n"
                    "43  NaN\n",
                )
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    "nowcast-green",
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    2160,
                    2160,
                    config,
                )
        assert not run_succeeded

    def test_no_tracer_stat_file(self, m_logger, config):
        with patch("nowcast.workers.watch_NEMO.Path.exists") as m_exists:
            m_exists.side_effect = (True, False, True, True)
            with patch("nowcast.workers.watch_NEMO.Path.open") as m_open:
                m_open().__enter__().read.return_value = "2160\n"
                m_open.side_effect = FileNotFoundError
                run_succeeded = watch_NEMO._confirm_run_success(
                    "arbutus.cloud",
                    "nowcast-green",
                    arrow.get("2017-11-16"),
                    Path("tmp_run_dir"),
                    2160,
                    2160,
                    config,
                )
        assert "tracer.stat" in m_logger.critical.call_args_list[3][0][0]
        assert not run_succeeded
