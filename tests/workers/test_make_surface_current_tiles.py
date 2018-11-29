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
"""Unit tests for SalishSeaCast make_surface_current_tiles worker.
"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_surface_current_tiles


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    return base_config


@patch("nowcast.workers.make_surface_current_tiles.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_surface_current_tiles.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_surface_current_tiles",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_surface_current_tiles.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_surface_current_tiles.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"forecast", "forecast2"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_surface_current_tiles.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_surface_current_tiles.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_surface_current_tiles.make_surface_current_tiles,
            make_surface_current_tiles.success,
            make_surface_current_tiles.failure,
        )


@pytest.mark.parametrize("run_type", ["forecast", "forecast2"])
@patch("nowcast.workers.make_surface_current_tiles.logger", autospec=True)
class TestSuccess:
    """Unit test for success() function.
    """

    def test_success(self, m_logger, run_type):
        parsed_args = SimpleNamespace(run_type=run_type)
        msg_type = make_surface_current_tiles.success(parsed_args)
        m_logger.info.assert_called_once_with(
            f"{run_type} surface current tile figures completed"
        )
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["forecast", "forecast2"])
@patch("nowcast.workers.make_surface_current_tiles.logger", autospec=True)
class TestFailure:
    """Unit test for failure() function.
    """

    def test_failure_log_critical(self, m_logger, run_type):
        parsed_args = SimpleNamespace(run_type=run_type)
        msg_type = make_surface_current_tiles.failure(parsed_args)
        m_logger.critical.assert_called_once_with(
            f"{run_type} surface current tile figures production failed"
        )
        assert msg_type == f"failure {run_type}"


@patch("nowcast.workers.make_surface_current_tiles.logger", autospec=True)
class TestMakeSurfaceCurrentTiles:
    """Unit tests for make_surface_current_tiles() function.
    """

    def test_checklist(self, m_logger, config):
        parsed_args = SimpleNamespace()
        checklist = make_surface_current_tiles.make_surface_current_tiles(
            parsed_args, config
        )
        expected = {}
        assert checklist == expected
