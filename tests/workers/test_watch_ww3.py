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
import logging
from types import SimpleNamespace

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
    (
        ("nowcast", "arbutus.cloud-nowcast"),
        ("forecast", "arbutus.cloud-nowcast"),
        ("forecast2", "arbutus.cloud-nowcast"),
    ),
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, run_type, host_name, caplog):
        parsed_args = SimpleNamespace(host_name=host_name, run_type=run_type)
        caplog.set_level(logging.DEBUG)

        msg_type = watch_ww3.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"{run_type} WWATCH3 run on {host_name} completed"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize(
    "run_type, host_name",
    (
        ("nowcast", "arbutus.cloud-nowcast"),
        ("forecast", "arbutus.cloud-nowcast"),
        ("forecast2", "arbutus.cloud-nowcast"),
    ),
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, run_type, host_name, caplog):
        parsed_args = SimpleNamespace(host_name=host_name, run_type=run_type)
        caplog.set_level(logging.DEBUG)

        msg_type = watch_ww3.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"{run_type} WWATCH3 run on {host_name} failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {run_type}"


class TestFindRunPid:
    """Unit test for _find_run_pid() function."""

    def test_find_run_pid(self, caplog, monkeypatch):
        def mock_run(cmd, stdout, check, universal_newlines):
            return SimpleNamespace(stdout="4343")

        monkeypatch.setattr(watch_ww3.subprocess, "run", mock_run)

        run_info = {"run exec cmd": "bash SoGWW3.sh"}
        caplog.set_level(logging.DEBUG)

        pid = watch_ww3._find_run_pid(run_info)

        assert caplog.records[0].levelname == "DEBUG"
        expected = (
            'searching processes with `pgrep --newest --exact --full "bash SoGWW3.sh"`'
        )
        assert caplog.messages[0] == expected
        assert pid == 4343


class TestPidExists:
    """Unit tests for _pid_exists() function."""

    def test_negative_pid(self):
        pid_exists = watch_ww3._pid_exists(-1)
        assert not pid_exists

    def test_zero_pid(self):
        with pytest.raises(ValueError):
            watch_ww3._pid_exists(0)

    def test_pid_exists(self, monkeypatch):
        def mock_kill(pid, signal):
            return None

        monkeypatch.setattr(watch_ww3.os, "kill", mock_kill)

        pid_exists = watch_ww3._pid_exists(42)

        assert pid_exists

    def test_no_such_pid(self, monkeypatch):
        def mock_kill(pid, signal):
            raise ProcessLookupError

        monkeypatch.setattr(watch_ww3.os, "kill", mock_kill)

        pid_exists = watch_ww3._pid_exists(42)

        assert not pid_exists

    def test_pid_permission_error(self, monkeypatch):
        def mock_kill(pid, signal):
            raise PermissionError

        monkeypatch.setattr(watch_ww3.os, "kill", mock_kill)

        pid_exists = watch_ww3._pid_exists(42)

        assert pid_exists

    def test_oserror(self, monkeypatch):
        def mock_kill(pid, signal):
            raise OSError

        monkeypatch.setattr(watch_ww3.os, "kill", mock_kill)

        with pytest.raises(OSError):
            watch_ww3._pid_exists(42)
