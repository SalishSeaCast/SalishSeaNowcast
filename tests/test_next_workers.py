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
import pytest

from nemo_nowcast import (
    Message,
    NextWorker,
)

from nowcast import next_workers


@pytest.fixture
def config():
    return {
        'run types': {
            'nowcast': {}, 'nowcast-green': {},
            'forecast': {}, 'forecast2': {}},
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
    def test_no_next_worker_msg_types(self, msg_type, config):
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type), config)
        assert workers == []

    def test_success_06_launch_make_runoff_file(self, config):
        workers = next_workers.after_download_weather(
            Message('download_weather', 'success 06'), config)
        expected = NextWorker(
            'nowcast.workers.make_runoff_file', [], host='localhost')
        assert expected in workers

    @pytest.mark.parametrize('msg_type, args', [
        ('success 06', ['forecast2']),
        ('success 12', ['nowcast']),
    ])
    def test_success_launch_get_NeahBay_ssh(self, msg_type, args, config):
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type), config)
        expected = NextWorker(
            'nowcast.workers.get_NeahBay_ssh', args, host='localhost')
        assert expected in workers

    @pytest.mark.parametrize('msg_type, args', [
        ('success 06', ['forecast2']),
        ('success 12', ['nowcast+']),
    ])
    def test_success_launch_grib_to_netcdf(self, msg_type, args, config):
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type), config)
        expected = NextWorker(
            'nowcast.workers.grib_to_netcdf', args, host='localhost')
        assert expected in workers


class TestAfterMakeRunoffFile:
    """Unit tests for the after_make_runoff_file function.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
        'success',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config):
        workers = next_workers.after_make_runoff_file(
            Message('make_runoff_file', msg_type), config)
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
    def test_no_next_worker_msg_types(self, msg_type, config):
        workers = next_workers.after_get_NeahBay_ssh(
            Message('get_NeahBay_ssh', msg_type), config)
        assert workers == []

    def test_success_forecast_launch_upload_forcing_ssh(self, config):
        workers = next_workers.after_get_NeahBay_ssh(
            Message('get_NeahBay_ssh', 'success forecast'), config)
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
    def test_no_next_worker_msg_types(self, msg_type, config):
        workers = next_workers.after_grib_to_netcdf(
            Message('grib_to_netcdf', msg_type), config)
        assert workers == []

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
    ])
    def test_success_launch_upload_forcing(self, run_type, config):
        workers = next_workers.after_grib_to_netcdf(
            Message('grib_to_netcdf', 'success {}'.format(run_type)), config)
        expected = NextWorker(
            'nowcast.workers.upload_forcing',
            args=['west.cloud', run_type], host='localhost')
        assert expected in workers

    def test_success_nowcastp_launch_make_forcing_links_nowcast_green(
        self, config,
    ):
        workers = next_workers.after_grib_to_netcdf(
            Message('grib_to_netcdf', 'success nowcast+'), config)
        expected = NextWorker(
            'nowcast.workers.make_forcing_links',
            args=['salish', 'nowcast-green', '--shared-storage'],
            host='localhost')
        assert expected in workers


class TestAfterUploadForcing:
    """Unit tests for the after_upload_forcing function.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast+',
        'failure forecast2',
        'failure ssh',
        'success nowcast+',
        'success forecast2',
        'success ssh',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config):
        workers = next_workers.after_upload_forcing(
            Message('upload_forcing', msg_type), config)
        assert workers == []

    def test_msg_payload_missing_host_name(self, config):
        workers = next_workers.after_upload_forcing(
            Message('upload_forcing', 'crash'), config)
        assert workers == []

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'ssh',
        'forecast2',
    ])
    def test_success_launch_make_forcing_link(self, run_type, config):
        workers = next_workers.after_upload_forcing(
            Message(
                'upload_forcing', 'success {}'.format(run_type),
                {'west.cloud': '2016-10-11 ssh'}),
            config)
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
    def test_no_next_worker_msg_types(self, msg_type, config):
        workers = next_workers.after_make_forcing_links(
            Message('make_forcing_links', msg_type), config)
        assert workers == []

    @pytest.mark.parametrize('msg_type, args, host_name', [
        ('success nowcast+', ['west.cloud', 'nowcast'], 'west.cloud'),
        ('success nowcast-green',
            ['salish', 'nowcast-green', '--shared-storage'], 'salish'),
        ('success ssh', ['west.cloud', 'forecast'], 'west.cloud'),
        ('success forecast2', ['west.cloud', 'forecast2'], 'west.cloud'),
    ])
    def test_success_launch_run_NEMO(
        self, msg_type, args, host_name, config,
    ):
        workers = next_workers.after_make_forcing_links(
            Message('make_forcing_links', msg_type, payload={host_name: ''}),
            config)
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
    def test_no_next_worker_msg_types(self, msg_type, config):
        workers = next_workers.after_run_NEMO(
            Message('run_NEMO', msg_type), config)
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
    def test_no_next_worker_msg_types(self, msg_type, config):
        workers = next_workers.after_watch_NEMO(
            Message('watch_NEMO', msg_type), config)
        assert workers == []

    def test_success_nowcast_launch_get_NeahBay_ssh_forecast(self, config):
        workers = next_workers.after_watch_NEMO(
            Message(
                'watch_NEMO', 'success nowcast', {
                    'nowcast': {
                        'host': 'cloud', 'run date': '2016-10-16',
                        'completed': True,}}),
                config)
        expected = NextWorker(
            'nowcast.workers.get_NeahBay_ssh',
            args=['forecast'], host='localhost')
        assert workers[0] == expected

    @pytest.mark.parametrize('msg', [
        Message(
            'watch_NEMO', 'success nowcast', {
                'nowcast': {
                    'host': 'cloud', 'run date': '2016-10-15',
                    'completed': True}}),
        Message(
            'watch_NEMO', 'success forecast', {
                'forecast': {
                    'host': 'cloud', 'run date': '2016-10-15',
                    'completed': True}}),
        Message(
            'watch_NEMO', 'success forecast2', {
                'forecast2': {
                    'host': 'cloud', 'run date': '2016-10-15',
                    'completed': True}}),
    ])
    def test_success_launch_download_results(self, msg, config):
        workers = next_workers.after_watch_NEMO(msg, config)
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
                    'completed': True}}),
    ])
    def test_success_nowcast_grn_no_launch_download_results(self, msg, config):
        workers = next_workers.after_watch_NEMO(msg, config)
        assert workers == []


