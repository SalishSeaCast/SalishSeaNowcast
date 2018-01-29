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
"""Unit tests for Salish Sea NEMO nowcast get_onc_ferry worker.
"""
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import pytest

from nowcast.workers import get_onc_ferry


@patch('nowcast.workers.get_onc_ferry.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        get_onc_ferry.main()
        args, kwargs = m_worker.call_args
        assert args == ('get_onc_ferry',)
        assert 'description' in kwargs

    def test_init_cli(self, m_worker):
        get_onc_ferry.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_onc_station_arg(self, m_worker):
        get_onc_ferry.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('ferry_platform',)
        assert kwargs['choices'] == {'TWDP'}
        assert 'help' in kwargs

    def test_add_data_date_arg(self, m_worker):
        get_onc_ferry.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--data-date',)
        assert kwargs['default'] == arrow.now().floor('day').replace(days=-1)
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        get_onc_ferry.main()
        args, kwargs = m_worker().run.call_args
        expected = (
            get_onc_ferry.get_onc_ferry, get_onc_ferry.success,
            get_onc_ferry.failure
        )
        assert args == expected


@pytest.mark.parametrize('ferry_platform', [
    'TWDP',
])
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, ferry_platform):
        parsed_args = SimpleNamespace(
            ferry_platform=ferry_platform, data_date=arrow.get('2016-09-09')
        )
        with patch('nowcast.workers.get_onc_ferry.logger') as m_logger:
            get_onc_ferry.success(parsed_args)
        assert m_logger.info.called
        extra_value = m_logger.info.call_args[1]['extra']['ferry_platform']
        assert extra_value == ferry_platform
        assert m_logger.info.call_args[1]['extra']['data_date'] == '2016-09-09'

    def test_success_msg_type(self, ferry_platform):
        parsed_args = SimpleNamespace(
            ferry_platform=ferry_platform, data_date=arrow.get('2016-09-09')
        )
        with patch('nowcast.workers.get_onc_ferry.logger') as m_logger:
            msg_type = get_onc_ferry.success(parsed_args)
        assert msg_type == 'success {}'.format(ferry_platform)


@pytest.mark.parametrize('ferry_platform', [
    'TWDP',
])
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_critical(self, ferry_platform):
        parsed_args = SimpleNamespace(
            ferry_platform=ferry_platform, data_date=arrow.get('2016-09-09')
        )
        with patch('nowcast.workers.get_onc_ferry.logger') as m_logger:
            get_onc_ferry.failure(parsed_args)
        assert m_logger.critical.called
        extra_value = m_logger.critical.call_args[1]['extra']['ferry_platform']
        assert extra_value == ferry_platform
        extra_value = m_logger.critical.call_args[1]['extra']['data_date']
        assert extra_value == '2016-09-09'

    def test_failure_msg_type(self, ferry_platform):
        parsed_args = SimpleNamespace(
            ferry_platform=ferry_platform, data_date=arrow.get('2016-09-09')
        )
        with patch('nowcast.workers.get_onc_ferry.logger') as m_logger:
            msg_type = get_onc_ferry.failure(parsed_args)
        assert msg_type == 'failure'


@pytest.mark.parametrize('ferry_platform', [
    'TWDP',
])
class TestGetONCFerry:
    """Unit tests for get_onc_ferry() function.
    """
    pass


@pytest.mark.parametrize('ferry_platform', [
    'TWDP',
])
class TestGetNavData:
    """Unit tests for _get_nav_data() function.
    """
    pass


@pytest.mark.parametrize('ferry_platform', [
    'TWDP',
])
class TestCalcLocationArrays:
    """Unit tests for _calc_location_arrays() function.
    """
    pass


@pytest.mark.parametrize('ferry_platform', [
    'TWDP',
])
class TestOnCrossing:
    """Unit tests for _on_crossing() function.
    """
    pass


@pytest.mark.parametrize('ferry_platform', [
    'TWDP',
])
class TestCalcCrossingNumbers:
    """Unit tests for _calc_crossing_numbers() function.
    """
    pass


@pytest.mark.parametrize('ferry_platform', [
    'TWDP',
])
class TestGetWaterData:
    """Unit tests for _get_water_data() function.
    """
    pass


@pytest.mark.parametrize(
    'ferry_platform, device, sensors', [
        ('TWDP', 'TSG', 'temperature,conductivity,salinity'),
    ]
)
@patch('nowcast.workers.get_onc_ferry.logger', autospec=True)
class TestEmptyDeviceData:
    """Unit tests for _empty_device_data() function.
    """

    def test_empty_device_data(
        self, m_logger, ferry_platform, device, sensors
    ):
        dataset = get_onc_ferry._empty_device_data(
            ferry_platform, device, '2017-12-01', sensors
        )
        for sensor in sensors.split(','):
            assert sensor in dataset.data_vars
            assert dataset.data_vars[sensor].shape == (0,)
            assert dataset.data_vars[sensor].dtype == float
            assert 'sampleTime' in dataset.coords
            assert dataset.sampleTime.shape == (0,)
            assert dataset.sampleTime.dtype == 'datetime64[ns]'
            assert 'sampleTime' in dataset.dims


@pytest.mark.parametrize('ferry_platform', [
    'TWDP',
])
class TestQaqcFilter:
    """Unit tests for _qaqc_filter() function.
    """
    pass


@pytest.mark.parametrize('ferry_platform', [
    'TWDP',
])
class TestCreateDataset:
    """Unit tests for _create_dataset() function.
    """
    pass


@pytest.mark.parametrize('ferry_platform', [
    'TWDP',
])
class TestCreateDataarray:
    """Unit tests for _create_dataarray() function.
    """
    pass
