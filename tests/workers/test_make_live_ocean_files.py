# Copyright 2013-2017 The Salish Sea MEOPAR Contributors
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

"""Unit tests for Salish Sea NEMO nowcast make_live_ocean_files worker.
"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow

from nowcast.workers import make_live_ocean_files


@patch('nowcast.workers.make_live_ocean_files.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    def test_instantiate_worker(self, m_worker):
        make_live_ocean_files.main()
        args, kwargs = m_worker.call_args
        assert args == ('make_live_ocean_files',)
        assert 'description' in kwargs

    def test_add_run_date_arg(self, m_worker):
        make_live_ocean_files.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        make_live_ocean_files.main()
        args, kwargs = m_worker().run.call_args
        expected = (
            make_live_ocean_files.make_live_ocean_files,
            make_live_ocean_files.success,
            make_live_ocean_files.failure)
        assert args == expected


@patch('nowcast.workers.make_live_ocean_files.logger')
class TestSuccess:
    """Unit tests for success() function.
    """
    def test_success_log_info(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get('2017-01-12'))
        make_live_ocean_files.success(parsed_args)
        assert m_logger.info.called
        assert m_logger.info.call_args[1]['extra']['run_date'] == '2017-01-12'

    def test_success_msg_type(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get('2017-01-12'))
        msg_type = make_live_ocean_files.success(parsed_args)
        assert msg_type == 'success'


@patch('nowcast.workers.make_live_ocean_files.logger')
class TestFailure:
    """Unit tests for failure() function.
    """
    def test_failure_log_critical(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get('2017-01-12'))
        make_live_ocean_files.failure(parsed_args)
        assert m_logger.critical.called
        expected = '2017-01-12'
        assert m_logger.critical.call_args[1]['extra']['run_date'] == expected

    def test_failure_msg_type(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get('2017-01-12'))
        msg_type = make_live_ocean_files.failure(parsed_args)
        assert msg_type == 'failure'


@patch('nowcast.workers.make_live_ocean_files.create_LiveOcean_TS_BCs')
@patch('nowcast.workers.make_live_ocean_files.create_LiveOcean_bio_BCs_fromTS')
class TestMakeLiveOceanFiles:
    """Unit test for make_live_ocean_files() function.
    """
    def test_checklist(self, m_create_bio, m_create_ts):
        parsed_args = SimpleNamespace(run_date=arrow.get('2017-01-30'))
        config = {
            'temperature salinity': {
                'download': {'dest dir': 'forcing/LiveOcean/downloaded'},
                'bc dir': 'forcing/LiveOcean/boundary_conditions',
                'boundary info': 'SalishSea_west_TEOS10.nc',
            },
            'n and si': {
                'file template': 'LO_bio_{:y%Ym%md%d}.nc',
                'bc bio dir': 'forcing/LiveOcean/boundary_conditions/bio',
                'n fit':
                    'forcing/LiveOcean/boundary_conditions/bio/fits/'
                    'bioOBCfit_NTS.csv',
                'si fit':
                    'forcing/LiveOcean/boundary_conditions/bio/fits/'
                    'bioOBCfit_SiTS.csv',
                'n clim':
                    'forcing/LiveOcean/boundary_conditions/bio/fits/nmat.csv',
                'si clim':
                    'forcing/LiveOcean/boundary_conditions/bio/fits/simat.csv'
            }
        }
        m_create_ts.return_value = ['LO_TS_y2017m01d30.nc']
        m_create_bio.return_value = 'LO_bio_y2017m01d30.nc'
        checklist = make_live_ocean_files.make_live_ocean_files(
            parsed_args, config)
        expected = {
            'temperature & salinity': 'LO_TS_y2017m01d30.nc',
            'nutrients': 'LO_bio_y2017m01d30.nc',
        }
        assert checklist == expected
