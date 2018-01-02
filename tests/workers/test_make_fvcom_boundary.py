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
"""Unit tests for Vancouver Harbour & Fraser River FVCOM make_fvcom_boundary
worker.
"""
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import pytest

from nowcast.workers import make_fvcom_boundary


@patch('nowcast.workers.make_fvcom_boundary.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker.call_args
        assert args == ('make_fvcom_boundary',)
        assert list(kwargs.keys()) == ['description']

    def test_init_cli(self, m_worker):
        make_fvcom_boundary.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('run_type',)
        assert kwargs['choices'] == {'nowcast', 'forecast'}
        assert 'help' in kwargs

    def test_add_run_date_option(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        make_fvcom_boundary.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_fvcom_boundary.make_fvcom_boundary,
            make_fvcom_boundary.success,
            make_fvcom_boundary.failure,
        )


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.make_fvcom_boundary.logger')
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        make_fvcom_boundary.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        msg_type = make_fvcom_boundary.success(parsed_args)
        assert msg_type == f'success {run_type}'


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.make_fvcom_boundary.logger')
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_error(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        make_fvcom_boundary.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        msg_type = make_fvcom_boundary.failure(parsed_args)
        assert msg_type == f'failure {run_type}'


@pytest.mark.parametrize('run_type', [
    'nowcast',
    'forecast',
])
@patch('nowcast.workers.make_fvcom_boundary.logger')
class TestMakeFVCOMBoundary:
    """Unit tests for make_fvcom_boundary() function.
    """

    def test_checklist(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            run_date=arrow.get('2017-11-29')
        )
        config = {}
        checklist = make_fvcom_boundary.make_fvcom_boundary(
            parsed_args, config
        )
        expected = {}
        assert checklist == expected
