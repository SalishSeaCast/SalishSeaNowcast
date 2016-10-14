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

"""Unit tests for Salish Sea NEMO nowcast make_forcing_links worker.
"""
from unittest.mock import (
    call,
    Mock,
    patch,
)

import arrow
import pytest


@pytest.fixture
def worker_module():
    from nowcast.workers import make_forcing_links
    return make_forcing_links


@patch.object(worker_module(), 'NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    def test_instantiate_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker.call_args
        assert args == ('make_forcing_links',)
        assert list(kwargs.keys()) == ['description']

    def test_add_host_name_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('host_name',)
        assert 'help' in kwargs

    def test_add_run_type_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ('run_type',)
        assert kwargs['choices'] == {
            'nowcast+', 'forecast2', 'ssh', 'nowcast-green'}
        assert 'help' in kwargs

    def test_add_shared_storage_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
        assert args == ('--shared-storage',)
        assert kwargs['action'] == 'store_true'
        assert 'help' in kwargs

    def test_add_run_date_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            worker_module.make_forcing_links,
            worker_module.success,
            worker_module.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """
    def test_success_log_info(self, worker_module):
        parsed_args = Mock(run_type='nowcast+')
        with patch.object(worker_module.logger, 'info') as m_logger:
            worker_module.success(parsed_args)
        assert m_logger.called

    def test_success_msg_type(self, worker_module):
        parsed_args = Mock(run_type='forecast2')
        with patch.object(worker_module.logger, 'info'):
            msg_type = worker_module.success(parsed_args)
        assert msg_type == 'success forecast2'


class TestFailure:
    """Unit tests for failure() function.
    """
    def test_failure_log_critical(self, worker_module):
        parsed_args = Mock(run_type='nowcast+')
        with patch.object(worker_module.logger, 'critical') as m_logger:
            worker_module.failure(parsed_args)
        assert m_logger.called

    def test_failure_msg_type(self, worker_module):
        parsed_args = Mock(run_type='ssh')
        with patch.object(worker_module.logger, 'critical'):
            msg_type = worker_module.failure(parsed_args)
        assert msg_type == 'failure ssh'


@patch.object(worker_module(), '_create_symlink')
@patch.object(worker_module(), '_clear_links')
class TestMakeRunoffLinks:
    """Unit tests for _make_runoff_links() function.
    """
    def test_clear_links(self, m_clear_links, m_create_symlink, worker_module):
        run_date = arrow.get('2016-03-11')
        m_sftp_client = Mock(name='sftp_client')
        host_run_config = {
            'forcing': {
                'rivers dir': '/results/forcing/rivers/',
                'rivers_month.nc': 'NEMO-forcing/rivers/rivers_month.nc',
            },
            'nowcast dir': 'nowcast-green/',
        }
        worker_module._make_runoff_links(
            m_sftp_client, host_run_config, run_date, 'salish-nowcast')
        m_clear_links.assert_called_once_with(
            m_sftp_client, host_run_config, 'rivers/')

    def test_rivers_month_link(
        self, m_clear_links, m_create_symlink, worker_module,
    ):
        run_date = arrow.get('2016-03-11')
        m_sftp_client = Mock(name='sftp_client')
        host_run_config = {
            'forcing': {
                'rivers dir': '/results/forcing/rivers/',
                'rivers_month.nc': 'NEMO-forcing/rivers/rivers_month.nc',
            },
            'nowcast dir': 'nowcast-green/',
        }
        worker_module._make_runoff_links(
            m_sftp_client, host_run_config, run_date, 'salish-nowcast')
        assert m_create_symlink.call_args_list[0] == call(
            m_sftp_client, 'salish-nowcast',
            'NEMO-forcing/rivers/rivers_month.nc',
            'nowcast-green/rivers/rivers_month.nc')

    def test_rivers_temp_link(
        self, m_clear_links, m_create_symlink, worker_module,
    ):
        run_date = arrow.get('2016-10-14')
        m_sftp_client = Mock(name='sftp_client')
        host_run_config = {
            'forcing': {
                'rivers dir': '/results/forcing/rivers/',
                'rivers_month.nc': 'NEMO-forcing/rivers/rivers_month.nc',
                'rivers_temp.nc': 'NEMO-forcing/rivers/river_ConsTemp_month.nc',
            },
            'nowcast dir': 'nowcast-green/',
        }
        worker_module._make_runoff_links(
            m_sftp_client, host_run_config, run_date, 'salish-nowcast')
        assert m_create_symlink.call_args_list[1] == call(
            m_sftp_client, 'salish-nowcast',
            'NEMO-forcing/rivers/river_ConsTemp_month.nc',
            'nowcast-green/rivers/river_ConsTemp_month.nc')

    def test_bio_climatology_link(
        self, m_clear_links, m_create_symlink, worker_module,
    ):
        run_date = arrow.get('2016-03-11')
        m_sftp_client = Mock(name='sftp_client')
        host_run_config = {
            'forcing': {
                'rivers dir': '/results/forcing/rivers/',
                'rivers_month.nc': 'NEMO-forcing/rivers/rivers_month.nc',
                'rivers_temp.nc': 'NEMO-forcing/rivers/river_ConsTemp_month.nc',
                'rivers bio dir': 'NEMO-forcing/rivers/bio_climatology/',
            },
            'nowcast dir': 'nowcast-green/',
        }
        worker_module._make_runoff_links(
            m_sftp_client, host_run_config, run_date, 'salish-nowcast')
        assert m_create_symlink.call_args_list[2] == call(
            m_sftp_client, 'salish-nowcast',
            'NEMO-forcing/rivers/bio_climatology/',
            'nowcast-green/rivers/bio_climatology')

    def test_runoff_files_links(
        self, m_clear_links, m_create_symlink, worker_module,
    ):
        run_date = arrow.get('2016-03-11')
        m_sftp_client = Mock(name='sftp_client')
        host_run_config = {
            'forcing': {
                'rivers dir': '/results/forcing/rivers/',
                'rivers_month.nc': 'NEMO-forcing/rivers/rivers_month.nc',
            },
            'nowcast dir': 'nowcast-green/',
        }
        worker_module._make_runoff_links(
            m_sftp_client, host_run_config, run_date, 'salish-nowcast')
        start = run_date.replace(days=-1)
        end = run_date.replace(days=+2)
        for date in arrow.Arrow.range('day', start, end):
            expected = call(
                m_sftp_client, 'salish-nowcast',
                '/results/forcing/rivers/RFraserCElse_{:y%Ym%md%d}.nc'
                .format(start.date()),
                'nowcast-green/rivers/RFraserCElse_{:y%Ym%md%d}.nc'
                .format(date.date()))
            assert expected in m_create_symlink.call_args_list
            expected = call(
                m_sftp_client, 'salish-nowcast',
                '/results/forcing/rivers/RLonFraCElse_{:y%Ym%md%d}.nc'
                .format(start.date()),
                'nowcast-green/rivers/RLonFraCElse_{:y%Ym%md%d}.nc'
                .format(date.date()))
            assert expected in m_create_symlink.call_args_list
