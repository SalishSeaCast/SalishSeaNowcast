# Copyright 2013-2018 The Salish Sea MEOPAR contributors
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
        'temperature salinity': {
            'matlab host': 'salish'
        },
        'observations': {
            'ctd data': {
                'stations': ['SCVIP', 'SEVIP', 'USDDL'],
            },
            'ferry data': {
                'ferries': {
                    'TWDP': {}
                },
            },
        },
        'run types': {
            'nowcast': {},
            'nowcast-dev': {},
            'nowcast-green': {},
            'nowcast-agrif': {},
            'forecast': {},
            'forecast2': {}
        },
        'run': {
            'enabled hosts': {
                'west.cloud': {
                    'shared storage':
                        False,
                    'run types': [
                        'nowcast', 'forecast', 'forecast2', 'nowcast-green'
                    ],
                },
                'salish': {
                    'shared storage': True,
                    'run types': ['nowcast-dev'],
                },
                'orcinus': {
                    'shared storage': False,
                    'run types': ['nowcast-agrif'],
                },
            },
            'hindcast hosts': {
                'cedar': {},
            },
        },
        'wave forecasts': {
            'host': 'west.cloud',
            'run when': 'after nowcast-green',
        },
        'vhfr fvcom runs': {
            'host': 'west.cloud',
        },
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

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure 00',
            'failure 06',
            'failure 12',
            'failure 18',
            'success 00',
            'success 18',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type), config, checklist
        )
        assert workers == []

    def test_success_06_launch_make_runoff_file(self, config, checklist):
        workers = next_workers.after_download_weather(
            Message('download_weather', 'success 06'), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.make_runoff_file', [], host='localhost'
        )
        assert expected in workers

    @pytest.mark.parametrize(
        'msg_type, args', [
            ('success 06', ['forecast2']),
            ('success 12', ['nowcast']),
        ]
    )
    def test_success_launch_get_NeahBay_ssh(
        self, msg_type, args, config, checklist
    ):
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.get_NeahBay_ssh', args, host='localhost'
        )
        assert expected in workers

    @pytest.mark.parametrize(
        'msg_type, args', [
            ('success 06', ['forecast2']),
            ('success 12', ['nowcast+']),
        ]
    )
    def test_success_launch_grib_to_netcdf(
        self, msg_type, args, config, checklist
    ):
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.grib_to_netcdf', args, host='localhost'
        )
        assert expected in workers

    @pytest.mark.parametrize('ctd_stn', [
        'SCVIP',
        'SEVIP',
        'USDDL',
    ])
    def test_success_06_launch_get_onc_ctd(self, ctd_stn, config, checklist):
        workers = next_workers.after_download_weather(
            Message('download_weather', 'success 06'), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.get_onc_ctd', args=[ctd_stn], host='localhost'
        )
        assert expected in workers

    @pytest.mark.parametrize('ferry_platform', [
        'TWDP',
    ])
    def test_success_06_launch_get_onc_ferry(
        self, ferry_platform, config, checklist
    ):
        workers = next_workers.after_download_weather(
            Message('download_weather', 'success 06'), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.get_onc_ferry',
            args=[ferry_platform],
            host='localhost'
        )
        assert expected in workers

    def test_success_12_launch_download_live_ocean(self, config, checklist):
        workers = next_workers.after_download_weather(
            Message('download_weather', 'success 12'), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.download_live_ocean', [], host='localhost'
        )
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
            Message('make_runoff_file', msg_type), config, checklist
        )
        assert workers == []


