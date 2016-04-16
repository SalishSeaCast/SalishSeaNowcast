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

"""Unit tests for Salish Sea NEMO nowcast rsync_to_web worker.
"""
from unittest.mock import (
    call,
    Mock,
    patch,
)

import pytest
import subprocess


@pytest.fixture
def worker_module():
    from nowcast.workers import rsync_to_web
    return rsync_to_web


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

    def test_run_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            worker_module.rsync_to_web,
            worker_module.success,
            worker_module.failure,
        )


@patch.object(worker_module().logger, 'info')
class TestSuccess:
    """Unit tests for success() function.
    """
    def test_success_log_info(self, m_logger, worker_module):
        parsed_args = Mock()
        worker_module.success(parsed_args)
        assert m_logger.called

    def test_success_msg_type(self, m_logger, worker_module):
        parsed_args = Mock()
        msg_type = worker_module.success(parsed_args)
        assert msg_type == 'success'


@patch.object(worker_module().logger, 'critical')
class TestFailure:
    """Unit tests for failure() function.
    """
    def test_failure_log_error(self, m_logger, worker_module):
        parsed_args = Mock()
        worker_module.failure(parsed_args)
        assert m_logger.called

    def test_failure_msg_type(self, m_logger, worker_module):
        parsed_args = Mock()
        msg_type = worker_module.failure(parsed_args)
        assert msg_type == 'failure'


@patch.object(worker_module().logger, 'error')
@patch.object(worker_module().logger, 'debug')
@patch.object(worker_module().logger, 'info')
@patch.object(worker_module().lib, 'run_in_subprocess')
class TestSphinxBuild:
    """Unit tests for sphinx_build() function.
    """
    def test_rsync_to_web(self, m_ris, m_info, m_debug, m_error, worker_module):
        parsed_args = Mock()
        config = {
            'web': {
                'site_repo_url': 'https://bitbucket.org//salishsea-site',
                'server_path': '/var/www/html',
                'www_path': 'www',
                'www_site': 'www/site',
                'storm_surge_path': 'storm-surge',
                'nemo_results_path': 'nemo/results',
            }}
        checklist = worker_module.rsync_to_web(parsed_args, config)
        assert m_ris.call_args_list[0] == call(
            ['rsync', '-rRv',
             'www/salishsea-site/site/_build/html/./storm-surge/',
             '/var/www/html'],
            m_debug, m_error)
        assert m_ris.call_args_list[1] == call(
            ['rsync', '-rRv',
             'www/salishsea-site/site/_build/html/./nemo/results/',
             '/var/www/html'],
            m_debug, m_error)
        assert m_info.called
        assert checklist == {'storm-surge': True, 'nemo/results': True}
