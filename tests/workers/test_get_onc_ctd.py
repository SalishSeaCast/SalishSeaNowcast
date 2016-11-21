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

"""Unit tests for Salish Sea NEMO nowcast get_onc_ctd worker.
"""
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import pytest

from nowcast.workers import get_onc_ctd


@patch('nowcast.workers.get_onc_ctd.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    def test_instantiate_worker(self, m_worker):
        get_onc_ctd.main()
        args, kwargs = m_worker.call_args
        assert args == ('get_onc_ctd',)
        assert 'description' in kwargs

    def test_add_onc_station_arg(self, m_worker):
        get_onc_ctd.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('onc_station',)
        assert kwargs['choices'] == {'SCVIP', 'SEVIP'}
        assert 'help' in kwargs

    def test_add_data_date_arg(self, m_worker):
        get_onc_ctd.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--data-date',)
        assert kwargs['default'] == arrow.utcnow().floor('day').replace(days=-1)
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        get_onc_ctd.main()
        args, kwargs = m_worker().run.call_args
        expected = (
            get_onc_ctd.get_onc_ctd,
            get_onc_ctd.success,
            get_onc_ctd.failure)
        assert args == expected


class TestSuccess:
    """Unit tests for success() function.
    """
    @pytest.mark.parametrize('onc_station', [
        'SCVIP',
        'SEVIP',
    ])
    def test_success_log_info(self, onc_station):
        parsed_args = SimpleNamespace(
            onc_station=onc_station, data_date=arrow.get('2016-09-09'))
        with patch('nowcast.workers.get_onc_ctd.logger') as m_logger:
            get_onc_ctd.success(parsed_args)
        assert m_logger.info.called
        assert m_logger.info.call_args[1]['extra']['onc_station'] == onc_station
        assert m_logger.info.call_args[1]['extra']['data_date'] == '2016-09-09'

    @pytest.mark.parametrize('onc_station', [
        'SCVIP',
        'SEVIP',
    ])
    def test_success_msg_type(self, onc_station):
        parsed_args = SimpleNamespace(
            onc_station=onc_station, data_date=arrow.get('2016-09-09'))
        with patch('nowcast.workers.get_onc_ctd.logger') as m_logger:
            msg_type = get_onc_ctd.success(parsed_args)
        assert msg_type == 'success {}'.format(onc_station)


class TestFailure:
    """Unit tests for failure() function.
    """
    @pytest.mark.parametrize('onc_station', [
        'SCVIP',
        'SEVIP',
    ])
    def test_failure_log_critical(self, onc_station):
        parsed_args = SimpleNamespace(
            onc_station=onc_station, data_date=arrow.get('2016-09-09'))
        with patch('nowcast.workers.get_onc_ctd.logger') as m_logger:
            get_onc_ctd.failure(parsed_args)
        assert m_logger.critical.called
        extra_value = m_logger.critical.call_args[1]['extra']['onc_station']
        assert extra_value == onc_station
        extra_value = m_logger.critical.call_args[1]['extra']['data_date']
        assert extra_value == '2016-09-09'

    @pytest.mark.parametrize('onc_station', [
        'SCVIP',
        'SEVIP',
    ])
    def test_failure_msg_type(self, onc_station):
        parsed_args = SimpleNamespace(
            onc_station=onc_station, data_date=arrow.get('2016-09-09'))
        with patch('nowcast.workers.get_onc_ctd.logger') as m_logger:
            msg_type = get_onc_ctd.failure(parsed_args)
        assert msg_type == 'failure'
