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
"""Unit tests for SalishSeaCast system download_wwatch3_results worker.
"""
from unittest.mock import (
    Mock,
    patch,
)

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import download_wwatch3_results


@patch(
    'nowcast.workers.download_wwatch3_results.NowcastWorker',
    spec=nemo_nowcast.NowcastWorker
)
class TestMain:
    """Unit tests for main() function.
            def test_init_cli(self, m_worker):
        download_results.main()
        m_worker().init_cli.assert_called_once_with()
    """

    def test_instantiate_worker(self, m_worker):
        download_wwatch3_results.main()
        args, kwargs = m_worker.call_args
        assert args == ('download_wwatch3_results',)
        assert list(kwargs.keys()) == ['description']

    def test_init_cli(self, m_worker):
        download_wwatch3_results.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        download_wwatch3_results.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker):
        download_wwatch3_results.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('run_type',)
        expected = {'forecast', 'forecast2'}
        assert kwargs['choices'] == expected
        assert 'help' in kwargs

    def test_add_run_date_arg(self, m_worker):
        download_wwatch3_results.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        download_wwatch3_results.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            download_wwatch3_results.download_wwatch3_results,
            download_wwatch3_results.success,
            download_wwatch3_results.failure,
        )


@pytest.mark.parametrize(
    'run_type, host_name', [
        ('forecast', 'west.cloud-nowcast'),
        ('forecast2', 'west.cloud-nowcast'),
    ]
)
@patch('nowcast.workers.download_wwatch3_results.logger', autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, run_type, host_name):
        parsed_args = Mock(host_name=host_name, run_type=run_type)
        download_wwatch3_results.success(parsed_args)
        assert m_logger.info.called
        assert m_logger.info.call_args[1]['extra']['run_type'] == run_type
        assert m_logger.info.call_args[1]['extra']['host_name'] == host_name

    def test_success_msg_type(self, m_logger, run_type, host_name):
        parsed_args = Mock(host_name=host_name, run_type=run_type)
        msg_typ = download_wwatch3_results.success(parsed_args)
        assert msg_typ == 'success {}'.format(run_type)


@pytest.mark.parametrize(
    'run_type, host_name', [
        ('forecast', 'west.cloud-nowcast'),
        ('forecast2', 'west.cloud-nowcast'),
    ]
)
@patch('nowcast.workers.download_wwatch3_results.logger', autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_info(self, m_logger, run_type, host_name):
        parsed_args = Mock(host_name=host_name, run_type=run_type)
        download_wwatch3_results.failure(parsed_args)
        assert m_logger.critical.called
        assert m_logger.critical.call_args[1]['extra']['run_type'] == run_type
        assert m_logger.critical.call_args[1]['extra']['host_name'
                                                       ] == host_name

    def test_failure_msg_type(self, m_logger, run_type, host_name):
        parsed_args = Mock(host_name=host_name, run_type=run_type)
        msg_typ = download_wwatch3_results.failure(parsed_args)
        assert msg_typ == 'failure {}'.format(run_type)
