# Copyright 2013-2018 The Salish Sea MEOPAR Contributors
# and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for SalishSeaCast make_surface_current_tiles worker.
"""
from types import SimpleNamespace
from unittest.mock import patch

import nemo_nowcast
import pytest

from nowcast.workers import make_surface_current_tiles


@patch(
    'nowcast.workers.make_surface_current_tiles.NowcastWorker',
    spec=nemo_nowcast.NowcastWorker
)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        make_surface_current_tiles.main()
        args, kwargs = m_worker.call_args
        assert args == ('make_surface_current_tiles',)
        assert list(kwargs.keys()) == ['description']

    def test_init_cli(self, m_worker):
        make_surface_current_tiles.main()
        m_worker().init_cli.assert_called_once_with()

    def test_run_worker(self, m_worker):
        make_surface_current_tiles.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_surface_current_tiles.make_surface_current_tiles,
            make_surface_current_tiles.success,
            make_surface_current_tiles.failure,
        )


@patch('nowcast.workers.make_surface_current_tiles.logger', autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger):
        parsed_args = SimpleNamespace()
        make_surface_current_tiles.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self, m_logger):
        parsed_args = SimpleNamespace()
        msg_type = make_surface_current_tiles.success(parsed_args)
        assert msg_type == f'success'


@patch('nowcast.workers.make_surface_current_tiles.logger', autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_critical(self, m_logger):
        parsed_args = SimpleNamespace()
        make_surface_current_tiles.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self, m_logger):
        parsed_args = SimpleNamespace()
        msg_type = make_surface_current_tiles.failure(parsed_args)
        assert msg_type == f'failure'


@patch('nowcast.workers.make_surface_current_tiles.logger', autospec=True)
class TestMakeSurfaceCurrentTiles:
    """Unit tests for make_surface_current_tiles() function.
    """

    def test_checklist(self, m_logger):
        parsed_args = SimpleNamespace()
        config = {}
        checklist = make_surface_current_tiles.make_surface_current_tiles(
            parsed_args, config
        )
        expected = {}
        assert checklist == expected
