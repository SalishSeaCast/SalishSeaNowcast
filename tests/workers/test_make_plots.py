# Copyright 2013-2016 The Salish Sea MEOPAR contributors
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

"""Unit tests for Salish Sea NEMO nowcast make_plots worker.
"""
from unittest.mock import (
    Mock,
    patch,
)

import arrow
import pytest


@pytest.fixture
def worker_module():
    from nowcast.workers import make_plots
    return make_plots


@patch.object(worker_module(), 'NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    @patch.object(worker_module(), 'worker_name')
    def test_instantiate_worker(self, m_name, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker.call_args
        assert args == (m_name,)
        assert list(kwargs.keys()) == ['description']

    def test_add_run_type_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[0]
        assert args == ('run_type',)
        assert kwargs['choices'] == set(('nowcast', 'forecast', 'forecast2'))
        assert 'help' in kwargs

    def test_add_plot_type_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[1]
        assert args == ('plot_type',)
        assert kwargs['choices'] == set(('publish', 'research', 'comparison'))
        assert 'help' in kwargs

    def test_add_run_date_arg(self, m_worker, worker_module, lib_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[2]
        assert args == ('--run-date',)
        assert kwargs['type'] == lib_module.arrow_date
        assert kwargs['default'] == arrow.now('Canada/Pacific').floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            worker_module.make_plots,
            worker_module.success,
            worker_module.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """
    def test_success_log_info(self, worker_module):
        parsed_args = Mock(run_type='nowcast', plot_type='research')
        with patch.object(worker_module.logger, 'info') as m_logger:
            worker_module.success(parsed_args)
        assert m_logger.called

    def test_success_msg_type(self, worker_module):
        parsed_args = Mock(run_type='forecast2', plot_type='publish')
        msg_type = worker_module.success(parsed_args)
        assert msg_type == 'success forecast2 publish'


class TestFailure:
    """Unit tests for failure() function.
    """
    def test_failure_log_error(self, worker_module):
        parsed_args = Mock(run_type='nowcast', plot_type='comparison')
        with patch.object(worker_module.logger, 'critical') as m_logger:
            worker_module.failure(parsed_args)
        assert m_logger.called

    def test_failure_msg_type(self, worker_module):
        parsed_args = Mock(run_type='forecast', plot_type='publish')
        msg_type = worker_module.failure(parsed_args)
        assert msg_type == 'failure forecast publish'
