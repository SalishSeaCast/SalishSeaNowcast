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


"""Unit tests for Salish Sea nowcast watch_ww3 worker.
"""
import subprocess
from types import SimpleNamespace
from unittest.mock import call, patch, Mock

import pytest

from nowcast.workers import watch_ww3


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(watch_ww3, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = watch_ww3.main()
        assert worker.name == "watch_ww3"
        assert worker.description.startswith(
            "Salish Sea nowcast worker that monitors and reports on the progress of a WaveWatch3 run"
        )

    def test_add_host_name_arg(self, mock_worker):
        worker = watch_ww3.main()
        assert worker.cli.parser._actions[3].dest == "host_name"
        assert worker.cli.parser._actions[3].default == "arbutus.cloud-nowcast"
        assert worker.cli.parser._actions[3].help

    def test_add_run_type_arg(self, mock_worker):
        worker = watch_ww3.main()
        assert worker.cli.parser._actions[4].dest == "run_type"
        assert worker.cli.parser._actions[4].choices == {
            "nowcast",
            "forecast",
            "forecast2",
        }
        assert worker.cli.parser._actions[4].help


@pytest.mark.parametrize(
    "run_type, host_name",
    [("forecast2", "arbutus.cloud-nowcast"), ("forecast", "arbutus.cloud-nowcast")],
)
@patch("nowcast.workers.watch_ww3.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, m_logger, run_type, host_name):
        parsed_args = SimpleNamespace(host_name=host_name, run_type=run_type)
        msg_type = watch_ww3.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize(
    "run_type, host_name",
    [("forecast2", "arbutus.cloud-nowcast"), ("forecast", "arbutus.cloud-nowcast")],
)
@patch("nowcast.workers.watch_ww3.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, m_logger, run_type, host_name):
        parsed_args = SimpleNamespace(host_name=host_name, run_type=run_type)
        msg_type = watch_ww3.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {run_type}"


@patch("nowcast.workers.watch_ww3.logger", autospec=True)
@patch("nowcast.workers.watch_ww3.subprocess.run", autospec=True)
class TestFindRunPid:
    """Unit test for _find_run_pid() function."""

    def test_find_run_pid(self, m_run, m_logger):
        run_info = {"run exec cmd": "bash SoGWW3.sh"}
        m_run.return_value = Mock(stdout="4343")
        watch_ww3._find_run_pid(run_info)
        assert m_run.call_args_list == [
            call(
                ["pgrep", "--newest", "--exact", "--full", "bash SoGWW3.sh"],
                stdout=subprocess.PIPE,
                check=True,
                universal_newlines=True,
            )
        ]


class TestPidExists:
    """Unit tests for _pid_exists() function."""

    def test_negative_pid(self):
        pid_exists = watch_ww3._pid_exists(-1)
        assert not pid_exists

    def test_zero_pid(self):
        with pytest.raises(ValueError):
            watch_ww3._pid_exists(0)

    @patch("nowcast.workers.watch_ww3.os.kill", return_value=None, autospec=True)
    def test_pid_exists(self, m_kill):
        pid_exists = watch_ww3._pid_exists(42)
        assert pid_exists

    @patch(
        "nowcast.workers.watch_ww3.os.kill",
        side_effect=ProcessLookupError,
        autospec=True,
    )
    def test_no_such_pid(self, m_kill):
        pid_exists = watch_ww3._pid_exists(42)
        assert not pid_exists

    @patch(
        "nowcast.workers.watch_ww3.os.kill", side_effect=PermissionError, autospec=True
    )
    def test_pid_permission_error(self, m_kill):
        pid_exists = watch_ww3._pid_exists(42)
        assert pid_exists

    @patch("nowcast.workers.watch_ww3.os.kill", side_effect=OSError, autospec=True)
    def test_oserror(self, m_kill):
        with pytest.raises(OSError):
            watch_ww3._pid_exists(42)
