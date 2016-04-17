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

"""Unit tests for Salish Sea NEMO nowcast sphinx_build worker.
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
    from nowcast.workers import sphinx_build
    return sphinx_build


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

    def test_add_clean_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[0]
        assert args == ('--clean',)
        assert kwargs['action'] == 'store_true'
        assert 'help' in kwargs

    def test_run_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            worker_module.sphinx_build,
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


@patch.object(worker_module().logger, 'debug')
class TestSphinxBuild:
    """Unit tests for sphinx_build() function.
    """
    @patch.object(worker_module().lib, 'run_in_subprocess')
    @patch.object(worker_module().subprocess, 'run')
    def test_clean_build(self, m_run, m_ris, m_debug, worker_module):
        parsed_args = Mock(clean=True)
        config = {
            'web': {
                'site_repo_url': 'https://bitbucket.org/salishsea-site',
                'www_path': 'www',
            }}
        checklist = worker_module.sphinx_build(parsed_args, config)
        assert m_debug.call_count == 2
        assert m_run.call_args_list[0] == call(
            ['rm', '-rf', 'www/salishsea-site/site/_build'], check=True)
        assert checklist == {'www/salishsea-site/site/_build/html': True}

    @patch.object(worker_module().logger, 'error')
    @patch.object(worker_module().subprocess, 'run')
    def test_clean_build_failure(self, m_run, m_error, m_debug, worker_module):
        from nowcast.nowcast_worker import WorkerError
        parsed_args = Mock(clean=True)
        config = {
            'web': {
                'site_repo_url': 'https://bitbucket.org/salishsea-site',
                'www_path': 'www',
            }}
        m_run.side_effect = subprocess.CalledProcessError(2, 'cmd')
        with pytest.raises(WorkerError):
            worker_module.sphinx_build(parsed_args, config)
        assert m_error.called

    @patch.object(worker_module().logger, 'error')
    @patch.object(worker_module().logger, 'info')
    @patch.object(worker_module().lib, 'run_in_subprocess')
    def test_sphinx_build(self, m_ris, m_info, m_error, m_debug, worker_module):
        from nowcast.nowcast_worker import WorkerError
        parsed_args = Mock(clean=False)
        config = {
            'web': {
                'site_repo_url': 'https://bitbucket.org/salishsea-site',
                'www_path': 'www',
            }}
        checklist = worker_module.sphinx_build(parsed_args, config)
        assert m_debug.called
        m_ris.assert_called_once_with(
            ['sphinx-build',
             '-b', 'html',
             '-d', 'www/salishsea-site/site/_build/doctrees',
             '-E',
             'www/salishsea-site/site',
             'www/salishsea-site/site/_build/html'],
            m_debug, m_error,
        )
        assert m_info.called
        assert checklist == {'www/salishsea-site/site/_build/html': True}
