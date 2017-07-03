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

"""Unit tests for Salish Sea NEMO nowcast download_weather worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import pytest

from nowcast.workers import download_weather


@pytest.fixture
def parsed_args():
    return SimpleNamespace(forecast='06', yesterday=False)


@pytest.fixture
def config():
    return {
        'file group': 'foo',
        'weather': {
            'download': {
                'url template':
                    'http://dd.beta.weather.gc.ca/model_hrdps/west/grib2/'
                    '{forecast}/{hour}/{filename}',
                'file template':
                    'CMC_hrdps_west_{variable}_ps2.5km_{date}{forecast}_'
                    'P{hour}-00.grib2',
                'grib variables': [
                    'UGRD_TGL_10',
                    'VGRD_TGL_10',
                    'DSWRF_SFC_0',
                    'DLWRF_SFC_0',
                    'TMP_TGL_2',
                    'SPFH_TGL_2',
                    'APCP_SFC_0',
                    'PRMSL_MSL_0',
                ],
                'forecast duration': 48,
                'GRIB dir': '/tmp/',
            }
        }
    }


@patch('nowcast.workers.download_weather.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    def test_instantiate_worker(self, m_worker):
        download_weather.main()
        args, kwargs = m_worker.call_args
        assert args == ('download_weather',)
        assert list(kwargs.keys()) == ['description']

    def test_add_forecast_arg(self, m_worker):
        download_weather.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('forecast',)
        assert kwargs['choices'] == {'00', '06', '12', '18'}
        assert 'help' in kwargs

    def test_add_yesterday_arg(self, m_worker):
        download_weather.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('--yesterday',)
        assert kwargs['action'] == 'store_true'
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        download_weather.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            download_weather.get_grib,
            download_weather.success,
            download_weather.failure,
        )


@patch('nowcast.workers.download_weather.logger')
class TestSuccess:
    """Unit tests for success() function.
    """
    @pytest.mark.parametrize('forecast', [
        '00',
        '06',
        '12',
        '18',
    ])
    def test_success_log_info(self, m_logger, forecast, parsed_args):
        parsed_args.forecast = forecast
        download_weather.success(parsed_args)
        assert m_logger.info.called

    @pytest.mark.parametrize('forecast', [
        '00',
        '06',
        '12',
        '18',
    ])
    def test_success_msg_type(self, m_logger, forecast, parsed_args):
        parsed_args.forecast = forecast
        msg_type = download_weather.success(parsed_args)
        assert msg_type == 'success {forecast}'.format(forecast=forecast)


@patch('nowcast.workers.download_weather.logger')
class TestFailure:
    """Unit tests for failure() function.
    """
    @pytest.mark.parametrize('forecast', [
        '00',
        '06',
        '12',
        '18',
    ])
    def test_failure_log_critical(self, m_logger, forecast, parsed_args):
        parsed_args.forecast = forecast
        download_weather.failure(parsed_args)
        assert m_logger.critical.called

    @pytest.mark.parametrize('forecast', [
        '00',
        '06',
        '12',
        '18',
    ])
    def test_failure_msg_type(self, m_logger, forecast, parsed_args):
        parsed_args.forecast = forecast
        msg_type = download_weather.failure(parsed_args)
        assert msg_type == 'failure {forecast}'.format(forecast=forecast)


@patch('nowcast.workers.download_weather.logger')
@patch('nowcast.workers.download_weather._calc_date', return_value='20150619')
@patch('nowcast.workers.download_weather.lib.mkdir')
@patch('nowcast.workers.download_weather.lib.fix_perms')
@patch('nowcast.workers.download_weather._get_file')
class TestGetGrib:
    """Unit tests for get_grib() function.
    """
    def test_make_hour_dirs(
        self, m_get_file, m_fix_perms, m_mkdir, m_calc_date, m_logger,
        parsed_args, config,
    ):
        p_config = patch.dict(
            config['weather']['download'], {'forecast duration': 6})
        with p_config:
            download_weather.get_grib(parsed_args, config)
        for hr in range(1, 7):
            args, kwargs = m_mkdir.call_args_list[hr+1]
            assert args == ('/tmp/20150619/06/00{}'.format(hr), m_logger)
            assert kwargs == {'grp_name': 'foo', 'exist_ok': False}

    @patch('nowcast.workers.download_weather.requests.Session')
    def test_get_grib_variable_file(
        self, m_session, m_get_file, m_fix_perms, m_mkdir, m_calc_date,
        m_logger, parsed_args, config,
    ):
        p_config = patch.dict(
            config['weather']['download'],
            {'grib variables': ['UGRD_TGL_10'], 'forecast duration': 1})
        with p_config:
            download_weather.get_grib(parsed_args, config)
        args, kwargs = m_get_file.call_args
        assert args == (
            config['weather']['download']['url template'],
            config['weather']['download']['file template'],
            'UGRD_TGL_10', '/tmp/', '20150619', '06', '001',
            m_session().__enter__())
        assert kwargs == {}

    def test_fix_perms(
        self, m_get_file, m_fix_perms, m_mkdir, m_calc_date, m_logger,
        parsed_args, config,
    ):
        p_config = patch.dict(
            config['weather']['download'],
            {'grib variables': ['UGRD_TGL_10'], 'forecast duration': 1})
        m_get_file.return_value = 'filepath'
        p_chmod = patch('nowcast.workers.download_weather.os.chmod')
        p_fileperms = patch('nowcast.workers.download_weather.FilePerms')
        with p_config, p_chmod as m_chmod, p_fileperms as m_fileperms:
            download_weather.get_grib(parsed_args, config)
        m_chmod.assert_called_once_with(
            'filepath', m_fileperms(user='rw', group='rw', other='r'))

    def test_checklist(
        self, m_get_file, m_fix_perms, m_mkdir, m_calc_date, m_logger,
        parsed_args, config,
    ):
        checklist = download_weather.get_grib(parsed_args, config)
        assert checklist == {'20150619 06 forecast': True}


@patch(
    'nowcast.workers.download_weather.arrow.utcnow',
    return_value=arrow.get(2015, 6, 18, 19, 3, 42),
)
class TestCalcDate:
    """Unit tests for _calc_date() function.
    """
    def test_calc_date_06_forecast(self, m_utcnow, parsed_args):
        date = download_weather._calc_date(parsed_args, '06')
        assert date == '20150618'

    def test_calc_date_yesterday(self, m_utcnow, parsed_args):
        parsed_args.yesterday = True
        date = download_weather._calc_date(parsed_args, '06')
        assert date == '20150617'


@patch('nowcast.workers.download_weather.logger')
@patch('nowcast.workers.download_weather.lib.mkdir')
class TestMkdirs:
    """Unit tests for _mkdirs() function.
    """
    def test_make_date_dir(self, m_mkdir, m_logger):
        download_weather._mkdirs('/tmp', '20150618', '06', 'foo')
        args, kwargs = m_mkdir.call_args_list[0]
        assert args == ('/tmp/20150618', m_logger)
        assert kwargs == {'grp_name': 'foo'}

    def test_make_forecast_dir(self, m_mkdir, m_logger):
        download_weather._mkdirs('/tmp', '20150618', '06', 'foo')
        args, kwargs = m_mkdir.call_args_list[1]
        assert args == ('/tmp/20150618/06', m_logger)
        assert kwargs == {'grp_name': 'foo', 'exist_ok': False}


@patch('nowcast.workers.download_weather.logger')
@patch('nowcast.workers.download_weather.get_web_data')
@patch('nowcast.workers.download_weather.os.stat')
class TestGetFile:
    """Unit tests for _get_file() function.
    """
    def test_get_web_data(self, m_stat, m_get_web_data, m_logger, config):
        m_stat().st_size = 123456
        download_weather._get_file(
            config['weather']['download']['url template'],
            config['weather']['download']['file template'],
            'UGRD_TGL_10', '/tmp/', '20150619', '06', '001', None
        )
        url = (
            'http://dd.beta.weather.gc.ca/model_hrdps/west/grib2/06/001/'
            'CMC_hrdps_west_UGRD_TGL_10_ps2.5km_2015061906_P001-00.grib2'
        )
        filepath = (
            '/tmp/20150619/06/001/'
            'CMC_hrdps_west_UGRD_TGL_10_ps2.5km_2015061906_P001-00.grib2'
        )
        m_get_web_data.assert_called_once_with(
            url, 'download_weather', Path(filepath), session=None,
            wait_exponential_max=9000,
        )

    def test_empty_file_exception(
        self, m_stat, m_get_web_data, m_logger, config
    ):
        m_stat().st_size = 0
        with pytest.raises(download_weather.WorkerError):
            download_weather._get_file(
                config['weather']['download']['url template'],
                config['weather']['download']['file template'],
                'UGRD_TGL_10', '/tmp/', '20150619', '06', '001', None)
