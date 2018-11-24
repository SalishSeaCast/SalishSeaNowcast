#  Copyright 2013-2018 The Salish Sea MEOPAR contributors
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
"""Unit tests for Salish Sea NEMO nowcast make_turbidity_file worker.
"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import pytest

from nowcast.workers import make_turbidity_file


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    return base_config


@patch("nowcast.workers.make_turbidity_file.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_turbidity_file.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_turbidity_file",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_turbidity_file.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_turbidity_file.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_turbidity_file.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_turbidity_file.make_turbidity_file,
            make_turbidity_file.success,
            make_turbidity_file.failure,
        )


@patch("nowcast.workers.make_turbidity_file.logger")
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-07-08"))
        make_turbidity_file.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-07-08"))
        msg_type = make_turbidity_file.success(parsed_args)
        assert msg_type == "success"


@patch("nowcast.workers.make_turbidity_file.logger")
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_error(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-07-08"))
        make_turbidity_file.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-07-08"))
        msg_type = make_turbidity_file.failure(parsed_args)
        assert msg_type == f"failure"
