# Copyright 2013-2015 The Salish Sea MEOPAR contributors
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
from unittest.mock import patch

import arrow
import pytest


@pytest.fixture()
def make_site_page_module():
    from nowcast.workers import make_site_page
    return make_site_page


class TestConfigureArgParser(object):
    """Unit test for configure_argparser() function.
    """
    @patch.object(make_site_page_module().arrow, 'now')
    def test_run_date_default_value(self, m_now, make_site_page_module):
        m_now.return_value = arrow.get(2015, 2, 8, 17, 40, 42)
        parser = make_site_page_module.configure_argparser(
            'make_site_page', 'description from docstring', parents=[])
        assert parser.get_default('run_date') == arrow.get(2015, 2, 8)


class TestMakeSitePage(object):
    """Unit tests for make_site_page() function.
    """
    @patch.object(make_site_page_module().mako.template, 'Template')
    @patch.object(make_site_page_module(), 'render_index_rst')
    @patch.object(make_site_page_module(), 'render_nowcast_rst')
    def test_nowcast_publish_render_rst_run_date(
        self, m_render_rst, m_render_index, m_tmpl, make_site_page_module,
    ):
        config = {
            'web': {
                'site_repo_url': 'http://example.com/bar',
                'site_nemo_results_path': 'foo',
                'templates_path': 'bar',
                'www_path': 'www',
            }}
        make_site_page_module.make_site_page(
            'nowcast', 'publish', arrow.get(2015, 2, 8), config)
        assert m_render_rst.call_args[0][2] == arrow.get(2015, 2, 8)

    @patch.object(make_site_page_module().shutil, 'copy2')
    @patch.object(make_site_page_module().mako.template, 'Template')
    @patch.object(make_site_page_module(), 'render_index_rst')
    @patch.object(make_site_page_module(), 'render_forecast2_rst')
    def test_forecast2_publish_render_rst_run_date(
        self, m_render_rst, m_render_index, m_tmpl, m_copy2,
        make_site_page_module,
    ):
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
        make_site_page_module.make_site_page(
            'forecast2', 'publish', arrow.get(2015, 2, 8), config)
        assert m_render_rst.call_args[0][2] == arrow.get(2015, 2, 8)

    @patch.object(make_site_page_module().mako.template, 'Template')
    @patch.object(make_site_page_module(), 'render_index_rst')
    @patch.object(make_site_page_module(), 'render_nowcast_rst')
    def test_render_index_rst_run_date(
        self, m_render_rst, m_render_index, m_tmpl, make_site_page_module,
    ):
        config = {
            'web': {
                'site_repo_url': 'http://example.com/bar',
                'site_nemo_results_path': 'foo',
                'templates_path': 'bar',
                'www_path': 'www',
            }}
        make_site_page_module.make_site_page(
            'nowcast', 'index', arrow.get(2015, 2, 8), config)
        assert m_render_index.call_args[0][2] == arrow.get(2015, 2, 8)
        assert not m_render_rst.called


@patch.object(make_site_page_module(), 'tmpl_to_rst')
def test_render_nowcast_rst_run_date(m_tmpl_to_rst, make_site_page_module):
    config = {
        'web': {
            'domain': 'salishsea.eos.ubc.ca',
            'figures': {'server_path': '/nowcast-sys/figures'},
        }}
    svg_file_roots = {'publish': []}
    make_site_page_module.render_nowcast_rst(
        'tmpl', 'publish', arrow.get(2015, 2, 8), svg_file_roots, 'rst_path',
        config)
    expected = 'rst_path/nowcast/publish_08feb15.rst'
    assert m_tmpl_to_rst.call_args[0][1] == expected


@patch.object(make_site_page_module(), 'tmpl_to_rst')
def test_render_forecast_rst_run_date(m_tmpl_to_rst, make_site_page_module):
    config = {
        'web': {
            'domain': 'salishsea.eos.ubc.ca',
            'figures': {'server_path': '/nowcast-sys/figures'},
        }}
    svg_file_roots = {'publish': []}
    make_site_page_module.render_forecast_rst(
        'tmpl', 'publish', arrow.get(2015, 2, 8), svg_file_roots, 'rst_path',
        config)
    expected = 'rst_path/forecast/publish_09feb15.rst'
    assert m_tmpl_to_rst.call_args[0][1] == expected


@patch.object(make_site_page_module(), 'tmpl_to_rst')
def test_render_forecast2_rst_run_date(m_tmpl_to_rst, make_site_page_module):
    config = {
        'web': {
            'domain': 'salishsea.eos.ubc.ca',
            'figures': {'server_path': '/nowcast-sys/figures'},
        }}
    svg_file_roots = {'publish': []}
    make_site_page_module.render_forecast2_rst(
        'tmpl', 'publish', arrow.get(2015, 2, 8), svg_file_roots, 'rst_path',
        config)
    expected = 'rst_path/forecast2/publish_10feb15.rst'
    assert m_tmpl_to_rst.call_args[0][1] == expected


class TestRenderIndexRst(object):
    """Unit tests for render_index_rst() function.
    """
    @patch.object(make_site_page_module().mako.template, 'Template')
    @patch.object(make_site_page_module(), 'tmpl_to_rst')
    @patch.object(make_site_page_module(), 'exclude_missing_dates')
    def test_nowcast_run_date(
        self, m_exclude_missing_dates, m_tmpl_to_rst, m_tmpl,
        make_site_page_module,
    ):
        config = {
            'web': {
                'templates_path': 'bar',
                'salinity_comparison': {
                    'web_path': 'eoas.ubc.ca/~jieliu/MEOPAR/nowcast',
                    'filesystem_path': '/home/jie/public_html/MEOPAR/nowcast',
                    'fileroot': 'SaliCom',
                }}}
        make_site_page_module.render_index_rst(
            'publish', 'nowcast', arrow.get(2015, 2, 8), 'rst_path', config)
        expected = arrow.get(2015, 2, 9)
        assert m_exclude_missing_dates.call_args_list[0][0][0][-1] == expected

    @patch.object(make_site_page_module().mako.template, 'Template')
    @patch.object(make_site_page_module(), 'tmpl_to_rst')
    @patch.object(make_site_page_module(), 'exclude_missing_dates')
    def test_forecast2_run_date(
        self, m_exclude_missing_dates, m_tmpl_to_rst, m_tmpl,
        make_site_page_module,
    ):
        config = {
            'web': {
                'templates_path': 'bar',
                'salinity_comparison': {
                    'web_path': 'eoas.ubc.ca/~jieliu/MEOPAR/nowcast',
                    'filesystem_path': '/home/jie/public_html/MEOPAR/nowcast',
                    'fileroot': 'SaliCom',
                }}}
        make_site_page_module.render_index_rst(
            'publish', 'forecast2', arrow.get(2015, 2, 8), 'rst_path', config)
        expected = arrow.get(2015, 2, 10)
        assert m_exclude_missing_dates.call_args_list[0][0][0][-1] == expected
