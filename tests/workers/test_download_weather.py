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

"""Unit tests for Salish Sea NEMO nowcast download_weather worker.
"""
import arrow
from unittest.mock import (
    Mock,
    patch,
)
import pytest


@pytest.fixture
def worker_module():
    from nowcast.workers import download_weather
    return download_weather


@pytest.fixture
def parsed_args():
    return Mock(forecast='06', yesterday=False)


@pytest.fixture
def config():
    return {
        'file group': 'foo',
        'weather': {'GRIB_dir': '/tmp/'}
    }


@patch.object(worker_module(), 'NowcastWorker')
class TestMain():
    """Unit tests for main() function.
    """
    @patch.object(worker_module(), 'worker_name')
    def test_instantiate_worker(self, m_name, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker.call_args
        assert args == (m_name,)
        assert list(kwargs.keys()) == ['description']

    def test_add_forecast_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[0]
        assert args == ('forecast',)
        assert kwargs['choices'] == set(('00', '06', '12', '18'))
        assert 'help' in kwargs

    def test_add_yesterday_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[1]
        assert args == ('--yesterday',)
        assert kwargs['action'] == 'store_true'
        assert 'help' in kwargs

    def test_run_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            worker_module.get_grib,
            worker_module.success,
            worker_module.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """
    def test_success_log_info(self, worker_module):
        parsed_args = Mock(forecast='00')
        with patch.object(worker_module.logger, 'info') as m_logger:
            worker_module.success(parsed_args)
        assert m_logger.called

    def test_success_msg_type(self, worker_module):
        parsed_args = Mock(forecast='06')
        msg_type = worker_module.success(parsed_args)
        assert msg_type == 'success 06'


class TestFailure:
    """Unit tests for failure() function.
    """
    def test_failure_log_error(self, worker_module):
        parsed_args = Mock(forecast='12')
        with patch.object(worker_module.logger, 'error') as m_logger:
            worker_module.failure(parsed_args)
        assert m_logger.called

    def test_failure_msg_type(self, worker_module):
        parsed_args = Mock(forecast='18')
        msg_type = worker_module.failure(parsed_args)
        assert msg_type == 'failure 18'


@patch.object(worker_module(), 'logger')
@patch.object(worker_module(), '_calc_date', return_value='20150619')
@patch.object(worker_module().lib, 'mkdir')
@patch.object(worker_module().lib, 'fix_perms')
@patch.object(worker_module(), '_get_file')
class TestGetGrib():
    """Unit tests for get_grib() function.
    """
    def test_make_hour_dirs(
        self, m_get_file, m_fix_perms, m_mkdir, m_calc_date, m_logger,
        worker_module, parsed_args, config,
    ):
        worker_module.FORECAST_DURATION = 6
        worker_module.get_grib(parsed_args, config)
        for hr in range(1, 7):
            args, kwargs = m_mkdir.call_args_list[hr+1]
            assert args == ('/tmp/20150619/06/00{}'.format(hr), m_logger)
            assert kwargs == {'grp_name': 'foo', 'exist_ok': False}

    def test_get_grib_variable_file(
        self, m_get_file, m_fix_perms, m_mkdir, m_calc_date, m_logger,
        worker_module, parsed_args, config,
    ):
        worker_module.FORECAST_DURATION = 1
        worker_module.GRIB_VARIABLES = ('UGRD_TGL_10_',)
        worker_module.get_grib(parsed_args, config)
        args, kwargs = m_get_file.call_args
        assert args == ('UGRD_TGL_10_', '/tmp/', '20150619', '06', '001')
        assert kwargs == {}

    def test_fix_perms(
        self, m_get_file, m_fix_perms, m_mkdir, m_calc_date, m_logger,
        worker_module, parsed_args, config,
    ):
        worker_module.FORECAST_DURATION = 1
        worker_module.GRIB_VARIABLES = ('UGRD_TGL_10_',)
        m_get_file.return_value = 'filepath'
        with patch.object(worker_module.lib, 'fix_perms') as m_fix_perms:
            worker_module.get_grib(parsed_args, config)
        m_fix_perms.assert_called_once_with('filepath')

    def test_checklist(
        self, m_get_file, m_fix_perms, m_mkdir, m_calc_date, m_logger,
        worker_module, parsed_args, config,
    ):
        checklist = worker_module.get_grib(parsed_args, config)
        assert checklist == {'06 forecast': True}


@patch.object(
    worker_module().arrow, 'utcnow',
    return_value=arrow.get(2015, 6, 18, 19, 3, 42),
)
class TestCalcDate():
    """Unit tests for _calc_date() function.
    """
    def test_calc_date_06_forecast(self, m_utcnow, worker_module, parsed_args):
        date = worker_module._calc_date(parsed_args, '06')
        assert date == '20150618'

    def test_calc_date_yesterday(self, m_utcnow, worker_module, parsed_args):
        parsed_args.yesterday = True
        date = worker_module._calc_date(parsed_args, '06')
        assert date == '20150617'


@patch.object(worker_module(), 'logger')
@patch.object(worker_module().lib, 'mkdir')
class TestMkdirs():
    """Unit tests for _mkdirs() function.
    """
    def test_make_date_dir(self, m_mkdir, m_logger, worker_module):
        worker_module._mkdirs('/tmp', '20150618', '06', 'foo')
        args, kwargs = m_mkdir.call_args_list[0]
        assert args == ('/tmp/20150618', m_logger)
        assert kwargs == {'grp_name': 'foo'}

    def test_make_forecast_dir(self, m_mkdir, m_logger, worker_module):
        worker_module._mkdirs('/tmp', '20150618', '06', 'foo')
        args, kwargs = m_mkdir.call_args_list[1]
        assert args == ('/tmp/20150618/06', m_logger)
        assert kwargs == {'grp_name': 'foo', 'exist_ok': False}


@patch.object(worker_module(), 'logger')
@patch.object(worker_module().lib, 'get_web_data')
class TestGetFile():
    """Unit tests for _get_file() function.
    """
    def test_get_web_data(self, m_get_web_data, m_logger, worker_module):
        worker_module._get_file(
            'UGRD_TGL_10_', '/tmp/', '20150619', '06', '001')
        url = (
            'http://dd.weather.gc.ca/model_hrdps/west/grib2/06/001/'
            'CMC_hrdps_west_UGRD_TGL_10_ps2.5km_2015061906_P001-00.grib2'
        )
        filepath = (
            '/tmp/20150619/06/001/'
            'CMC_hrdps_west_UGRD_TGL_10_ps2.5km_2015061906_P001-00.grib2'
        )
        m_get_web_data.assert_called_once_with(
            url, m_logger, filepath, retry_time_limit=9000,
        )

    def test_empty_file_exception(
        self, m_get_web_data, m_logger, worker_module,
    ):
        m_get_web_data.return_value = {'Content-Length': 0}
        with pytest.raises(worker_module.lib.WorkerError):
            worker_module._get_file(
                'UGRD_TGL_10_', '/tmp/', '20150619', '06', '001')
