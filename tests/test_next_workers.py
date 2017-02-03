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

"""Unit tests for nowcast.next_workers module.
"""
from unittest.mock import patch

import pytest
from nemo_nowcast import (
    Message,
    NextWorker,
)

from nowcast import next_workers


@pytest.fixture
def config():
    """Nowcast system config dict data structure;
    a mock for :py:attr:`nemo_nowcast.config.Config._dict`.
    """
    return {
        'temperature salinity': {'matlab host': 'salish'},
        'observations': {
            'ctd data': {
                'stations': ['SCVIP', 'SEVIP', 'LSBBL', 'USDDL'],
            },
        },
        'run types': {
            'nowcast': {}, 'nowcast-green': {},
            'forecast': {}, 'forecast2': {}
        },
        'run': {
            'enabled hosts': {
                'cloud': {
                    'shared storage': False,
                    'run types': ['nowcast', 'forecast', 'forecast2'],
                },
                'salish': {
                    'shared storage': True,
                    'run types': ['nowast-green'],
                },
            },
            'remote hosts': ['cloud host'],
            'cloud host': 'west.cloud',
            'nowcast-green host': 'salish',
        }
    }


@pytest.fixture
def checklist():
    """Nowcast system state checklist dict data structure;
    a mock for :py:attr:`nemo_nowcast.manager.NowcastManager.checklist`.
    """
    return {}


class TestAfterDownloadWeather:
    """Unit tests for the after_download_weather function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure 00',
        'failure 06',
        'failure 12',
        'failure 18',
        'success 00',
        'success 18',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type), config, checklist)
        assert workers == []

    def test_success_06_launch_make_runoff_file(self, config, checklist):
        workers = next_workers.after_download_weather(
            Message('download_weather', 'success 06'), config, checklist)
        expected = NextWorker(
            'nowcast.workers.make_runoff_file', [], host='localhost')
        assert expected in workers

    @pytest.mark.parametrize('msg_type, args', [
        ('success 06', ['forecast2']),
        ('success 12', ['nowcast']),
    ])
    def test_success_launch_get_NeahBay_ssh(
        self, msg_type, args, config, checklist,
    ):
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type), config, checklist)
        expected = NextWorker(
            'nowcast.workers.get_NeahBay_ssh', args, host='localhost')
        assert expected in workers

    @pytest.mark.parametrize('msg_type, args', [
        ('success 06', ['forecast2']),
        ('success 12', ['nowcast+']),
    ])
    def test_success_launch_grib_to_netcdf(
        self, msg_type, args, config, checklist,
    ):
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type), config, checklist)
        expected = NextWorker(
            'nowcast.workers.grib_to_netcdf', args, host='localhost')
        assert expected in workers

    @pytest.mark.parametrize('ctd_stn', [
        'SCVIP',
        'SEVIP',
        'LSBBL',
        'USDDL',
    ])
    def test_success_06_launch_get_onc_ctd(self, ctd_stn, config, checklist):
        workers = next_workers.after_download_weather(
            Message('download_weather', 'success 06'), config, checklist)
        expected = NextWorker(
            'nowcast.workers.get_onc_ctd', args=[ctd_stn], host='localhost')
        assert expected in workers


class TestAfterMakeRunoffFile:
    """Unit tests for the after_make_runoff_file function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
        'success',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_runoff_file(
            Message('make_runoff_file', msg_type), config, checklist)
        assert workers == []


class TestAfterGetNeahBaySsh:
    """Unit tests for the after_get_NeahBay_ssh function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast',
        'failure forecast',
        'failure forecast2',
        'success nowcast',
        'success forecast2',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_get_NeahBay_ssh(
            Message('get_NeahBay_ssh', msg_type), config, checklist)
        assert workers == []

    def test_success_forecast_launch_upload_forcing_ssh(
        self, config, checklist,
    ):
        workers = next_workers.after_get_NeahBay_ssh(
            Message('get_NeahBay_ssh', 'success forecast'), config, checklist)
        expected = NextWorker(
            'nowcast.workers.upload_forcing',
            args=['cloud', 'ssh'], host='localhost')
        assert expected in workers


class TestAfterGribToNetcdf:
    """Unit tests for the after_grib_to_netcdf function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast+',
        'failure forecast2',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_grib_to_netcdf(
            Message('grib_to_netcdf', msg_type), config, checklist)
        assert workers == []

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
    ])
    def test_success_launch_upload_forcing(self, run_type, config, checklist):
        workers = next_workers.after_grib_to_netcdf(
            Message('grib_to_netcdf', 'success {}'.format(run_type)), config,
            checklist)
        expected = NextWorker(
            'nowcast.workers.upload_forcing',
            args=['west.cloud', run_type], host='localhost')
        assert expected in workers

    def test_success_nowcastp_launch_ping_erddap_download_weather(
        self, config, checklist,
    ):
        workers = next_workers.after_grib_to_netcdf(
            Message('grib_to_netcdf', 'success nowcast+'), config, checklist)
        expected = NextWorker(
            'nowcast.workers.ping_erddap',
            args=['download_weather'], host='localhost')
        assert expected in workers