class TestAfterDownloadResults:
    """Unit tests for the after_download_results function.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast',
        'failure forecast',
        'failure forecast2',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config):
        checklist = {}
        workers = next_workers.after_download_results(
            Message('download_results', msg_type), config, checklist)
        assert workers == []

    @pytest.mark.parametrize('run_type, plot_type', [
        ('nowcast', 'publish'),
        ('forecast', 'publish'),
        ('forecast2', 'publish'),
    ])
    def test_success_launch_make_plots(self, run_type, plot_type, config):
        checklist = {'NEMO run': {run_type: {'run date': '2016-10-22'}}}
        workers = next_workers.after_download_results(
            Message(
                'download results', 'success {}'.format(run_type)),
            config, checklist)
        expected = NextWorker(
            'nowcast.workers.make_plots',
            args=[run_type, plot_type, '--run-date', '2016-10-22'],
            host='localhost')
        assert expected in workers


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
        'success forecast publish',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config):
        workers = next_workers.after_make_plots(
            Message('make_plots', msg_type), config)
        assert workers == []

    def test_success_forecast2_publish_launch_clear_checklist(self, config):
        workers = next_workers.after_make_plots(
            Message('make_plots', 'success forecast2 publish'), config)
        assert workers[-1] == NextWorker(
            'nemo_nowcast.workers.clear_checklist', args=[], host='localhost')


class TestAfterClearChecklist:
    """Unit tests for the after_clear_checklist function.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config):
        workers = next_workers.after_clear_checklist(
            Message('clear_checklist', msg_type), config)
        assert workers == []

    def test_success_launch_rotate_logs(self, config):
        workers = next_workers.after_clear_checklist(
            Message('rotate_logs', 'success'), config)
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
    def test_no_next_worker_msg_types(self, msg_type, config):
        workers = next_workers.after_rotate_logs(
            Message('rotate_logs', msg_type), config)
        assert workers == []
