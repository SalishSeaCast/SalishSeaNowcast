# Copyright 2013-2018 The Salish Sea MEOPAR contributors
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
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import pytest

from nowcast.workers import make_plots


@patch('nowcast.workers.make_plots.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        make_plots.main()
        args, kwargs = m_worker.call_args
        assert args == ('make_plots',)
        assert list(kwargs.keys()) == ['description']

    def test_init_cli(self, m_worker):
        make_plots.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_model_arg(self, m_worker):
        make_plots.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('model',)
        assert kwargs['choices'] == {'nemo', 'fvcom'}
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker):
        make_plots.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('run_type',)
        assert kwargs['choices'] == {
            'nowcast', 'nowcast-green', 'forecast', 'forecast2'
        }
        assert 'help' in kwargs

    def test_add_plot_type_arg(self, m_worker):
        make_plots.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
        assert args == ('plot_type',)
        assert kwargs['choices'] == {'publish', 'research', 'comparison'}
        assert 'help' in kwargs

    def test_add_run_date_arg(self, m_worker):
        make_plots.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
        assert 'help' in kwargs

    def test_add_test_figure_arg(self, m_worker):
        make_plots.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[3]
        assert args == ('--test-figure',)
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        make_plots.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_plots.make_plots,
            make_plots.success,
            make_plots.failure,
        )


@pytest.mark.parametrize(
    'model, run_type, plot_type', [
        ('nemo', 'nowcast', 'publish'),
        ('nemo', 'nowcast', 'research'),
        ('nemo', 'nowcast', 'comparison'),
        ('nemo', 'forecast', 'publish'),
        ('nemo', 'forecast2', 'publish'),
        ('fvcom', 'nowcast', 'publish'),
    ]
)
@patch('nowcast.workers.make_plots.logger')
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, model, run_type, plot_type):
        parsed_args = SimpleNamespace(
            model=model,
            run_type=run_type,
            plot_type=plot_type,
            run_date=arrow.get('2017-01-02')
        )
        make_plots.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self, m_logger, model, run_type, plot_type):
        parsed_args = SimpleNamespace(
            model=model,
            run_type=run_type,
            plot_type=plot_type,
            run_date=arrow.get('2017-01-02')
        )
        msg_type = make_plots.success(parsed_args)
        assert msg_type == f'success {model} {run_type} {plot_type}'


@pytest.mark.parametrize(
    'model, run_type, plot_type', [
        ('nemo', 'nowcast', 'publish'),
        ('nemo', 'nowcast', 'research'),
        ('nemo', 'nowcast', 'comparison'),
        ('nemo', 'forecast', 'publish'),
        ('nemo', 'forecast2', 'publish'),
        ('fvcom', 'nowcast', 'publish'),
    ]
)
@patch('nowcast.workers.make_plots.logger')
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_error(self, m_logger, model, run_type, plot_type):
        parsed_args = SimpleNamespace(
            model=model,
            run_type=run_type,
            plot_type=plot_type,
            run_date=arrow.get('2017-01-02')
        )
        make_plots.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self, m_logger, model, run_type, plot_type):
        parsed_args = SimpleNamespace(
            model=model,
            run_type=run_type,
            plot_type=plot_type,
            run_date=arrow.get('2017-01-02')
        )
        msg_type = make_plots.failure(parsed_args)
        assert msg_type == f'failure {model} {run_type} {plot_type}'
