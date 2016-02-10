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

"""Unit tests for Salish Sea NEMO nowcast make_site_page worker.
"""
from unittest.mock import (
    patch,
    Mock,
)

import arrow
import pytest


@pytest.fixture()
def worker_module():
    from nowcast.workers import make_site_page
    return make_site_page


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

    def test_add_run_type_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[0]
        assert args == ('run_type',)
        assert kwargs['choices'] == {
            'nowcast', 'nowcast-green', 'forecast', 'forecast2'}
        assert 'help' in kwargs

    def test_add_page_type_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[1]
        assert args == ('page_type',)
        assert kwargs['choices'] == {'index', 'publish', 'research'}
        assert 'help' in kwargs

    def test_add_run_date_arg(self, m_worker, worker_module, lib_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[2]
        assert args == ('--run-date',)
        assert kwargs['type'] == lib_module.arrow_date
        assert kwargs['default'] == arrow.now('Canada/Pacific').floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            worker_module.make_site_page,
            worker_module.success,
            worker_module.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """
    @pytest.mark.parametrize('run_type, page_type', [
        ('nowcast', 'research'),
        ('nowcast', 'publish'),
        ('nowcast', 'index'),
        ('forecast', 'publish'),
        ('forecast', 'index'),
        ('forecast2', 'publish'),
        ('forecast2', 'index'),
        ('nowcast-green', 'research'),
        ('nowcast-green', 'index'),
    ])
    def test_success_log_info(self, run_type, page_type, worker_module):
        parsed_args = Mock(
            run_type=run_type, page_type=page_type,
            run_date=arrow.get('2016-02-08'))
        with patch.object(worker_module.logger, 'info') as m_logger:
            worker_module.success(parsed_args)
        assert m_logger.called

    @pytest.mark.parametrize('run_type, page_type, expected', [
        ('nowcast', 'research', 'success research'),
        ('nowcast', 'publish', 'success publish'),
        ('nowcast', 'index', 'success index'),
        ('forecast', 'publish', 'success publish'),
        ('forecast', 'index', 'success index'),
        ('forecast2', 'publish', 'success publish'),
        ('forecast2', 'index', 'success index'),
        ('nowcast-green', 'research', 'success research'),
        ('nowcast-green', 'index', 'success index'),
    ])
    def test_success_msg_type(
        self, run_type, page_type, expected, worker_module,
    ):
        parsed_args = Mock(
            run_type=run_type, page_type=page_type,
            run_date=arrow.get('2016-02-08'))
        msg_type = worker_module.success(parsed_args)
        assert msg_type == expected


class TestFailure:
    """Unit tests for failure() function.
    """
    @pytest.mark.parametrize('run_type, page_type', [
        ('nowcast', 'research'),
        ('nowcast', 'publish'),
        ('nowcast', 'index'),
        ('forecast', 'publish'),
        ('forecast', 'index'),
        ('forecast2', 'publish'),
        ('forecast2', 'index'),
        ('nowcast-green', 'research'),
        ('nowcast-green', 'index'),
    ])
    def test_failure_log_error(self, run_type, page_type, worker_module):
        parsed_args = Mock(
            run_type=run_type, page_type=page_type,
            run_date=arrow.get('2016-02-08'))
        with patch.object(worker_module.logger, 'critical') as m_logger:
            worker_module.failure(parsed_args)
        assert m_logger.called

    @pytest.mark.parametrize('run_type, page_type, expected', [
        ('nowcast', 'research', 'failure research'),
        ('nowcast', 'publish', 'failure publish'),
        ('nowcast', 'index', 'failure index'),
        ('forecast', 'publish', 'failure publish'),
        ('forecast', 'index', 'failure index'),
        ('forecast2', 'publish', 'failure publish'),
        ('forecast2', 'index', 'failure index'),
        ('nowcast-green', 'research', 'failure research'),
        ('nowcast-green', 'index', 'failure index'),
    ])
    def test_failure_msg_type(
        self, run_type, page_type, expected, worker_module,
    ):
        parsed_args = Mock(
            run_type=run_type, page_type=page_type,
            run_date=arrow.get('2016-02-08'))
        msg_type = worker_module.failure(parsed_args)
        assert msg_type == expected


class TestMakeSitePage:
    """Unit tests for make_site_page() function.
    """
    @patch.object(worker_module().mako.template, 'Template')
    @patch.object(worker_module(), '_render_index_rst')
    @patch.object(worker_module(), '_render_nowcast_rst')
    def test_nowcast_publish_render_rst_run_date(
        self, m_render_rst, m_render_index, m_tmpl, worker_module,
    ):
        parsed_args = Mock(
            run_type='nowcast', page_type='publish',
            run_date=arrow.get(2015, 2, 8))
        config = {
            'web': {
                'site_repo_url': 'http://example.com/bar',
                'site_nemo_results_path': 'foo',
                'templates_path': 'bar',
                'www_path': 'www',
            }}
        worker_module.make_site_page(parsed_args, config)
        assert m_render_rst.call_args[0][2] == arrow.get(2015, 2, 8)

    @patch.object(worker_module().shutil, 'copy2')
    @patch.object(worker_module().mako.template, 'Template')
    @patch.object(worker_module(), '_render_index_rst')
    @patch.object(worker_module(), '_render_forecast2_rst')
    def test_forecast2_publish_render_rst_run_date(
        self, m_render_rst, m_render_index, m_tmpl, m_copy2,
        worker_module,
    ):
        parsed_args = Mock(
            run_type='forecast2', page_type='publish',
            run_date=arrow.get(2015, 2, 8))
        config = {
            'web': {
                'site_repo_url': 'http://example.com/bar',
                'site_nemo_results_path': 'foo',
                'site_storm_surge_path': 'bar',
                'templates_path': 'baz',
                'www_path': 'www',
            }}
        m_render_rst.return_value = {
            'forecast2 publish': 'publish_08feb15.rst'}
        worker_module.make_site_page(parsed_args, config)
        assert m_render_rst.call_args[0][2] == arrow.get(2015, 2, 8)

    @patch.object(worker_module().mako.template, 'Template')
    @patch.object(worker_module(), '_render_index_rst')
    @patch.object(worker_module(), '_render_nowcast_rst')
    def test_render_index_rst_run_date(
        self, m_render_rst, m_render_index, m_tmpl, worker_module,
    ):
        parsed_args = Mock(
            run_type='nowcast', page_type='index',
            run_date=arrow.get(2015, 2, 8))
        config = {
            'web': {
                'site_repo_url': 'http://example.com/bar',
                'site_nemo_results_path': 'foo',
                'templates_path': 'bar',
                'www_path': 'www',
            }}
        worker_module.make_site_page(parsed_args, config)
        assert m_render_index.call_args[0][2] == arrow.get(2015, 2, 8)
        assert not m_render_rst.called


@patch.object(worker_module(), '_tmpl_to_rst')
def test_render_nowcast_rst_run_date(m_tmpl_to_rst, worker_module):
    config = {
        'web': {
            'domain': 'salishsea.eos.ubc.ca',
            'figures': {'server_path': '/nowcast-sys/figures'},
        }}
    svg_file_roots = {'publish': []}
    worker_module._render_nowcast_rst(
        'tmpl', 'publish', arrow.get(2015, 2, 8), svg_file_roots, 'rst_path',
        config)
    expected = 'rst_path/nowcast/publish_08feb15.rst'
    assert m_tmpl_to_rst.call_args[0][1] == expected


@patch.object(worker_module(), '_tmpl_to_rst')
def test_render_forecast_rst_run_date(m_tmpl_to_rst, worker_module):
    config = {
        'web': {
            'domain': 'salishsea.eos.ubc.ca',
            'figures': {'server_path': '/nowcast-sys/figures'},
        }}
    svg_file_roots = {'publish': []}
    worker_module._render_forecast_rst(
        'tmpl', 'publish', arrow.get(2015, 2, 8), svg_file_roots, 'rst_path',
        config)
    expected = 'rst_path/forecast/publish_09feb15.rst'
    assert m_tmpl_to_rst.call_args[0][1] == expected


@patch.object(worker_module(), '_tmpl_to_rst')
def test_render_forecast2_rst_run_date(m_tmpl_to_rst, worker_module):
    config = {
        'web': {
            'domain': 'salishsea.eos.ubc.ca',
            'figures': {'server_path': '/nowcast-sys/figures'},
        }}
    svg_file_roots = {'publish': []}
    worker_module._render_forecast2_rst(
        'tmpl', 'publish', arrow.get(2015, 2, 8), svg_file_roots, 'rst_path',
        config)
    expected = 'rst_path/forecast2/publish_10feb15.rst'
    assert m_tmpl_to_rst.call_args[0][1] == expected


class TestRenderIndexRst(object):
    """Unit tests for render_index_rst() function.
    """
    @patch.object(worker_module().mako.template, 'Template')
    @patch.object(worker_module(), '_tmpl_to_rst')
    @patch.object(worker_module(), '_exclude_missing_dates')
    def test_nowcast_run_date(
        self, m_exclude_missing_dates, m_tmpl_to_rst, m_tmpl,
        worker_module,
    ):
        config = {
            'web': {
                'templates_path': 'bar',
                'salinity_comparison': {
                    'web_path': 'eoas.ubc.ca/~jieliu/MEOPAR/nowcast',
                    'filesystem_path': '/home/jie/public_html/MEOPAR/nowcast',
                    'fileroot': 'SaliCom',
                }}}
        worker_module._render_index_rst(
            'publish', 'nowcast', arrow.get(2015, 2, 8), 'rst_path', config)
        expected = arrow.get(2015, 2, 9)
        assert m_exclude_missing_dates.call_args_list[0][0][0][-1] == expected

    @patch.object(worker_module().mako.template, 'Template')
    @patch.object(worker_module(), '_tmpl_to_rst')
    @patch.object(worker_module(), '_exclude_missing_dates')
    def test_forecast2_run_date(
        self, m_exclude_missing_dates, m_tmpl_to_rst, m_tmpl,
        worker_module,
    ):
        config = {
            'web': {
                'templates_path': 'bar',
                'salinity_comparison': {
                    'web_path': 'eoas.ubc.ca/~jieliu/MEOPAR/nowcast',
                    'filesystem_path': '/home/jie/public_html/MEOPAR/nowcast',
                    'fileroot': 'SaliCom',
                }}}
        worker_module._render_index_rst(
            'publish', 'forecast2', arrow.get(2015, 2, 8), 'rst_path', config)
        expected = arrow.get(2015, 2, 10)
        assert m_exclude_missing_dates.call_args_list[0][0][0][-1] == expected
