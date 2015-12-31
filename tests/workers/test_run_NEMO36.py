# Copyright 2013-2015 The Salish Sea MEOPAR contributors
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

"""Unit tests for Salish Sea NEMO nowcast run_NEMO36 worker.
"""
from unittest.mock import (
    patch,
    Mock,
)

import arrow
import pytest


@pytest.fixture
def worker_module():
    from nowcast.workers import run_NEMO36
    return run_NEMO36


@pytest.fixture
def config():
    return {
        'run_types': {
            'nowcast': 'SalishSea',
            'forecast': 'SalishSea',
            'forecast2': 'SalishSea',
            'nowcast-green': 'SOG',
        },
        'run': {
            'salish': {
                'results': {
                    'nowcast': '/results/SalishSea/nowcast/',
                    'nowcast-green': '/results/SalishSea/nowcast-green/',
                    'forecast': '/results/SalishSea/forecast/',
                    'forecast2': '/results/SalishSea/forecast2/',
                }}}
    }


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

    def test_add_host_name_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[1]
        assert args == ('run_type',)
        assert kwargs['choices'] == {
            'nowcast', 'nowcast-green', 'forecast', 'forecast2'}
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
            worker_module.run_NEMO,
            worker_module.success,
            worker_module.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """
    def test_success_log_info(self, worker_module):
        parsed_args = Mock(
            run_type='forecast', run_date=arrow.get('2015-12-28'))
        with patch.object(worker_module.logger, 'info') as m_logger:
            worker_module.success(parsed_args)
        assert m_logger.called

    def test_success_msg_type(self, worker_module):
        parsed_args = Mock(
            run_type='forecast2', run_date=arrow.get('2015-12-28'))
        msg_type = worker_module.success(parsed_args)
        assert msg_type == 'success forecast2'


class TestFailure:
    """Unit tests for failure() function.
    """
    def test_failure_log_error(self, worker_module):
        parsed_args = Mock(
            run_type='forecast', run_date=arrow.get('2015-12-28'))
        with patch.object(worker_module.logger, 'critical') as m_logger:
            worker_module.failure(parsed_args)
        assert m_logger.called

    def test_failure_msg_type(self, worker_module):
        parsed_args = Mock(
            run_type='forecast2', run_date=arrow.get('2015-12-28'))
        msg_type = worker_module.failure(parsed_args)
        assert msg_type == 'failure forecast2'


class TestCalcNewNamelistLines:
    """Unit tests for _calc_new_namelist_lines() function.
    """
    @pytest.mark.parametrize(
        'run_type, prev_itend, dt_per_day, it000, itend, date0, restart', [
            ('nowcast', 2160, 2160, 2161, 4320, '20151230', 2160),
            ('nowcast-green', 2160, 2160, 2161, 4320, '20151230', 2160),
            ('forecast', 2160, 2160, 2161, 4860, '20151230', 2160),
            ('forecast2', 2700, 2160, 2161, 4860, '20151230', 2160),
        ])
    def test_calc_new_namelist_lines(
        self, run_type, prev_itend, dt_per_day, it000, itend, date0, restart,
        worker_module,
    ):
        lines = [
            '  nn_it000 = 1\n',
            '  nn_itend = 2160\n',
            '  nn_date0 = 20151229\n',
        ]
        new_lines, restart_timestep = worker_module._calc_new_namelist_lines(
            run_type, 1, prev_itend, 20151229, dt_per_day, lines)
        assert new_lines == [
            '  nn_it000 = {}\n'.format(it000),
            '  nn_itend = {}\n'.format(itend),
            '  nn_date0 = {}\n'.format(date0),
        ]
        assert restart_timestep == restart


class TestGetNamelistValue:
    """Unit tests for _get_namelist_value() function.
    """
    def test_get_value(self, worker_module):
        lines = ['  nn_it000 = 8641  ! first time step\n']
        line_index, value = worker_module._get_namelist_value(
            'nn_it000', lines)
        assert line_index == 0
        assert value == str(8641)

    def test_get_last_occurrence(self, worker_module):
        lines = [
            '  nn_it000 = 8641  ! first time step\n',
            '  nn_it000 = 8642  ! last time step\n',
        ]
        line_index, value = worker_module._get_namelist_value(
            'nn_it000', lines)
        assert line_index == 1
        assert value == str(8642)

    def test_handle_empty_line(self, worker_module):
        lines = [
            '\n',
            '  nn_it000 = 8641  ! first time step\n',
            ]
        line_index, value = worker_module._get_namelist_value(
            'nn_it000', lines)
        assert line_index == 1
        assert value == str(8641)


class TestRunDescription:
    """Unit tests for _run_description() function.
    """
    @pytest.mark.parametrize('run_type, expected', [
        ('nowcast', 'SalishSea'),
        ('nowcast-green', 'SOG'),
        ('forecast', 'SalishSea'),
        ('forecast2', 'SalishSea'),
    ])
    def test_config_name(
        self, run_type, expected, worker_module, config,
    ):
        run_date = arrow.get('2015-12-30')
        dmy = run_date.format('DDMMMYY')
        run_id = '{dmy}{run_type}'.format(dmy=dmy, run_type=run_type)
        run_desc = worker_module._run_description(
            run_date, run_type, run_id, 2160, 'salish', config)
        assert run_desc['config_name'] == expected
