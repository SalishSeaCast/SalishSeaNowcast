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

"""Unit tests for Salish Sea NEMO nowcast upload_forcing worker.
"""
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import pytest

from nowcast.workers import upload_forcing


@patch('nowcast.workers.upload_forcing.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    def test_instantiate_worker(self, m_worker):
        upload_forcing.main()
        args, kwargs = m_worker.call_args
        assert args == ('upload_forcing',)
        assert list(kwargs.keys()) == ['description']

    def test_add_host_name_arg(self, m_worker):
        upload_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker):
        upload_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('run_type',)
        assert kwargs['choices'] == {'nowcast+', 'forecast2', 'ssh'}
        assert 'help' in kwargs

    def test_add_run_date_arg(self, m_worker):
        upload_forcing.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        upload_forcing.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            upload_forcing.upload_forcing,
            upload_forcing.success,
            upload_forcing.failure,
        )


@patch('nowcast.workers.upload_forcing.logger')
class TestSuccess:
    """Unit tests for success() function.
    """
    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
        'ssh',
    ])
    def test_success_log_info(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud', run_type=run_type,
            run_date=arrow.get('2017-01-02'))
        upload_forcing.success(parsed_args)
        assert m_logger.info.called

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
        'ssh',
    ])
    def test_success_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud', run_type=run_type,
            run_date=arrow.get('2017-01-02'))
        msg_type = upload_forcing.success(parsed_args)
        assert msg_type == 'success {run_type}'.format(run_type=run_type)


@patch('nowcast.workers.upload_forcing.logger')
class TestFailure:
    """Unit tests for failure() function.
    """
    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
        'ssh',
    ])
    def test_failure_log_critical(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud', run_type=run_type,
            run_date=arrow.get('2017-01-02'))
        upload_forcing.failure(parsed_args)
        assert m_logger.critical.called

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
        'ssh',
    ])
    def test_failure_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud', run_type=run_type,
            run_date=arrow.get('2017-01-02'))
        msg_type = upload_forcing.failure(parsed_args)
        assert msg_type == 'failure {run_type}'.format(run_type=run_type)
