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

"""Unit tests for Salish Sea WaveWatch3 forecast worker run_ww3 worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import (
    patch,
    Mock,
    call, create_autospec)

import arrow
import pytest

from nowcast.workers import run_ww3


@pytest.fixture
def config(scope='function'):
    return {'wave forecasts': {
        'run prep dir': 'wwatch3-runs',
        'results': {
            'forecast2': 'wwatch3-forecast2',
            'forecast': 'wwatch3-forecast',
        }
    }}


@patch('nowcast.workers.run_ww3.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    def test_instantiate_worker(self, m_worker):
        run_ww3.main()
        args, kwargs = m_worker.call_args
        assert args == ('run_ww3',)
        assert list(kwargs.keys()) == ['description']

    def test_add_host_name_arg(self, m_worker):
        run_ww3.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker):
        run_ww3.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('run_type',)
        assert kwargs['choices'] == {'forecast', 'forecast2'}
        assert 'help' in kwargs

    def test_add_run_date_option(self, m_worker):
        run_ww3.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        run_ww3.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            run_ww3.run_ww3,
            run_ww3.success,
            run_ww3.failure,
        )


@patch('nowcast.workers.run_ww3.logger')
class TestSuccess:
    """Unit tests for success() function.
    """
    @pytest.mark.parametrize('run_type', [
        'forecast2',
        'forecast',
    ])
    def test_success_log_info(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud', run_type=run_type,
            run_date=arrow.get('2017-03-25'))
        run_ww3.success(parsed_args)
        assert m_logger.info.called

    @pytest.mark.parametrize('run_type', [
        'forecast2',
        'forecast',
    ])
    def test_success_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud', run_type=run_type,
            run_date=arrow.get('2017-03-25'))
        msg_type = run_ww3.success(parsed_args)
        assert msg_type == 'success {run_type}'.format(run_type=run_type)


@patch('nowcast.workers.run_ww3.logger')
class TestFailure:
    """Unit tests for failure() function.
    """
    @pytest.mark.parametrize('run_type', [
        'forecast2',
        'forecast',
    ])
    def test_failure_log_error(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud', run_type=run_type,
            run_date=arrow.get('2017-03-25'))
        run_ww3.failure(parsed_args)
        assert m_logger.critical.called

    @pytest.mark.parametrize('run_type', [
        'forecast2',
        'forecast',
    ])
    def test_failure_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud', run_type=run_type,
            run_date=arrow.get('2017-03-25'))
        msg_type = run_ww3.failure(parsed_args)
        assert msg_type == 'failure {run_type}'.format(run_type=run_type)


@patch('nowcast.workers.run_ww3.logger')
class TestRunWW3:
    """Unit tests for run_ww3() function.
    """
    @pytest.mark.parametrize('run_type', [
        'forecast2',
        'forecast',
    ])
    @patch('nowcast.workers.run_ww3._build_tmp_run_dir')
    @patch('nowcast.workers.run_ww3._launch_run', return_value=4343)
    def test_checklist(
        self, m_launch_run, m_create_tmp_run_dir, m_logger, run_type, config
    ):
        parsed_args = SimpleNamespace(
            host_name='west.cloud', run_type=run_type,
            run_date=arrow.get('2017-03-25'))
        m_create_tmp_run_dir.return_value = Path(
            '/wwatch3-runs/a1e00274-11a3-11e7-ad44-80fa5b174bd6')

        checklist = run_ww3.run_ww3(parsed_args, config)
        expected = {
            run_type: {
                'host': 'west.cloud',
                'run date': '2017-03-25',
                'run dir': '/wwatch3-runs/a1e00274-11a3-11e7-ad44-80fa5b174bd6',
                'pid': 4343,
            }
        }
        assert checklist == expected


class TestBuildTmpRunDir:
    """Unit tests for _build_tmp_run_dir() function.
    """
    @pytest.mark.parametrize('run_type', [
        'forecast2',
        'forecast',
    ])
    @patch('nowcast.workers.run_ww3._write_ww3_input_files')
    @patch('nowcast.workers.run_ww3._create_symlinks')
    @patch('nowcast.workers.run_ww3._make_run_dir')
    def test_run_dir_path(
        self, m_make_run_dir, m_create_symlinks, m_write_ww3_input_files,
        run_type, config
    ):
        m_make_run_dir.return_value = Path(
            'wwatch3-runs/a1e00274-11a3-11e7-ad44-80fa5b174bd6')
        run_dir_path = run_ww3._build_tmp_run_dir(
            arrow.get('2017-03-24'), run_type, config)
        assert run_dir_path == Path(
            'wwatch3-runs/a1e00274-11a3-11e7-ad44-80fa5b174bd6')


class TestMakeRunDir:
    """Unit test for _make_run_dir() function.
    """
    @patch('nowcast.workers.run_ww3.Path.mkdir')
    @patch('nowcast.workers.run_ww3.uuid.uuid1')
    def test_make_run_dir(self, m_uuid1, m_mkdir):
        m_uuid1.return_value = 'a1e00274-11a3-11e7-ad44-80fa5b174bd6'
        run_dir_path = run_ww3._make_run_dir(Path('/wwatch3-runs'))
        m_mkdir.assert_called_once_with(mode=0o775)
        assert run_dir_path == Path(
            '/wwatch3-runs/a1e00274-11a3-11e7-ad44-80fa5b174bd6')


class TestWW3PrncWindContents:
    """Unit test for _ww3_prnc_wind_contents() function.
    """
    def test_ww3_prnc_wind_contents(self):
        contents = run_ww3._ww3_prnc_wind_contents(arrow.get('2017-03-25'))
        assert "'WND' 'LL' T T" in contents
        assert 'longitude latitude' in contents
        assert 'u_wind v_wind' in contents
        assert "'wind/SoG_wind_20170325.nc'" in contents


class TestWW3PrncCurrentContents:
    """Unit test for _ww3_prnc_current_contents() function.
    """
    def test_ww3_prnc_current_contents(self):
        contents = run_ww3._ww3_prnc_current_contents(arrow.get('2017-03-26'))
        assert "'CUR' 'LL' T T" in contents
        assert 'longitude latitude' in contents
        assert 'UCUR VCUR' in contents
        assert "'current/SoG_current_20170326.nc'" in contents


class TestWW3ShelContents:
    """Unit test for _ww3_shel_contents() function.
    """
    def test_ww3_shel_contents(self):
        contents = run_ww3._ww3_shel_contents(arrow.get('2017-03-26'))
        assert 'F F  Water levels w/ homogeneous field data' in contents
        assert 'T F  Currents w/ homogeneous field data' in contents
        assert 'T F  Winds w/ homogeneous field data' in contents
        assert 'F    Ice concentration' in contents
        assert 'F    Assimilation data : Mean parameters' in contents
        assert 'F    Assimilation data : 1-D spectra' in contents
        assert 'F    Assimilation data : 2-D spectra.' in contents
        assert '20170326 000000  Start time (YYYYMMDD HHmmss)' in contents
        assert '20170328 233000  End time (YYYYMMDD HHmmss)' in contents
        assert '2  dedicated process' in contents
        assert '20170326 000000 1800 20170328 233000' in contents
        assert 'N  by name' in contents
        assert 'HS LM WND CUR FP T02 DIR DP WCH WCC TWO FCO USS' in contents
        assert '20170326 000000 1800 20170328 233000' in contents
        assert "236.52 48.66 'C46134PatB'" in contents
        assert "236.27 49.34 'C46146HalB'" in contents
        assert "235.01 49.91 'C46131SenS'" in contents
        assert "0.0 0.0 'STOPSTRING'" in contents
        assert '20170326 000000 0 20170328 233000' in contents
        assert '20170328 233000 3600 20170328 233000' in contents
        assert '20170326 000000 0 20170328 233000' in contents
        assert '20170326 000000 0 20170328 233000' in contents
        assert "STP" in contents


class TestWW3OunfContents:
    """Unit test for _ww3_ounf_contents() function.
    """
    def test_ww3_ounf_contents(self):
        contents = run_ww3._ww3_ounf_contents(arrow.get('2017-03-26'))
        assert '20170326 000000 1800 144' in contents
        assert 'N  by name' in contents
        assert 'HS LM WND CUR FP T02 DIR DP WCH WCC TWO FCO USS' in contents
        assert '4' in contents
        assert '4' in contents
        assert '0 1 2' in contents
        assert 'T' in contents
        assert 'SoG_ww3_fields_' in contents
        assert '8' in contents
        assert '1 1000000 1 1000000' in contents


class TestWW3OunpContents:
    """Unit test for _ww3_ounp_contents() function.
    """
    def test_ww3_ounp_contents(self):
        contents = run_ww3._ww3_ounp_contents(arrow.get('2017-03-26'))
        assert '20170326 000000 1800 144' in contents
        assert '-1' in contents
        assert 'SoG_ww3_points_' in contents
        assert '8' in contents
        assert '4' in contents
        assert 'T 100' in contents
        assert '2' in contents
        assert '0' in contents
        assert '6' in contents
        assert 'T' in contents