class TestAfterGetONC_CTD:
    """Unit tests for the after_get_onc_ctd function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_get_onc_ctd(
            Message('get_onc_ctd', msg_type), config, checklist)
        assert workers == []

    @pytest.mark.parametrize('ctd_stn', [
        'SCVIP',
        'SEVIP',
        'LSBBL',
        'USDDL',
    ])
    def test_success_launch_ping_erddap(self, ctd_stn, config, checklist):
        workers = next_workers.after_get_onc_ctd(
            Message(
                'get_onc_ctd', 'success {}'.format(ctd_stn)), config, checklist)
        expected = NextWorker(
            'nowcast.workers.ping_erddap',
            args=['{}-CTD'.format(ctd_stn)], host='localhost')
        assert expected in workers


class TestAfterDownloadLiveOcean:
    """Unit tests for the after_download_live_ocean function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_download_live_ocean(
            Message('download_live_ocean', msg_type), config, checklist)
        assert workers == []

    def test_success_launch_make_live_ocean_files(self, config, checklist):
        workers = next_workers.after_download_live_ocean(
            Message('download_live_ocean', 'success'), config, checklist)
        expected = NextWorker(
            'nowcast.workers.make_live_ocean_files', args=[], host='salish')
        assert expected in workers


class TestAfterMakeLiveOceanFiles:
    """Unit tests for the after_make_live_ocean_files function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
        'success',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_live_ocean_files(
            Message('make_live_ocean_files', msg_type), config, checklist)
        assert workers == []


class TestAfterUploadForcing:
    """Unit tests for the after_upload_forcing function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast+',
        'failure forecast2',
        'failure ssh',
        'success forecast2',
        'success ssh',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_upload_forcing(
            Message('upload_forcing', msg_type), config, checklist)
        assert workers == []

    def test_msg_payload_missing_host_name(self, config, checklist):
        workers = next_workers.after_upload_forcing(
            Message('upload_forcing', 'crash'), config, checklist)
        assert workers == []

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'ssh',
        'forecast2',
    ])
    def test_success_launch_make_forcing_link(
        self, run_type, config, checklist,
    ):
        workers = next_workers.after_upload_forcing(
            Message(
                'upload_forcing', 'success {}'.format(run_type),
                {'west.cloud': '2016-10-11 ssh'}),
            config, checklist)
        expected = NextWorker(
            'nowcast.workers.make_forcing_links',
            args=['west.cloud', run_type], host='localhost')
        assert expected in workers


class TestAfterMakeForcingLinks:
    """Unit tests for the after_make_forcing_links function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast+',
        'failure nowcast-green',
        'failure forecast2',
        'failure ssh',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_forcing_links(
            Message('make_forcing_links', msg_type), config, checklist)
        assert workers == []

    @pytest.mark.parametrize('msg_type, args, host_name', [
        ('success nowcast+',
        ['west.cloud', 'nowcast', '--run-date', '2016-10-23'],
        'west.cloud'),
        ('success nowcast-green',
        ['west.cloud', 'nowcast-green', '--run-date', '2016-10-23'],
        'west.cloud'),
        ('success ssh',
        ['west.cloud', 'forecast', '--run-date', '2016-10-23'],
        'west.cloud'),
        ('success forecast2',
        ['west.cloud', 'forecast2', '--run-date', '2016-10-23'],
        'west.cloud'),
    ])
    def test_success_launch_run_NEMO(
        self, msg_type, args, host_name, config, checklist,
    ):
        p_checklist = patch.dict(
            checklist,
            {
                'forcing links': {
                    host_name: {'links': '', 'run date': '2016-10-23'}
                }
            })
        with p_checklist:
            workers = next_workers.after_make_forcing_links(
                Message(
                    'make_forcing_links', msg_type, payload={host_name: ''}),
                config, checklist)
        expected = NextWorker(
            'nowcast.workers.run_NEMO', args=args, host=host_name)
        assert expected in workers


class TestAfterRunNEMO:
    """Unit tests for the after_run_NEMO function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast',
        'failure nowcast-green',
        'failure forecast',
        'failure forecast2',
        'success nowcast',
        'success nowcast-green',
        'success forecast',
        'success forecast2',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_run_NEMO(
            Message('run_NEMO', msg_type), config, checklist)
        assert workers == []


