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
"""Unit tests for SalishSeaCast launch_remote_worker worker.
"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from nowcast.workers import launch_remote_worker


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    return base_config


@patch("nowcast.workers.launch_remote_worker.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        launch_remote_worker.main()
        args, kwargs = m_worker.call_args
        assert args == ("launch_remote_worker",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        launch_remote_worker.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        launch_remote_worker.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_remote_worker_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        launch_remote_worker.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("remote_worker",)
        assert "help" in kwargs

    def test_add_worker_args_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        launch_remote_worker.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
        assert args == ("worker_args",)
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        launch_remote_worker.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            launch_remote_worker.launch_remote_worker,
            launch_remote_worker.success,
            launch_remote_worker.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "launch_remote_worker" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"][
            "launch_remote_worker"
        ]
        assert msg_registry["checklist key"] == "remote worker launch"

    @pytest.mark.parametrize("msg", ("success", "failure", "crash"))
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "launch_remote_worker"
        ]
        assert msg in msg_registry


@patch("nowcast.workers.launch_remote_worker.logger", autospec=True)
class TestSuccess:
    """Unit test for success() function.
    """

    def test_success(self, m_logger):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", remote_worker="foo", worker_args=[]
        )
        msg_type = launch_remote_worker.success(parsed_args)
        m_logger.info.assert_called_once_with(
            "remote worker launched on west.cloud: foo"
        )
        assert msg_type == "success"


@patch("nowcast.workers.launch_remote_worker.logger", autospec=True)
class TestFailure:
    """Unit test for failure() function.
    """

    def test_failure(self, m_logger):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", remote_worker="foo", worker_args=""
        )
        msg_type = launch_remote_worker.failure(parsed_args)
        m_logger.critical.assert_called_once_with(
            "remote worker launch on west.cloud failed: foo"
        )
        assert msg_type == "failure"


@patch("nowcast.workers.launch_remote_worker.logger", autospec=True)
@patch("nowcast.workers.launch_remote_worker.NextWorker", spec=True)
class TestLaunchRemoteWorker:
    """Unit test for launch_remote_worker() function.
    """

    @pytest.mark.parametrize(
        "remote_worker, exp_remote_wkr",
        (
            ("foo", "nowcast.workers.foo"),
            ("nemo_nowcast.workers.foo", "nemo_nowcast.workers.foo"),
        ),
    )
    def test_checklist(self, m_next_wkr, m_logger, remote_worker, exp_remote_wkr):
        parsed_args = SimpleNamespace(
            host_name="west.cloud",
            remote_worker=remote_worker,
            worker_args="nowcast --run-date 2018-11-23",
        )
        checklist = launch_remote_worker.launch_remote_worker(parsed_args, config)
        expected = {
            "host name": "west.cloud",
            "remote worker": exp_remote_wkr,
            "worker args": ["nowcast", "--run-date", "2018-11-23"],
        }
        assert checklist == expected

    def test_launch_remote_worker(self, m_next_wkr, m_logger, config):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", remote_worker="foo", worker_args=""
        )
        launch_remote_worker.launch_remote_worker(parsed_args, config)
        m_next_wkr().launch.assert_called_once_with(config, m_logger.name)
