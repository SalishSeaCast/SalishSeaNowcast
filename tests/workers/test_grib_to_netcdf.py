# Copyright 2013-2017 The Salish Sea MEOPAR contributors
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
"""Unit tests for Salish Sea NEMO nowcast grib_to_netcdf worker.
"""
from unittest.mock import (
    Mock,
    patch,
)

import arrow
import pytest

from nowcast.workers import grib_to_netcdf


@patch('nowcast.workers.grib_to_netcdf.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        grib_to_netcdf.main()
        args, kwargs = m_worker.call_args
        assert args == ('grib_to_netcdf',)
        assert list(kwargs.keys()) == ['description']

    def test_init_cli(self, m_worker):
        grib_to_netcdf.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_type_arg(self, m_worker):
        grib_to_netcdf.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('run_type',)
        assert kwargs['choices'] == {'nowcast+', 'forecast2'}
        assert 'help' in kwargs

    def test_add_run_date_arg(self, m_worker):
        grib_to_netcdf.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        grib_to_netcdf.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            grib_to_netcdf.grib_to_netcdf,
            grib_to_netcdf.success,
            grib_to_netcdf.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
    ])
    def test_success_log_info(self, run_type):
        parsed_args = Mock(run_type=run_type)
        with patch('nowcast.workers.grib_to_netcdf.logger') as m_logger:
            grib_to_netcdf.success(parsed_args)
        assert m_logger.info.called
        assert m_logger.info.call_args[1]['extra']['run_type'] == run_type

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
    ])
    def test_success_msg_type(self, run_type):
        parsed_args = Mock(run_type=run_type)
        with patch('nowcast.workers.grib_to_netcdf.logger') as m_logger:
            msg_type = grib_to_netcdf.success(parsed_args)
        assert msg_type == 'success {}'.format(run_type)


class TestFailure:
    """Unit tests for failure() function.
    """

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
    ])
    def test_failure_log_critical(self, run_type):
        parsed_args = Mock(run_type=run_type)
        with patch('nowcast.workers.grib_to_netcdf.logger') as m_logger:
            grib_to_netcdf.failure(parsed_args)
        assert m_logger.critical.called
        assert m_logger.critical.call_args[1]['extra']['run_type'] == run_type

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
    ])
    def test_failure_msg_type(self, run_type):
        parsed_args = Mock(run_type=run_type)
        with patch('nowcast.workers.grib_to_netcdf.logger') as m_logger:
            msg_type = grib_to_netcdf.failure(parsed_args)
        assert msg_type == 'failure {}'.format(run_type)
