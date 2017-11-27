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
"""Unit tests for Salish Sea NEMO nowcast make_forcing_links worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import (
    call,
    Mock,
    patch,
)

import arrow
import pytest

from nowcast.workers import make_forcing_links


@patch('nowcast.workers.make_forcing_links.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        make_forcing_links.main()
        args, kwargs = m_worker.call_args
        assert args == ('make_forcing_links',)
        assert list(kwargs.keys()) == ['description']

    def test_add_host_name_arg(self, m_worker):
        make_forcing_links.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker):
        make_forcing_links.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('run_type',)
        assert kwargs['choices'] == {
            'nowcast+', 'forecast2', 'ssh', 'nowcast-green'
        }
        assert 'help' in kwargs

    def test_add_shared_storage_arg(self, m_worker):
        make_forcing_links.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
        assert args == ('--shared-storage',)
        assert kwargs['action'] == 'store_true'
        assert 'help' in kwargs

    def test_add_run_date_arg(self, m_worker):
        make_forcing_links.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        make_forcing_links.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_forcing_links.make_forcing_links,
            make_forcing_links.success,
            make_forcing_links.failure,
        )


@patch('nowcast.workers.make_forcing_links.logger')
class TestSuccess:
    """Unit tests for success() function.
    """

    @pytest.mark.parametrize(
        'run_type', [
            'nowcast+',
            'forecast2',
            'ssh',
            'nowcast-green',
        ]
    )
    def test_success_log_info(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            shared_storaage=False,
            run_date=arrow.get('2017-01-04')
        )
        make_forcing_links.success(parsed_args)
        assert m_logger.info.called

    @pytest.mark.parametrize(
        'run_type', [
            'nowcast+',
            'forecast2',
            'ssh',
            'nowcast-green',
        ]
    )
    def test_success_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            shared_storaage=False,
            run_date=arrow.get('2017-01-04')
        )
        msg_type = make_forcing_links.success(parsed_args)
        assert msg_type == 'success {run_type}'.format(run_type=run_type)


@patch('nowcast.workers.make_forcing_links.logger')
class TestFailure:
    """Unit tests for failure() function.
    """

    @pytest.mark.parametrize(
        'run_type', [
            'nowcast+',
            'forecast2',
            'ssh',
            'nowcast-green',
        ]
    )
    def test_failure_log_critical(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            shared_storaage=False,
            run_date=arrow.get('2017-01-04')
        )
        make_forcing_links.failure(parsed_args)
        assert m_logger.critical.called

    @pytest.mark.parametrize(
        'run_type', [
            'nowcast+',
            'forecast2',
            'ssh',
            'nowcast-green',
        ]
    )
    def test_failure_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name='west.cloud',
            run_type=run_type,
            shared_storaage=False,
            run_date=arrow.get('2017-01-04')
        )
        msg_type = make_forcing_links.failure(parsed_args)
        assert msg_type == 'failure {run_type}'.format(run_type=run_type)


@patch('nowcast.workers.make_forcing_links._create_symlink')
@patch('nowcast.workers.make_forcing_links._clear_links')
class TestMakeRunoffLinks:
    """Unit tests for _make_runoff_links() function.
    """
    config = {
        'rivers': {
            'file templates': {
                'short': 'RFraserCElse_{:y%Ym%md%d}.nc',
                'long': 'RLonFraCElse_{:y%Ym%md%d}.nc',
            },
            'turbidity': {
                'file template': 'riverTurbDaily2_{:y%Ym%md%d}.nc',
            }
        },
        'run': {
            'enabled hosts': {
                'salish-nowcast': {
                    'run prep dir': 'runs/',
                    'forcing': {
                        'rivers dir':
                            '/results/forcing/rivers/',
                        'rivers_month.nc':
                            'rivers/rivers_month.nc',
                        'Fraser turbidity dir':
                            '/results/forcing/rivers/river_turb/',
                    },
                },
            },
        }
    }

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
        'ssh',
    ])
    def test_clear_links(self, m_clear_links, m_create_symlink, run_type):
        run_date = arrow.get('2016-03-11')
        m_sftp_client = Mock(name='sftp_client')
        make_forcing_links._make_runoff_links(
            m_sftp_client, run_type, run_date, self.config, 'salish-nowcast'
        )
        run_prep_dir = Path(
            self.config['run']['enabled hosts']['salish-nowcast']
            ['run prep dir']
        )
        m_clear_links.assert_called_once_with(
            m_sftp_client,
            Path(
                self.config['run']['enabled hosts']['salish-nowcast']
                ['run prep dir']
            ), 'rivers/'
        )

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
        'ssh',
    ])
    def test_rivers_month_link(
        self, m_clear_links, m_create_symlink, run_type
    ):
        run_date = arrow.get('2016-03-11')
        m_sftp_client = Mock(name='sftp_client')
        make_forcing_links._make_runoff_links(
            m_sftp_client, run_type, run_date, self.config, 'salish-nowcast'
        )
        assert m_create_symlink.call_args_list[0] == call(
            m_sftp_client, 'salish-nowcast',
            Path('rivers/rivers_month.nc'),
            Path('runs/rivers/rivers_month.nc')
        )

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
        'ssh',
    ])
    def test_rivers_temp_link(self, m_clear_links, m_create_symlink, run_type):
        run_date = arrow.get('2016-10-14')
        m_sftp_client = Mock(name='sftp_client')
        p_config = patch.dict(
            self.config['run']['enabled hosts']['salish-nowcast']['forcing'], {
                'rivers dir': '/results/forcing/rivers/',
                'rivers_month.nc': 'rivers/rivers_month.nc',
                'rivers_temp.nc': 'rivers/river_ConsTemp_month.nc',
            }
        )
        with p_config:
            make_forcing_links._make_runoff_links(
                m_sftp_client, run_type, run_date, self.config,
                'salish-nowcast'
            )
        assert m_create_symlink.call_args_list[1] == call(
            m_sftp_client, 'salish-nowcast',
            Path('rivers/river_ConsTemp_month.nc'),
            Path('runs/rivers/river_ConsTemp_month.nc')
        )

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
        'ssh',
    ])
    def test_bio_climatology_link(
        self, m_clear_links, m_create_symlink, run_type
    ):
        run_date = arrow.get('2016-03-11')
        m_sftp_client = Mock(name='sftp_client')
        p_config = patch.dict(
            self.config['run']['enabled hosts']['salish-nowcast']['forcing'], {
                'rivers dir': '/results/forcing/rivers/',
                'rivers_month.nc': 'rivers/rivers_month.nc',
                'rivers_temp.nc': 'rivers/river_ConsTemp_month.nc',
                'rivers bio dir': 'rivers/bio/',
            }
        )
        with p_config:
            make_forcing_links._make_runoff_links(
                m_sftp_client, run_type, run_date, self.config,
                'salish-nowcast'
            )
        assert m_create_symlink.call_args_list[2] == call(
            m_sftp_client, 'salish-nowcast',
            Path('rivers/bio/'), Path('runs/rivers/bio')
        )

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
        'ssh',
    ])
    def test_runoff_files_links(
        self, m_clear_links, m_create_symlink, run_type
    ):
        run_date = arrow.get('2016-03-11')
        m_sftp_client = Mock(name='sftp_client')
        make_forcing_links._make_runoff_links(
            m_sftp_client, run_type, run_date, self.config, 'salish-nowcast'
        )
        start = run_date.replace(days=-1)
        end = run_date.replace(days=+2)
        for date in arrow.Arrow.range('day', start, end):
            expected = call(
                m_sftp_client, 'salish-nowcast',
                Path(
                    '/results/forcing/rivers/RFraserCElse_{:y%Ym%md%d}.nc'
                    .format(start.date())
                ),
                Path(
                    'runs/rivers/RFraserCElse_{:y%Ym%md%d}.nc'
                    .format(date.date())
                )
            )
            assert expected in m_create_symlink.call_args_list
            expected = call(
                m_sftp_client, 'salish-nowcast',
                Path(
                    '/results/forcing/rivers/RLonFraCElse_{:y%Ym%md%d}.nc'
                    .format(start.date())
                ),
                Path(
                    'runs/rivers/RLonFraCElse_{:y%Ym%md%d}.nc'
                    .format(date.date())
                )
            )
            assert expected in m_create_symlink.call_args_list

    def test_runoff_files_links_nowcast_green(
        self, m_clear_links, m_create_symlink
    ):
        run_date = arrow.get('2017-08-12')
        m_sftp_client = Mock(name='sftp_client')
        make_forcing_links._make_runoff_links(
            m_sftp_client, 'nowcast-green', run_date, self.config,
            'salish-nowcast'
        )
        start = run_date.replace(days=-1)
        end = run_date.replace(days=+2)
        for date in arrow.Arrow.range('day', start, end):
            expected = call(
                m_sftp_client, 'salish-nowcast',
                Path(
                    '/results/forcing/rivers/RFraserCElse_{:y%Ym%md%d}.nc'
                    .format(start.date())
                ),
                Path(
                    'runs/rivers/RFraserCElse_{:y%Ym%md%d}.nc'
                    .format(date.date())
                )
            )
            assert expected in m_create_symlink.call_args_list
            expected = call(
                m_sftp_client, 'salish-nowcast',
                Path(
                    '/results/forcing/rivers/RLonFraCElse_{:y%Ym%md%d}.nc'
                    .format(start.date())
                ),
                Path(
                    'runs/rivers/RLonFraCElse_{:y%Ym%md%d}.nc'
                    .format(date.date())
                )
            )
            assert expected in m_create_symlink.call_args_list
        expected = call(
            m_sftp_client, 'salish-nowcast',
            Path(
                '/results/forcing/rivers/river_turb/'
                'riverTurbDaily2_{:y%Ym%md%d}.nc'.format(run_date.date())
            ),
            Path(
                'runs/rivers/riverTurbDaily2_{:y%Ym%md%d}.nc'
                .format(run_date.date())
            )
        )
        assert expected in m_create_symlink.call_args_list
