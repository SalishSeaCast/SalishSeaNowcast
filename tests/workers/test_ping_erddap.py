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

"""Unit tests for Salish Sea NEMO nowcast ping_erddap worker.
"""
from unittest.mock import (
    Mock,
    patch,
)

import pytest


@pytest.fixture
def worker_module(scope='module'):
    from nowcast.workers import ping_erddap
    return ping_erddap


@patch.object(worker_module(), 'NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    @patch.object(worker_module(), 'worker_name')
    def test_instantiate_worker(self, m_name, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker.call_args
        assert args == (m_name,)
        assert list(kwargs.keys()) == ['description']

    def test_add_dataset_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[0]
        assert args == ('dataset',)
        assert kwargs['choices'] == {
            'nowcast', 'nowcast-green', 'forecast', 'forecast2',
            'download_weather'}
        assert 'help' in kwargs

    def test_run_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            worker_module.ping_erddap,
            worker_module.success,
            worker_module.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """
    @pytest.mark.parametrize('dataset', [
        'nowcast',
        'forecast',
        'forecast2',
        'nowcast-green',
        'download_weather',
    ])
    def test_success_log_info(self, dataset, worker_module):
        parsed_args = Mock(dataset=dataset)
        with patch.object(worker_module.logger, 'info') as m_logger:
            worker_module.success(parsed_args)
        assert m_logger.called

    @pytest.mark.parametrize('dataset, expected', [
        ('nowcast', 'success nowcast'),
        ('forecast', 'success forecast'),
        ('forecast2', 'success forecast2'),
        ('nowcast-green', 'success nowcast-green'),
        ('download_weather', 'success download_weather'),
    ])
    def test_success_msg_type(self, dataset, expected, worker_module):
        parsed_args = Mock(dataset=dataset)
        msg_type = worker_module.success(parsed_args)
        assert msg_type == expected


class TestFailure:
    """Unit tests for failure() function.
    """
    @pytest.mark.parametrize('dataset', [
        'nowcast',
        'forecast',
        'forecast2',
        'nowcast-green',
        'download_weather',
    ])
    def test_failure_log_error(self, dataset, worker_module):
        parsed_args = Mock(dataset=dataset)
        with patch.object(worker_module.logger, 'critical') as m_logger:
            worker_module.failure(parsed_args)
        assert m_logger.called

    @pytest.mark.parametrize('dataset, expected', [
        ('nowcast', 'failure nowcast'),
        ('forecast', 'failure forecast'),
        ('forecast2', 'failure forecast2'),
        ('nowcast-green', 'failure nowcast-green'),
        ('download_weather', 'failure download_weather'),
    ])
    def test_failure_msg_type(self, dataset, expected, worker_module):
        parsed_args = Mock(dataset=dataset)
        msg_type = worker_module.failure(parsed_args)
        assert msg_type == expected


class TestPingErddap:
    """Unit tests for ping_erddap() function.
    """
    @pytest.mark.parametrize('dataset', [
        'nowcast',
        'forecast',
        'forecast2',
        'nowcast-green',
        'download_weather',
    ])
    def test_ping_erddap(self, dataset, worker_module, tmpdir):
        parsed_args = Mock(dataset=dataset)
        tmp_flag_dir = tmpdir.ensure_dir('flag')
        config = {
            'erddap': {
                'flag_dir': str(tmp_flag_dir),
                'datasetIDs': {
                    'download_weather':
                        ['ubcSSaSurfaceAtmosphereFieldsV1'],
                    'nowcast':
                        ['ubcSSn3DTracerFields1hV1', 'ubcSSn3DuVelocity1hV1'],
                    'forecast':
                        ['ubcSSf3DTracerFields1hV1', 'ubcSSf3DuVelocity1hV1'],
                    'forecast2': [
                        'ubcSSf23DTracerFields1hV1', 'ubcSSf23DuVelocity1hV1'],
                    'nowcast-green': [
                        'ubcSSng3DTracerFields1hV1', 'ubcSSng3DuVelocity1hV1'],
                }}}
        with patch.object(worker_module, 'logger') as m_logger:
            checklist = worker_module.ping_erddap(parsed_args, config)
            dataset_ids = config['erddap']['datasetIDs'][dataset]
        for i, dataset_id in enumerate(dataset_ids):
            assert tmp_flag_dir.join(dataset_id).exists
            expected = '{} touched'.format(tmp_flag_dir.join(dataset_id))
            m_logger.debug.calls[i] == expected
        expected = {dataset: config['erddap']['datasetIDs'][dataset]}
        assert checklist == expected

    def test_no_datasetID(self, worker_module, tmpdir):
        parsed_args = Mock(dataset='nowcast-green')
        tmp_flag_dir = tmpdir.ensure_dir('flag')
        config = {
            'erddap': {
                'flag_dir': str(tmp_flag_dir),
                'datasetIDs': {
                    'nowcast':
                        ['ubcSSn3DTracerFields1hV1', 'ubcSSn3DuVelocity1hV1'],
                    'forecast':
                        ['ubcSSf3DTracerFields1hV1', 'ubcSSf3DuVelocity1hV1'],
                    'forecast2': [
                        'ubcSSf23DTracerFields1hV1', 'ubcSSf23DuVelocity1hV1'],
                }}}
        with patch.object(worker_module, 'logger') as m_logger:
            checklist = worker_module.ping_erddap(parsed_args, config)
        assert not m_logger.debug.called
        assert checklist == {'nowcast-green': []}