class TestAfterGetNeahBaySsh:
    """Unit tests for the after_get_NeahBay_ssh function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure nowcast',
            'failure forecast',
            'failure forecast2',
            'success nowcast',
            'success forecast2',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_get_NeahBay_ssh(
            Message('get_NeahBay_ssh', msg_type), config, checklist
        )
        assert workers == []

    def test_success_forecast_launch_upload_forcing_ssh(
        self,
        config,
        checklist,
    ):
        workers = next_workers.after_get_NeahBay_ssh(
            Message('get_NeahBay_ssh', 'success forecast'), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.upload_forcing',
            args=['west.cloud', 'ssh'],
            host='localhost'
        )
        assert expected in workers


class TestAfterGribToNetcdf:
    """Unit tests for the after_grib_to_netcdf function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure nowcast+',
            'failure forecast2',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_grib_to_netcdf(
            Message('grib_to_netcdf', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'forecast2',
    ])
    def test_success_launch_upload_forcing(self, run_type, config, checklist):
        workers = next_workers.after_grib_to_netcdf(
            Message('grib_to_netcdf', 'success {}'.format(run_type)), config,
            checklist
        )
        expected = NextWorker(
            'nowcast.workers.upload_forcing',
            args=['west.cloud', run_type],
            host='localhost'
        )
        assert expected in workers

    def test_success_forecast2_no_launch_upload_forcing_nowcastp(
        self, config, checklist
    ):
        workers = next_workers.after_grib_to_netcdf(
            Message('grib_to_netcdf', 'success forecast2'), config, checklist
        )
        not_expected = NextWorker(
            'nowcast.workers.upload_forcing',
            args=['salish', 'nowcast+'],
            host='localhost'
        )
        assert not_expected not in workers

    def test_success_nowcastp_launch_ping_erddap_download_weather(
        self, config, checklist
    ):
        workers = next_workers.after_grib_to_netcdf(
            Message('grib_to_netcdf', 'success nowcast+'), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.ping_erddap',
            args=['download_weather'],
            host='localhost'
        )
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
            Message('get_onc_ctd', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize('ctd_stn', [
        'SCVIP',
        'SEVIP',
        'USDDL',
    ])
    def test_success_launch_ping_erddap(self, ctd_stn, config, checklist):
        workers = next_workers.after_get_onc_ctd(
            Message('get_onc_ctd', 'success {}'.format(ctd_stn)), config,
            checklist
        )
        expected = NextWorker(
            'nowcast.workers.ping_erddap',
            args=['{}-CTD'.format(ctd_stn)],
            host='localhost'
        )
        assert expected in workers


class TestAfterGetONC_Ferry:
    """Unit tests for the after_get_onc_ferry function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_get_onc_ferry(
            Message('get_onc_ferry', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize('ferry_platform', [
        'TWDP',
    ])
    def test_success_launch_ping_erddap(
        self, ferry_platform, config, checklist
    ):
        workers = next_workers.after_get_onc_ferry(
            Message('get_onc_ferry', 'success {}'.format(ferry_platform)),
            config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.ping_erddap',
            args=['{}-ferry'.format(ferry_platform)],
            host='localhost'
        )
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
            Message('download_live_ocean', msg_type), config, checklist
        )
        assert workers == []

    def test_success_launch_make_live_ocean_files(self, config, checklist):
        with patch.dict(
            checklist, {
                'Live Ocean products': {
                    '2017-02-15': []
                }
            }
        ):
            workers = next_workers.after_download_live_ocean(
                Message('download_live_ocean', 'success'), config, checklist
            )
        expected = NextWorker(
            'nowcast.workers.make_live_ocean_files',
            args=['--run-date', '2017-02-15'],
            host='salish'
        )
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
            Message('make_live_ocean_files', msg_type), config, checklist
        )
        assert workers == []


class TestAfterMakeTurbidityFile:
    """Unit tests for the after_make_turbidity_file function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_turbidity_file(
            Message('make_turbidity_file', msg_type), config, checklist
        )
        assert workers == []

    def test_success_launch_upload_forcing_west_cloud(self, config, checklist):
        workers = next_workers.after_make_turbidity_file(
            Message('make_turbidity_file', 'success'), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.upload_forcing',
            args=['west.cloud', 'turbidity'],
            host='localhost'
        )
        assert expected in workers

    def test_success_no_launch_upload_forcing_salish(self, config, checklist):
        workers = next_workers.after_make_turbidity_file(
            Message('make_turbidity_file', 'success'), config, checklist
        )
        not_expected = NextWorker(
            'nowcast.workers.upload_forcing',
            args=['salish-nowcast', 'turbidity'],
            host='localhost'
        )
        assert not_expected not in workers


class TestAfterUploadForcing:
    """Unit tests for the after_upload_forcing function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure nowcast+',
            'failure forecast2',
            'failure ssh',
            'failure turbidity',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_upload_forcing(
            Message('upload_forcing', msg_type), config, checklist
        )
        assert workers == []

    def test_msg_payload_missing_host_name(self, config, checklist):
        workers = next_workers.after_upload_forcing(
            Message('upload_forcing', 'crash'), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize('run_type', [
        'nowcast+',
        'ssh',
        'forecast2',
    ])
    def test_success_launch_make_forcing_links(
        self, run_type, config, checklist
    ):
        workers = next_workers.after_upload_forcing(
            Message(
                'upload_forcing', 'success {}'.format(run_type), {
                    'west.cloud': '2016-10-11 ssh'
                }
            ), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.make_forcing_links',
            args=['west.cloud', run_type],
            host='localhost'
        )
        assert expected in workers

    def test_success_turbidity_launch_make_forcing_links_nowcast_green(
        self, config, checklist
    ):
        workers = next_workers.after_upload_forcing(
            Message(
                'upload_forcing', 'success turbidity', {
                    'west.cloud': '2017-08-10 turbidity'
                }
            ), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.make_forcing_links',
            args=['west.cloud', 'nowcast-green'],
            host='localhost'
        )
        assert expected in workers

    def test_success_turbidity_launch_make_forcing_links_nowcast_agrif(
        self, config, checklist
    ):
        workers = next_workers.after_upload_forcing(
            Message(
                'upload_forcing', 'success turbidity', {
                    'orcinus': '2018-03-31 turbidity'
                }
            ), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.make_forcing_links',
            args=['orcinus', 'nowcast-agrif'],
            host='localhost'
        )
        assert expected in workers


class TestAfterMakeForcingLinks:
    """Unit tests for the after_make_forcing_links function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure nowcast+',
            'failure nowcast-green',
            'failure forecast2',
            'failure ssh',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_forcing_links(
            Message('make_forcing_links', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        'msg_type, args, host_name', [
            (
                'success nowcast+', [
                    'west.cloud', 'nowcast', '--run-date', '2016-10-23'
                ], 'west.cloud'
            ),
            (
                'success nowcast-green', [
                    'west.cloud', 'nowcast-green', '--run-date', '2016-10-23'
                ], 'west.cloud'
            ),
            (
                'success nowcast+',
                ['salish', 'nowcast-dev', '--run-date', '2016-10-23'], 'salish'
            ),
            (
                'success ssh', [
                    'west.cloud', 'forecast', '--run-date', '2016-10-23'
                ], 'west.cloud'
            ),
            (
                'success forecast2', [
                    'west.cloud', 'forecast2', '--run-date', '2016-10-23'
                ], 'west.cloud'
            ),
        ]
    )
    def test_success_launch_run_NEMO(
        self, msg_type, args, host_name, config, checklist
    ):
        p_checklist = patch.dict(
            checklist, {
                'forcing links': {
                    host_name: {
                        'links': '',
                        'run date': '2016-10-23'
                    }
                }
            }
        )
        with p_checklist:
            workers = next_workers.after_make_forcing_links(
                Message(
                    'make_forcing_links', msg_type, payload={
                        host_name: ''
                    }
                ), config, checklist
            )
        expected = NextWorker(
            'nowcast.workers.run_NEMO', args=args, host=host_name
        )
        assert expected in workers


class TestAfterRunNEMO:
    """Unit tests for the after_run_NEMO function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure nowcast',
            'failure nowcast-green',
            'failure nowcast-dev',
            'failure forecast',
            'failure forecast2',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_run_NEMO(
            Message('run_NEMO', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        'msg_type, host', [
            ('success nowcast', 'west.cloud'),
            ('success nowcast-green', 'west.cloud'),
            ('success nowcast-dev', 'salish'),
            ('success forecast', 'west.cloud'),
            ('success forecast2', 'west.cloud'),
        ]
    )
    def test_success_launch_watch_NEMO(
        self, msg_type, host, config, checklist
    ):
        run_type = msg_type.split()[1]
        workers = next_workers.after_run_NEMO(
            Message('run_NEMO', msg_type, {
                run_type: {
                    'host': host
                }
            }), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.watch_NEMO', args=[host, run_type], host=host
        )
        assert workers[0] == expected


class TestAfterWatchNEMO:
    """Unit tests for the after_watch_NEMO function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure nowcast',
            'failure nowcast-green',
            'failure nowcast-dev',
            'failure forecast',
            'failure forecast2',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_watch_NEMO(
            Message('watch_NEMO', msg_type), config, checklist
        )
        assert workers == []

    def test_success_nowcast_launch_get_NeahBay_ssh_forecast(
        self, config, checklist
    ):
        workers = next_workers.after_watch_NEMO(
            Message(
                'watch_NEMO', 'success nowcast', {
                    'nowcast': {
                        'host': 'west.cloud',
                        'run date': '2016-10-16',
                        'completed': True,
                    }
                }
            ), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.get_NeahBay_ssh',
            args=['forecast'],
            host='localhost'
        )
        assert workers[0] == expected

    def test_success_nowcast_launch_make_fvcom_boundary(
        self, config, checklist
    ):
        workers = next_workers.after_watch_NEMO(
            Message(
                'watch_NEMO', 'success nowcast', {
                    'nowcast': {
                        'host': 'west.cloud',
                        'run date': '2018-01-20',
                        'completed': True,
                    }
                }
            ), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.make_fvcom_boundary',
            args=['west.cloud', 'nowcast'],
            host='west.cloud'
        )
        assert expected in workers

    def test_success_forecast_launch_make_turbidity_file(
        self, config, checklist
    ):
        workers = next_workers.after_watch_NEMO(
            Message(
                'watch_NEMO', 'success forecast', {
                    'forecast': {
                        'host': 'west.cloud',
                        'run date': '2017-08-10',
                        'completed': True,
                    }
                }
            ), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.make_turbidity_file',
            args=['--run-date', '2017-08-10'],
            host='localhost'
        )
        assert workers[0] == expected

    def test_success_forecast_launch_make_ww3_wind_file_forecast(
        self, config, checklist
    ):
        p_config = patch.dict(
            config['wave forecasts'], {
                'run when': 'after forecast'
            }
        )
        with p_config:
            workers = next_workers.after_watch_NEMO(
                Message(
                    'watch_NEMO', 'success forecast', {
                        'forecast': {
                            'host': 'west.cloud',
                            'run date': '2017-04-14',
                            'completed': True,
                        }
                    }
                ), config, checklist
            )
        expected = NextWorker(
            'nowcast.workers.make_ww3_wind_file',
            args=['west.cloud', 'forecast'],
            host='west.cloud'
        )
        assert workers[0] == expected

    def test_success_forecast_launch_make_ww3_current_file_forecast(
        self, config, checklist
    ):
        p_config = patch.dict(
            config['wave forecasts'], {
                'run when': 'after forecast'
            }
        )
        with p_config:
            workers = next_workers.after_watch_NEMO(
                Message(
                    'watch_NEMO', 'success forecast', {
                        'forecast': {
                            'host': 'west.cloud',
                            'run date': '2017-04-14',
                            'completed': True,
                        }
                    }
                ), config, checklist
            )
        expected = NextWorker(
            'nowcast.workers.make_ww3_current_file',
            args=['west.cloud', 'forecast'],
            host='west.cloud'
        )
        assert workers[1] == expected

    def test_success_forecast2_launch_make_ww3_wind_file_forecast2(
        self, config, checklist
    ):
        workers = next_workers.after_watch_NEMO(
            Message(
                'watch_NEMO', 'success forecast2', {
                    'forecast2': {
                        'host': 'west.cloud',
                        'run date': '2017-04-14',
                        'completed': True,
                    }
                }
            ), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.make_ww3_wind_file',
            args=['west.cloud', 'forecast2'],
            host='west.cloud'
        )
        assert workers[0] == expected

    def test_success_forecast2_launch_make_ww3_current_file_forecast2(
        self, config, checklist
    ):
        workers = next_workers.after_watch_NEMO(
            Message(
                'watch_NEMO', 'success forecast2', {
                    'forecast2': {
                        'host': 'west.cloud',
                        'run date': '2017-04-14',
                        'completed': True,
                    }
                }
            ), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.make_ww3_current_file',
            args=['west.cloud', 'forecast2'],
            host='west.cloud'
        )
        assert workers[1] == expected

    def test_success_nowcast_green_launch_make_ww3_wind_file_forecast(
        self, config, checklist
    ):
        p_config = patch.dict(
            config['wave forecasts'], {
                'run when': 'after nowcast-green'
            }
        )
        with p_config:
            workers = next_workers.after_watch_NEMO(
                Message(
                    'watch_NEMO', 'success nowcast-green', {
                        'nowcast-green': {
                            'host': 'west.cloud',
                            'run date': '2017-04-14',
                            'completed': True,
                        }
                    }
                ), config, checklist
            )
        expected = NextWorker(
            'nowcast.workers.make_ww3_wind_file',
            args=['west.cloud', 'forecast'],
            host='west.cloud'
        )
        assert workers[0] == expected

    def test_success_nowcast_green_launch_make_ww3_current_file_forecast(
        self, config, checklist
    ):
        p_config = patch.dict(
            config['wave forecasts'], {
                'run when': 'after nowcast-green'
            }
        )
        with p_config:
            workers = next_workers.after_watch_NEMO(
                Message(
                    'watch_NEMO', 'success nowcast-green', {
                        'nowcast-green': {
                            'host': 'west.cloud',
                            'run date': '2017-04-14',
                            'completed': True,
                        }
                    }
                ), config, checklist
            )
        expected = NextWorker(
            'nowcast.workers.make_ww3_current_file',
            args=['west.cloud', 'forecast'],
            host='west.cloud'
        )
        assert workers[1] == expected

    def test_success_nowcast_green_launch_mk_forcing_links_nowcastp_shrdstrg(
        self, config, checklist
    ):
        workers = next_workers.after_watch_NEMO(
            Message(
                'watch_NEMO', 'success nowcast-green', {
                    'nowcast-green': {
                        'host': 'west.cloud',
                        'run date': '2017-05-31',
                        'completed': True,
                    }
                }
            ), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.make_forcing_links',
            args=['salish', 'nowcast+', '--shared-storage'],
            host='localhost'
        )
        assert expected in workers

    @pytest.mark.parametrize(
        'msg', [
            Message(
                'watch_NEMO', 'success nowcast', {
                    'nowcast': {
                        'host': 'west.cloud',
                        'run date': '2016-10-15',
                        'completed': True
                    }
                }
            ),
            Message(
                'watch_NEMO', 'success forecast', {
                    'forecast': {
                        'host': 'west.cloud',
                        'run date': '2016-10-15',
                        'completed': True
                    }
                }
            ),
            Message(
                'watch_NEMO', 'success nowcast-green', {
                    'nowcast-green': {
                        'host': 'west.cloud',
                        'run date': '2016-10-15',
                        'completed': True
                    }
                }
            ),
            Message(
                'watch_NEMO', 'success forecast2', {
                    'forecast2': {
                        'host': 'west.cloud',
                        'run date': '2016-10-15',
                        'completed': True
                    }
                }
            ),
        ]
    )
    def test_success_launch_download_results(self, msg, config, checklist):
        workers = next_workers.after_watch_NEMO(msg, config, checklist)
        run_type = msg.type.split()[1]
        expected = NextWorker(
            'nowcast.workers.download_results',
            args=[
                msg.payload[run_type]['host'], run_type, '--run-date',
                msg.payload[run_type]['run date']
            ],
            host='localhost'
        )
        assert expected in workers

    @pytest.mark.parametrize(
        'msg', [
            Message(
                'watch_NEMO', 'success nowcast-dev', {
                    'nowcast-dev': {
                        'host': 'salish',
                        'run date': '2016-10-15',
                        'completed': True
                    }
                }
            ),
        ]
    )
    def test_success_nowcast_dev_no_launch_download_results(
        self, msg, config, checklist
    ):
        workers = next_workers.after_watch_NEMO(msg, config, checklist)
        download_results = NextWorker(
            'nowcast.workers.download_results',
            args=[
                msg.payload['nowcast-dev']['host'],
                msg.type.split()[1], '--run-date',
                msg.payload['nowcast-dev']['run date']
            ],
            host='localhost'
        )
        assert download_results not in workers


class TestAfterMakeFVCOMBoundary:
    """Unit tests for the after_make_fvcom_boundary function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure nowcast',
            'failure forecast',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_fvcom_boundary(
            Message('make_fvcom_boundary', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize('run_type', [
        'nowcast',
    ])
    def test_success_launch_make_fvcom_atmos_forcing(
        self, run_type, config, checklist
    ):

        msg = Message(
            'make_fvcom_boundary',
            f'success {run_type}',
            payload={
                run_type: {
                    'run date': '2018-03-16',
                    'open boundary file': 'input/bdy_nowcast_btrp_20180316.nc'
                }
            }
        )
        workers = next_workers.after_make_fvcom_boundary(
            msg, config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.make_fvcom_atmos_forcing',
            args=[run_type, '--run-date', '2018-03-16'],
            host='localhost'
        )
        assert expected in workers

    @pytest.mark.parametrize('run_type', [
        'nowcast',
    ])
    def test_success_launch_run_fvcom(self, run_type, config, checklist):
        """
        TODO: Move to after_make_fvcom_atmos_forcing when run_fvcom is capable of handling atmos forcing
        """
        msg = Message(
            'make_fvcom_boundary',
            f'success {run_type}',
            payload={
                run_type: {
                    'run date': '2018-03-16',
                    'open boundary file': 'input/bdy_nowcast_btrp_20180316.nc'
                }
            }
        )
        workers = next_workers.after_make_fvcom_boundary(
            msg, config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.run_fvcom',
            args=['west.cloud', run_type, '--run-date', '2018-03-16'],
            host='west.cloud'
        )
        assert expected in workers


class TestAfterMakeFVCOMAtmosForcing:
    """Unit tests for the after_make_fvcom_boundary function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure nowcast',
            'success nowcast',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_fvcom_atmos_forcing(
            Message('make_fvcom_atmos_forcing', msg_type), config, checklist
        )
        assert workers == []


class TestAfterRunFVCOM:
    """Unit tests for the after_run_fvcom function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure nowcast',
            'failure forecast',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_run_fvcom(
            Message('run_fvcom', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        'msg_type, host', [
            ('success nowcast', 'west.cloud'),
            ('success forecast', 'west.cloud'),
        ]
    )
    def test_success_launch_watch_fvcom(
        self, msg_type, host, config, checklist
    ):
        run_type = msg_type.split()[1]
        workers = next_workers.after_run_fvcom(
            Message('run_fvcom', msg_type, {
                run_type: {
                    'host': host
                }
            }), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.watch_fvcom', args=[host, run_type], host=host
        )
        assert workers[0] == expected


class TestAfterWatchFVCOM:
    """Unit tests for the after_watch_fvcom function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_watch_fvcom(
            Message('watch_fvcom', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        'msg', [
            Message(
                'watch_fvcom', 'success nowcast', {
                    'nowcast': {
                        'host': 'west.cloud',
                        'run date': '2018-02-16',
                        'completed': True
                    }
                }
            )
        ]
    )
    def test_success_launch_download_fvcom_results(
        self, msg, config, checklist
    ):
        workers = next_workers.after_watch_fvcom(msg, config, checklist)
        run_type = msg.type.split()[1]
        expected = NextWorker(
            'nowcast.workers.download_fvcom_results',
            args=[
                msg.payload[run_type]['host'],
                msg.type.split()[1], '--run-date',
                msg.payload[run_type]['run date']
            ],
            host='localhost'
        )
        assert expected in workers


class TestAfterMakeWW3WindFile:
    """Unit tests for the after_make_ww3_wind_file function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure forecast2',
            'failure forecast',
            'success forecast2',
            'success forecast',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_ww3_wind_file(
            Message('make_ww3_wind_file', msg_type), config, checklist
        )
        assert workers == []


class TestAfterMakeWW3currentFile:
    """Unit tests for the after_make_ww3_current_file function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure forecast2',
            'failure forecast',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_ww3_current_file(
            Message('make_ww3_current_file', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize('run_type', [
        'forecast',
        'forecast2',
    ])
    def test_success_launch_run_ww3(self, run_type, config, checklist):
        workers = next_workers.after_make_ww3_current_file(
            Message(
                'make_ww3_current_file', f'success {run_type}', {
                    run_type: 'current/SoG_current_20170415.nc'
                }
            ), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.run_ww3',
            args=['west.cloud', run_type],
            host='west.cloud'
        )
        assert workers[0] == expected


class TestAfterRunWW3:
    """Unit tests for the after_run_ww3 function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure forecast2',
            'failure forecast',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_run_ww3(
            Message('run_ww3', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        'msg_type, host', [
            ('success forecast2', 'west.cloud'),
            ('success forecast', 'west.cloud'),
        ]
    )
    def test_success_launch_watch_ww3(self, msg_type, host, config, checklist):
        run_type = msg_type.split()[1]
        workers = next_workers.after_run_ww3(
            Message('run_ww3', msg_type, {
                run_type: {
                    'host': host
                }
            }), config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.watch_ww3', args=[host, run_type], host=host
        )
        assert workers[0] == expected


class TestAfterWatchWW3:
    """Unit tests for the after_watch_ww3 function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure forecast2',
            'failure forecast',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_watch_ww3(
            Message('watch_ww3', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        'msg', [
            Message(
                'watch_ww3', 'success forecast', {
                    'forecast': {
                        'host': 'west.cloud',
                        'run date': '2017-12-24',
                        'completed': True
                    }
                }
            ),
            Message(
                'watch_ww3', 'success forecast2', {
                    'forecast2': {
                        'host': 'west.cloud',
                        'run date': '2017-12-24',
                        'completed': True
                    }
                }
            ),
        ]
    )
    def test_success_launch_download_wwatch3_results(
        self, msg, config, checklist
    ):
        workers = next_workers.after_watch_ww3(msg, config, checklist)
        run_type = msg.type.split()[1]
        expected = NextWorker(
            'nowcast.workers.download_wwatch3_results',
            args=[
                msg.payload[run_type]['host'],
                msg.type.split()[1], '--run-date',
                msg.payload[run_type]['run date']
            ],
            host='localhost'
        )
        assert expected in workers


class TestAfterWatchNEMO_Hindcast:
    """Unit tests for the after_watch_NEMO_hindcast function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_watch_NEMO_hindcast(
            Message('watch_NEMO_hindcast', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        'msg', [
            Message(
                'watch_NEMO_hindcast', 'success', {
                    'hindcast': {
                        'host': 'cedar',
                        'run date': '2018-03-10',
                        'completed': True
                    }
                }
            ),
        ]
    )
    def test_success_launch_download_results(self, msg, config, checklist):
        workers = next_workers.after_watch_NEMO_hindcast(
            msg, config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.download_results',
            args=[
                msg.payload['hindcast']['host'], 'hindcast', '--run-date',
                msg.payload['hindcast']['run date']
            ],
            host='localhost'
        )
        assert expected in workers

    @pytest.mark.parametrize(
        'msg', [
            Message(
                'watch_NEMO_hindcast', 'success', {
                    'hindcast': {
                        'host': 'cedar',
                        'run date': '2018-03-12',
                        'completed': True
                    }
                }
            ),
        ]
    )
    def test_success_launch_watch_NEMO_hindcast(self, msg, config, checklist):
        workers = next_workers.after_watch_NEMO_hindcast(
            msg, config, checklist
        )
        expected = NextWorker(
            'nowcast.workers.watch_NEMO_hindcast',
            args=[msg.payload['hindcast']['host']],
            host='localhost'
        )
        assert expected in workers


class TestAfterRunNEMO_Hindcast:
    """Unit tests for the after_run_NEMO_hindcast function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
        'success',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_run_NEMO_hindcast(
            Message('run_NEMO_hindcast', msg_type), config, checklist
        )
        assert workers == []


class TestAfterDownloadResults:
    """Unit tests for the after_download_results function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure nowcast',
            'failure nowcast-green',
            'failure forecast',
            'failure forecast2',
            'failure hindcast',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        p_checklist = patch.dict(
            checklist, {
                'NEMO run': {
                    'nowcast-green': {
                        'run date': '2016-10-22'
                    }
                }
            }
        )
        with p_checklist:
            workers = next_workers.after_download_results(
                Message('download_results', msg_type), config, checklist
            )
        assert workers == []

    @pytest.mark.parametrize(
        'model, run_type, plot_type, run_date', [
            ('nemo', 'nowcast', 'research', '2016-10-29'),
            ('nemo', 'nowcast', 'comparison', '2016-10-28'),
            ('nemo', 'nowcast-green', 'research', '2016-10-29'),
        ]
    )
    def test_success_nowcast_launch_make_plots_specials(
        self, model, run_type, plot_type, run_date, config, checklist
    ):
        p_checklist = patch.dict(
            checklist, {
                'NEMO run': {
                    run_type: {
                        'run date': '2016-10-29'
                    }
                }
            }
        )
        with p_checklist:
            workers = next_workers.after_download_results(
                Message('download results', 'success {}'.format(run_type)),
                config, checklist
            )
        expected = NextWorker(
            'nowcast.workers.make_plots',
            args=[model, run_type, plot_type, '--run-date', run_date],
            host='localhost'
        )
        assert expected in workers

    def test_success_nowcast_green_launch_ping_erddap_nowcast_green(
        self, config, checklist
    ):
        p_checklist = patch.dict(
            checklist, {
                'NEMO run': {
                    'nowcast-green': {
                        'run date': '2017-06-22'
                    }
                }
            }
        )
        with p_checklist:
            workers = next_workers.after_download_results(
                Message('download_results', 'success nowcast-green'), config,
                checklist
            )
        expected = NextWorker(
            'nowcast.workers.ping_erddap',
            args=['nowcast-green'],
            host='localhost'
        )
        assert expected in workers

    @pytest.mark.parametrize(
        'run_type, run_date', [
            ('forecast', '2017-11-11'),
            ('forecast2', '2018-01-24'),
        ]
    )
    def test_success_forecast_launch_update_forecast_datasets(
        self, run_type, run_date, config, checklist
    ):
        p_checklist = patch.dict(
            checklist, {
                'NEMO run': {
                    run_type: {
                        'run date': run_date
                    }
                }
            }
        )
        with p_checklist:
            workers = next_workers.after_download_results(
                Message('download_results', f'success {run_type}'), config,
                checklist
            )
        expected = NextWorker(
            'nowcast.workers.update_forecast_datasets',
            args=['nemo', run_type, '--run-date', run_date],
            host='localhost'
        )
        assert expected in workers

    def test_success_hindcast_launch_split_results(self, config, checklist):
        p_checklist = patch.dict(
            checklist, {
                'NEMO run': {
                    'hindcast': {
                        'run id': '11mar18hindcast'
                    }
                }
            }
        )
        with p_checklist:
            workers = next_workers.after_download_results(
                Message('download_results', f'success hindcast'), config,
                checklist
            )
        expected = NextWorker(
            'nowcast.workers.split_results',
            args=['hindcast', '2018-03-11'],
            host='localhost'
        )
        assert expected in workers


class TestAfterSplitResults:
    """Unit tests for after_split_results function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure hindcast',
            'success hindcast',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_split_results(
            Message('split_results', msg_type), config, checklist
        )
        assert workers == []


class TestAfterDownloadWWatch3Results:
    """Unit tests for the after_download_wwatch3_results function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure forecast',
            'failure forecast2',
            'success forecast',
            'success forecast2',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        p_checklist = patch.dict(
            checklist, {
                'WW3 run': {
                    'forecast': {
                        'run date': '2017-12-24'
                    }
                }
            }
        )
        with p_checklist:
            workers = next_workers.after_download_wwatch3_results(
                Message('download_wwatch3_results', msg_type), config,
                checklist
            )
        assert workers == []


class TestAfterDownloadFVCOMResults:
    """Unit tests for the after_download_fvcom_results function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        p_checklist = patch.dict(
            checklist, {
                'FVCOM run': {
                    'nowcast': {
                        'run date': '2018-02-19'
                    }
                }
            }
        )
        with p_checklist:
            workers = next_workers.after_download_fvcom_results(
                Message('download_fvcom_results', msg_type), config, checklist
            )
        assert workers == []

    @pytest.mark.parametrize('msg_type', [
        'success nowcast',
    ])
    def test_success_launch_make_plots(self, msg_type, config, checklist):
        p_checklist = patch.dict(
            checklist, {
                'FVCOM run': {
                    'nowcast': {
                        'run date': '2018-02-27'
                    }
                }
            }
        )
        with p_checklist:
            workers = next_workers.after_download_fvcom_results(
                Message('download_fvcom_results', msg_type), config, checklist
            )
        expected = NextWorker(
            'nowcast.workers.make_plots',
            args=['fvcom', 'nowcast', 'publish', '--run-date', '2018-02-27'],
            host='localhost'
        )
        assert expected in workers


class TestAfterUpdateForecastDatasets:
    """Unit tests for the after_update_forecast_datasets function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure nemo forecast',
            'failure nemo forecast2',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_update_forecast_datasets(
            Message('update_forecast_datasets', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        'run_type, run_date', [
            ('forecast', '2018-01-26'),
            ('forecast2', '2018-01-26'),
        ]
    )
    def test_success_launch_ping_erddap_nemo_forecast(
        self, run_type, run_date, config, checklist
    ):
        p_checklist = patch.dict(
            checklist, {
                'NEMO run': {
                    run_type: {
                        'run date': run_date
                    }
                }
            }
        )
        with p_checklist:
            workers = next_workers.after_update_forecast_datasets(
                Message(
                    'update_forecast_datasets', f'success nemo {run_type}'
                ), config, checklist
            )
        expected = NextWorker(
            'nowcast.workers.ping_erddap',
            args=['nemo-forecast'],
            host='localhost'
        )
        assert expected in workers

    @pytest.mark.parametrize(
        'run_type, run_date', [
            ('forecast', '2018-01-26'),
            ('forecast2', '2018-01-26'),
        ]
    )
    def test_success_launch_make_plots_forecast_publish(
        self, run_type, run_date, config, checklist
    ):
        p_checklist = patch.dict(
            checklist, {
                'NEMO run': {
                    run_type: {
                        'run date': run_date
                    }
                }
            }
        )
        with p_checklist:
            workers = next_workers.after_update_forecast_datasets(
                Message(
                    'update_forecast_datasets', f'success nemo {run_type}'
                ), config, checklist
            )
        expected = NextWorker(
            'nowcast.workers.make_plots',
            args=['nemo', run_type, 'publish', '--run-date', run_date],
            host='localhost'
        )
        assert expected in workers


class TestAfterPingERDDAP:
    """Unit tests for the after_ping_erddap function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure download_weather',
            'failure SCVIP-CTD',
            'failure SEVIP-CTD',
            'failure USDDL-CTD',
            'failure TWDP-ferry',
            'failure nowcast-green',
            'failure nemo-forecast',
            'success download_weather',
            'success SCVIP-CTD',
            'success SEVIP-CTD',
            'success USDDL-CTD',
            'success TWDP-ferry',
            'success nowcast-green',
            'success nemo-forecast',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_ping_erddap(
            Message('ping_erddap', msg_type), config, checklist
        )
        assert workers == []


class TestAfterMakePlots:
    """Unit tests for the after_make_plots function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure nemo nowcast research',
            'failure nemo nowcast comparison',
            'failure nemo nowcast publish',
            'failure nemo nowcast-green research',
            'failure nemo forecast publish',
            'failure nemo forecast2 publish',
            'failure fvcom nowcast publish',
            'success nemo nowcast research',
            'success nemo nowcast comparison',
            'success nemo nowcast publish',
            'success nemo nowcast-green research',
            'success fvcom nowcast publish',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_plots(
            Message('make_plots', msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        'msg_type, run_type', [
            ('success nemo forecast publish', 'forecast'),
            ('success nemo forecast2 publish', 'forecast2'),
        ]
    )
    def test_success_forecast_launch_make_feeds(
        self, msg_type, run_type, config, checklist
    ):
        p_checklist = patch.dict(
            checklist, {
                'NEMO run': {
                    run_type: {
                        'run date': '2016-11-11'
                    }
                }
            }
        )
        with p_checklist:
            workers = next_workers.after_make_plots(
                Message('make_plots', msg_type), config, checklist
            )
        expected = NextWorker(
            'nowcast.workers.make_feeds',
            args=[run_type, '--run-date', '2016-11-11'],
            host='localhost'
        )
        assert expected in workers


class TestAfterMakeSurfaceCurrentTiles:
    """Unit tests for the after_make_surface_current_tiles function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
        'success',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_surface_current_tiles(
            Message('make_surface_current_tiles', msg_type), config, checklist
        )
        assert workers == []


class TestAfterMakeFeeds:
    """Unit tests for the after_make_feeds function.
    """

    @pytest.mark.parametrize(
        'msg_type', [
            'crash',
            'failure forecast',
            'failure forecast2',
            'success forecast',
        ]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_feeds(
            Message('make_feeds', msg_type), config, checklist
        )
        assert workers == []

    def test_success_forecast2_publish_launch_clear_checklist(
        self, config, checklist
    ):
        workers = next_workers.after_make_feeds(
            Message('make_feeds', 'success forecast2'), config, checklist
        )
        assert workers[-1] == NextWorker(
            'nemo_nowcast.workers.clear_checklist', args=[], host='localhost'
        )


class TestAfterClearChecklist:
    """Unit tests for the after_clear_checklist function.
    """

    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
    ])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_clear_checklist(
            Message('clear_checklist', msg_type), config, checklist
        )
        assert workers == []

    def test_success_launch_rotate_logs(self, config, checklist):
        workers = next_workers.after_clear_checklist(
            Message('rotate_logs', 'success'), config, checklist
        )
        assert workers[-1] == NextWorker(
            'nemo_nowcast.workers.rotate_logs', args=[], host='localhost'
        )


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
            Message('rotate_logs', msg_type), config, checklist
        )
        assert workers == []
