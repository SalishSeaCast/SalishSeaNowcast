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

"""Unit tests for Salish Sea NEMO nowcast ping_erddap worker.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from nowcast.workers import ping_erddap


@patch('nowcast.workers.ping_erddap.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    def test_instantiate_worker(self, m_worker):
        ping_erddap.main()
        args, kwargs = m_worker.call_args
        assert args == ('ping_erddap',)
        assert list(kwargs.keys()) == ['description']

    def test_add_dataset_arg(self, m_worker):
        ping_erddap.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('dataset',)
        assert kwargs['choices'] == {
            'download_weather',
            'SCVIP-CTD', 'SEVIP-CTD', 'USDDL-CTD',
            'TWDP-ferry',
            'nowcast-green', 'nemo-forecast',
        }
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        ping_erddap.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            ping_erddap.ping_erddap,
            ping_erddap.success,
            ping_erddap.failure,
        )


@patch('nowcast.workers.ping_erddap.logger')
class TestSuccess:
    """Unit tests for success() function.
    """
    @pytest.mark.parametrize('dataset', [
        'download_weather',
        'SCVIP-CTD',
        'SEVIP-CTD',
        'USDDL-CTD',
        'TWDP-ferry',
        'nowcast-green',
        'nemo-forecast',
    ])
    def test_success_log_info(self, m_logger, dataset):
        parsed_args = SimpleNamespace(dataset=dataset)
        ping_erddap.success(parsed_args)
        assert m_logger.info.called

    @pytest.mark.parametrize('dataset, expected', [
        ('download_weather', 'success download_weather'),
        ('SCVIP-CTD', 'success SCVIP-CTD'),
        ('SEVIP-CTD', 'success SEVIP-CTD'),
        ('USDDL-CTD', 'success USDDL-CTD'),
        ('TWDP-ferry', 'success TWDP-ferry'),
        ('nowcast-green', 'success nowcast-green'),
        ('nemo-forecast', 'success nemo-forecast'),
    ])
    def test_success_msg_type(self, m_logger, dataset, expected):
        parsed_args = SimpleNamespace(dataset=dataset)
        msg_type = ping_erddap.success(parsed_args)
        assert msg_type == expected


@patch('nowcast.workers.ping_erddap.logger')
class TestFailure:
    """Unit tests for failure() function.
    """
    @pytest.mark.parametrize('dataset', [
        'download_weather',
        'SCVIP-CTD',
        'SEVIP-CTD',
        'USDDL-CTD',
        'TWDP-ferry',
        'nowcast-green',
        'nemo-forecast',
    ])
    def test_failure_log_error(self, m_logger, dataset):
        parsed_args = SimpleNamespace(dataset=dataset)
        ping_erddap.failure(parsed_args)
        assert m_logger.critical.called

    @pytest.mark.parametrize('dataset, expected', [
        ('download_weather', 'failure download_weather'),
        ('SCVIP-CTD', 'failure SCVIP-CTD'),
        ('SEVIP-CTD', 'failure SEVIP-CTD'),
        ('USDDL-CTD', 'failure USDDL-CTD'),
        ('TWDP-ferry', 'failure TWDP-ferry'),
        ('nowcast-green', 'failure nowcast-green'),
        ('nemo-forecast', 'failure nemo-forecast'),
    ])
    def test_failure_msg_type(self, m_logger, dataset, expected):
        parsed_args = SimpleNamespace(dataset=dataset)
        msg_type = ping_erddap.failure(parsed_args)
        assert msg_type == expected


@patch('nowcast.workers.ping_erddap.logger')
class TestPingErddap:
    """Unit tests for ping_erddap() function.
    """
    @pytest.mark.parametrize('dataset', [
        'download_weather',
        'SCVIP-CTD',
        'SEVIP-CTD',
        'USDDL-CTD',
        'TWDP-ferry',
        'nowcast-green',
        'nemo-forecast',
    ])
    def test_ping_erddap(self, m_logger, dataset, tmpdir):
        parsed_args = SimpleNamespace(dataset=dataset)
        tmp_flag_dir = tmpdir.ensure_dir('flag')
        config = {
            'erddap': {
                'flag dir': str(tmp_flag_dir),
                'datasetIDs': {
                    'download_weather':
                        ['ubcSSaSurfaceAtmosphereFieldsV1'],
                    'SCVIP-CTD': ['ubcONCSCVIPCTD15mV1'],
                    'SEVIP-CTD': ['ubcONCSEVIPCTD15mV1'],
                    'USDDL-CTD': ['ubcONCUSDDLCTD15mV1'],
                    'TWDP-ferry': ['ubcONCTWDP1mV1'],
                    'nowcast-green': [
                        'ubcSSg3DTracerFields1hV1', 'ubcSSg3DuVelocity1hV1'],
                    'nemo-forecast': ['ubcSSfPointAtkinson10mV17-02'],
                }}}
        checklist = ping_erddap.ping_erddap(parsed_args, config)
        dataset_ids = config['erddap']['datasetIDs'][dataset]
        for i, dataset_id in enumerate(dataset_ids):
            assert tmp_flag_dir.join(dataset_id).exists
            expected = '{} touched'.format(tmp_flag_dir.join(dataset_id))
            m_logger.debug.call_args_list[i] == expected
        expected = {dataset: config['erddap']['datasetIDs'][dataset]}
        assert checklist == expected

    def test_no_datasetID(self, m_logger, tmpdir):
        parsed_args = SimpleNamespace(dataset='nowcast-green')
        tmp_flag_dir = tmpdir.ensure_dir('flag')
        config = {
            'erddap': {
                'flag dir': str(tmp_flag_dir),
                'datasetIDs': {
                    'nemo-forecast': ['ubcSSfPointAtkinson10mV17-02'],
                }}}
        checklist = ping_erddap.ping_erddap(parsed_args, config)
        assert not m_logger.debug.called
        assert checklist == {'nowcast-green': []}
