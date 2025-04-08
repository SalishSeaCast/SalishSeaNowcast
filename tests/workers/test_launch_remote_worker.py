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


"""Unit tests for SalishSeaCast launch_remote_worker worker."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from nowcast.workers import launch_remote_worker


@pytest.fixture
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    return base_config


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(launch_remote_worker, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_init_cli(self, mock_worker):
        worker = launch_remote_worker.main()
        assert worker.name == "launch_remote_worker"
        assert worker.description.startswith(
            "SalishSeaCast worker that launches a specified worker on a remote host."
        )

    def test_add_host_name_arg(self, mock_worker):
        worker = launch_remote_worker.main()
        assert worker.cli.parser._actions[3].dest == "host_name"
        assert worker.cli.parser._actions[3].help

    def test_add_remote_worker_arg(self, mock_worker):
        worker = launch_remote_worker.main()
        assert worker.cli.parser._actions[4].dest == "remote_worker"
        assert worker.cli.parser._actions[4].help

    def test_add_worker_args_arg(self, mock_worker):
        worker = launch_remote_worker.main()
        assert worker.cli.parser._actions[5].dest == "worker_args"
        assert worker.cli.parser._actions[5].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

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
    """Unit test for success() function."""

    def test_success(self, m_logger):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud", remote_worker="foo", worker_args=[]
        )
        msg_type = launch_remote_worker.success(parsed_args)
        m_logger.info.assert_called_once_with(
            "remote worker launched on arbutus.cloud: foo"
        )
        assert msg_type == "success"


@patch("nowcast.workers.launch_remote_worker.logger", autospec=True)
class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, m_logger):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud", remote_worker="foo", worker_args=""
        )
        msg_type = launch_remote_worker.failure(parsed_args)
        m_logger.critical.assert_called_once_with(
            "remote worker launch on arbutus.cloud failed: foo"
        )
        assert msg_type == "failure"


@patch("nowcast.workers.launch_remote_worker.logger", autospec=True)
@patch("nowcast.workers.launch_remote_worker.NextWorker", spec=True)
class TestLaunchRemoteWorker:
    """Unit test for launch_remote_worker() function."""

    @pytest.mark.parametrize(
        "remote_worker, exp_remote_wkr",
        (
            ("foo", "nowcast.workers.foo"),
            ("nemo_nowcast.workers.foo", "nemo_nowcast.workers.foo"),
        ),
    )
    def test_checklist(
        self, m_next_wkr, m_logger, remote_worker, exp_remote_wkr, config
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            remote_worker=remote_worker,
            worker_args="nowcast --run-date 2018-11-23",
        )
        checklist = launch_remote_worker.launch_remote_worker(parsed_args, config)
        expected = {
            "host name": "arbutus.cloud",
            "remote worker": exp_remote_wkr,
            "worker args": ["nowcast", "--run-date", "2018-11-23"],
        }
        assert checklist == expected

    def test_launch_remote_worker(self, m_next_wkr, m_logger, config):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud", remote_worker="foo", worker_args=""
        )
        launch_remote_worker.launch_remote_worker(parsed_args, config)
        m_next_wkr().launch.assert_called_once_with(config, m_logger.name)
