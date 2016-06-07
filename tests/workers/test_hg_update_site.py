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

"""Unit tests for Salish Sea NEMO nowcast hg_update_site worker.
"""
import shlex
from unittest.mock import (
    Mock,
    patch,
)

import pytest

from nowcast.workers import hg_update_site


@patch('nowcast.workers.hg_update_site.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    @patch('nowcast.workers.hg_update_site.worker_name')
    def test_instantiate_worker(self, m_name, m_worker):
        hg_update_site.main()
        args, kwargs = m_worker.call_args
        assert args == (m_name,)
        assert list(kwargs.keys()) == ['description']

    def test_run_worker(self, m_worker):
        hg_update_site.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            hg_update_site.hg_update_site,
            hg_update_site.success,
            hg_update_site.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """
    def test_success_log_info(self):
        parsed_args = Mock()
        with patch('nowcast.workers.hg_update_site.logger') as m_logger:
            hg_update_site.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self):
        parsed_args = Mock()
        with patch('nowcast.workers.hg_update_site.logger'):
            msg_typ = hg_update_site.success(parsed_args)
        assert msg_typ == 'success'


class TestFailure:
    """Unit tests for failure() function.
    """
    def test_failure_log_critical(self):
        parsed_args = Mock()
        with patch('nowcast.workers.hg_update_site.logger') as m_logger:
            hg_update_site.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self):
        parsed_args = Mock()
        with patch('nowcast.workers.hg_update_site.logger'):
            msg_typ = hg_update_site.failure(parsed_args)
        assert msg_typ == 'failure'


class TestHgUpdateSite:
    """Unit tests for hg_update_site() function.
    """
    @patch('nowcast.workers.hg_update_site.logger')
    @patch('nowcast.workers.hg_update_site.lib.run_in_subprocess')
    def test_hg_update(self, m_lib_ris, m_logger, tmpdir):
        parsed_args = Mock()
        tmp_www_path = tmpdir.ensure_dir('www')
        tmp_repo_path = tmp_www_path.ensure_dir('salishsea-site')
        config = {
            'web': {
                'site_repo_url':
                    'https://bitbucket.org/salishsea/salishsea-site',
                'www_path': str(tmp_www_path),
            }}
        checklist = hg_update_site.hg_update_site(parsed_args, config)
        expected = shlex.split(
            'hg pull --update --cwd {}'.format(tmp_repo_path))
        m_lib_ris.assert_called_once_with(
            expected, m_logger.debug, m_logger.error)
        assert checklist == str(tmp_repo_path)

    @patch('nowcast.workers.hg_update_site.logger')
    @patch('nowcast.workers.hg_update_site.lib.run_in_subprocess')
    def test_hg_clone(self, m_lib_ris, m_logger, tmpdir):
        parsed_args = Mock()
        tmp_www_path = tmpdir.ensure_dir('www')
        config = {
            'web': {
                'site_repo_url':
                    'https://bitbucket.org/salishsea/salishsea-site',
                'www_path': str(tmp_www_path),
            }}
        checklist = hg_update_site.hg_update_site(parsed_args, config)
        expected = shlex.split(
            'hg clone {repo_url} {repo}'
            .format(
                repo_url=config['web']['site_repo_url'],
                repo=tmp_www_path.join('salishsea-site')))
        m_lib_ris.assert_called_once_with(
            expected, m_logger.debug, m_logger.error)
        assert checklist == str(tmp_www_path.join('salishsea-site'))