class TestAfterWatchNEMO:
    """Unit tests for the after_watch_NEMO function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast',
        'failure nowcast-green',
        'failure forecast',
        'failure forecast2',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_watch_NEMO(
            Message('watch_NEMO', msg_type), config, checklist)
        assert workers == []

    def test_success_nowcast_launch_get_NeahBay_ssh_forecast(
        self, config, checklist,
    ):
        workers = next_workers.after_watch_NEMO(
            Message(
                'watch_NEMO', 'success nowcast', {
                    'nowcast': {
                        'host': 'cloud', 'run date': '2016-10-16',
                        'completed': True,
                    }
                }),
            config, checklist)
        expected = NextWorker(
            'nowcast.workers.get_NeahBay_ssh',
            args=['forecast'], host='localhost')
        assert workers[0] == expected

    def test_success_forecast_launch_make_forcing_links_nowcast_green(
        self, config, checklist,
    ):
        workers = next_workers.after_watch_NEMO(
            Message(
                'watch_NEMO', 'success forecast', {
                    'forecast': {
                        'host': 'cloud', 'run date': '2017-01-29',
                        'completed': True,
                    }
                }),
            config, checklist)
        expected = NextWorker(
            'nowcast.workers.make_forcing_links',
            args=['cloud', 'nowcast-green'], host='localhost')
        assert workers[0] == expected

    @pytest.mark.parametrize('msg', [
        Message(
            'watch_NEMO', 'success nowcast', {
                'nowcast': {
                    'host': 'cloud', 'run date': '2016-10-15',
                    'completed': True
                }
            }),
        Message(
            'watch_NEMO', 'success forecast', {
                'forecast': {
                    'host': 'cloud', 'run date': '2016-10-15',
                    'completed': True
                }
            }),
        Message(
            'watch_NEMO', 'success forecast2', {
                'forecast2': {
                    'host': 'cloud', 'run date': '2016-10-15',
                    'completed': True
                }
            }),
    ])
    def test_success_launch_download_results(self, msg, config, checklist):
        workers = next_workers.after_watch_NEMO(msg, config, checklist)
        run_type = msg.type.split()[1]
        expected = NextWorker(
            'nowcast.workers.download_results',
            args=[
                msg.payload[run_type]['host'], msg.type.split()[1],
                '--run-date', msg.payload[run_type]['run date']],
            host='localhost')
        assert expected in workers

    @pytest.mark.parametrize('msg', [
        Message(
            'watch_NEMO', 'success nowcast-green', {
                'nowcast-green': {
                    'host': 'salish', 'run date': '2016-10-15',
                    'completed': True
                }
            }),
    ])
    def test_success_nowcast_green_no_launch_download_results(
        self, msg, config, checklist,
    ):
        workers = next_workers.after_watch_NEMO(msg, config, checklist)
        assert workers == []


class TestAfterDownloadResults:
    """Unit tests for the after_download_results function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast',
        'failure forecast',
        'failure forecast2',
        'failure hindcast',
        'success hindcast',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_download_results(
            Message('download_results', msg_type), config, checklist)
        assert workers == []

    @pytest.mark.parametrize('run_type, plot_type', [
        ('nowcast', 'publish'),
        ('forecast', 'publish'),
        ('forecast2', 'publish'),
    ])
    def test_success_launch_make_plots_publish(
        self, run_type, plot_type, config, checklist,
    ):
        p_checklist = patch.dict(
            checklist, {'NEMO run': {run_type: {'run date': '2016-10-22'}}})
        with p_checklist:
            workers = next_workers.after_download_results(
                Message(
                    'download results', 'success {}'.format(run_type)),
                config, checklist)
        expected = NextWorker(
            'nowcast.workers.make_plots',
            args=[run_type, plot_type, '--run-date', '2016-10-22'],
            host='localhost')
        assert expected in workers

    @pytest.mark.parametrize('run_type, plot_type, run_date', [
        ('nowcast', 'research', '2016-10-29'),
        ('nowcast', 'comparison', '2016-10-28'),
    ])
    def test_success_nowcast_launch_make_plots_specials(
        self, run_type, plot_type, run_date, config, checklist,
    ):
        p_checklist = patch.dict(
            checklist, {'NEMO run': {run_type: {'run date': '2016-10-29'}}})
        with p_checklist:
            workers = next_workers.after_download_results(
                Message(
                    'download results', 'success {}'.format(run_type)),
                config, checklist)
        expected = NextWorker(
            'nowcast.workers.make_plots',
            args=[run_type, plot_type, '--run-date', run_date],
            host='localhost')
        assert expected in workers

    def test_success_nowcast_launch_ping_erddap_nowcast(
        self, config, checklist,
    ):
        p_checklist = patch.dict(
            checklist, {'NEMO run': {'nowcast': {'run date': '2016-12-10'}}})
        with p_checklist:
            workers = next_workers.after_download_results(
                Message(
                    'download_results', 'success nowcast'), config, checklist)
        expected = NextWorker(
            'nowcast.workers.ping_erddap', args=['nowcast'], host='localhost')
        assert expected in workers


