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
"""Unit tests for SalishSeaCast watch_fvcom worker.
"""
import subprocess
from types import SimpleNamespace
from unittest.mock import call, Mock, patch

import pytest

from nowcast.workers import watch_fvcom


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    return base_config


@patch("nowcast.workers.watch_fvcom.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_fvcom.main()
        args, kwargs = m_worker.call_args
        assert args == ("watch_fvcom",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_fvcom.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_fvcom.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_model_config_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_fvcom.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("model_config",)
        assert kwargs["choices"] == {"r12", "x2"}
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_fvcom.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast"}
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        watch_fvcom.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            watch_fvcom.watch_fvcom,
            watch_fvcom.success,
            watch_fvcom.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "watch_fvcom" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["watch_fvcom"]
        assert msg_registry["checklist key"] == "FVCOM run"

    @pytest.mark.parametrize(
        "msg",
        (
            "need",
            "success x2 nowcast",
            "failure x2 nowcast",
            "success x2 forecast",
            "failure x2 forecast",
            "success r12 nowcast",
            "failure r12 nowcast",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["watch_fvcom"]
        assert msg in msg_registry


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.watch_fvcom.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud", model_config=model_config, run_type=run_type
        )
        msg_type = watch_fvcom.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {model_config} {run_type}"


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.watch_fvcom.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud", model_config=model_config, run_type=run_type
        )
        msg_type = watch_fvcom.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {model_config} {run_type}"


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.watch_fvcom.logger", autospec=True)
@patch("nowcast.workers.watch_fvcom._find_run_pid", return_value=43, autospec=True)
@patch("nowcast.workers.watch_fvcom._pid_exists", return_value=False, autospec=True)
class TestWatchFVCOM:
    """Uni tests for watch_fvcom() function.
    """

    def test_checklist(
        self, m_find_run_pid, m_pid_exists, m_logger, model_config, run_type, config
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud", model_config=model_config, run_type=run_type
        )
        tell_manager = Mock(name="tell_manager")
        tell_manager().payload = {
            f"{model_config} {run_type}": {
                "host": "arbutus.cloud",
                "run dir": "tmp_run_dir",
                "run exec cmd": "bash VHFR_FVCOM.sh",
                "model config": model_config,
                "run date": "2019-02-27",
            }
        }
        checklist = watch_fvcom.watch_fvcom(parsed_args, config, tell_manager)
        expected = {
            f"{model_config} {run_type}": {
                "host": "arbutus.cloud",
                "model config": model_config,
                "run date": "2019-02-27",
                "completed": True,
            }
        }
        assert checklist == expected


@patch("nowcast.workers.watch_fvcom.logger", autospec=True)
@patch("nowcast.workers.watch_fvcom.subprocess.run", autospec=True)
class TestFindRunPid:
    """Unit test for _find_run_pid() function.
    """

    def test_find_run_pid(self, m_run, m_logger):
        run_info = {"run exec cmd": "bash SoGWW3.sh"}
        m_run.return_value = Mock(stdout="4343")
        watch_fvcom._find_run_pid(run_info)
        assert m_run.call_args_list == [
            call(
                ["pgrep", "--newest", "--exact", "--full", "bash SoGWW3.sh"],
                stdout=subprocess.PIPE,
                check=True,
                universal_newlines=True,
            )
        ]


class TestPidExists:
    """Unit tests for _pid_exists() function.
    """

    def test_negative_pid(self):
        pid_exists = watch_fvcom._pid_exists(-1)
        assert not pid_exists

    def test_zero_pid(self):
        with pytest.raises(ValueError):
            watch_fvcom._pid_exists(0)

    @patch("nowcast.workers.watch_fvcom.os.kill", return_value=None, autospec=True)
    def test_pid_exists(self, m_kill):
        pid_exists = watch_fvcom._pid_exists(42)
        assert pid_exists

    @patch(
        "nowcast.workers.watch_fvcom.os.kill",
        side_effect=ProcessLookupError,
        autospec=True,
    )
    def test_no_such_pid(self, m_kill):
        pid_exists = watch_fvcom._pid_exists(42)
        assert not pid_exists

    @patch(
        "nowcast.workers.watch_fvcom.os.kill",
        side_effect=PermissionError,
        autospec=True,
    )
    def test_pid_permission_error(self, m_kill):
        pid_exists = watch_fvcom._pid_exists(42)
        assert pid_exists

    @patch("nowcast.workers.watch_fvcom.os.kill", side_effect=OSError, autospec=True)
    def test_oserror(self, m_kill):
        with pytest.raises(OSError):
            watch_fvcom._pid_exists(42)