class TestAfterSplitResults:
    """Unit tests for after_split_results function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure hindcast',
        'success hindcast',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_split_results(
            Message('split_results', msg_type), config, checklist)
        assert workers == []


class TestAfterPingERDDAP:
    """Unit tests for the after_ping_erddap function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast',
        'failure nowcast-green',
        'failure forecast',
        'failure forecast2',
        'failure download_weather',
        'failure SCVIP-CTD',
        'failure SEVIP-CTD',
        'success nowcast',
        'success nowcast-green',
        'success forecast',
        'success forecast2',
        'success download_weather',
        'success SCVIP-CTD',
        'success SEVIP-CTD',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_ping_erddap(
            Message('ping_erddap', msg_type), config, checklist)
        assert workers == []


class TestAfterMakePlots:
    """Unit tests for the after_make_plots function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast research',
        'failure nowcast comparison',
        'failure nowcast publish',
        'failure forecast publish',
        'failure forecast2 publish',
        'success nowcast research',
        'success nowcast comparison',
        'success nowcast publish',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_plots(
            Message('make_plots', msg_type), config, checklist)
        assert workers == []

    @pytest.mark.parametrize('msg_type, run_type', [
        ('success forecast publish', 'forecast'),
        ('success forecast2 publish', 'forecast2'),
    ])
    def test_success_forecast_launch_make_feeds(
        self, msg_type, run_type, config, checklist,
    ):
        p_checklist = patch.dict(
            checklist,
            {
                'NEMO run': {
                    run_type: {'run date': '2016-11-11'}
                }
            })
        with p_checklist:
            workers = next_workers.after_make_plots(
                Message('make_plots', msg_type), config, checklist)
        expected = NextWorker(
            'nowcast.workers.make_feeds',
            args=[run_type, '--run-date', '2016-11-11'], host='localhost')
        assert expected in workers


class TestAfterMakeFeeds:
    """Unit tests for the after_make_feeds function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure forecast',
        'failure forecast2',
        'success forecast',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_feeds(
            Message('make_feeds', msg_type), config, checklist)
        assert workers == []

    def test_success_forecast2_publish_launch_clear_checklist(
        self, config, checklist,
    ):
        workers = next_workers.after_make_feeds(
            Message(
                'make_feeds', 'success forecast2'), config, checklist)
        assert workers[-1] == NextWorker(
            'nemo_nowcast.workers.clear_checklist', args=[], host='localhost')


class TestAfterClearChecklist:
    """Unit tests for the after_clear_checklist function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_clear_checklist(
            Message('clear_checklist', msg_type), config, checklist)
        assert workers == []

    def test_success_launch_rotate_logs(self, config, checklist):
        workers = next_workers.after_clear_checklist(
            Message('rotate_logs', 'success'), config, checklist)
        assert workers[-1] == NextWorker(
            'nemo_nowcast.workers.rotate_logs', args=[], host='localhost')


class TestAfterRotateLogs:
    """Unit tests for the after_rotate_logs function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
        'success',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_rotate_logs(
            Message('rotate_logs', msg_type), config, checklist)
        assert workers == []
