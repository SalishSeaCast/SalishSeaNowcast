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

"""Unit tests for Salish Sea NEMO nowcast make_feeds worker.
"""
import datetime
from unittest.mock import (
    Mock,
    patch,
)

import arrow
import numpy as np
import pytest


@pytest.fixture
def worker_module():
    from nowcast.workers import make_feeds
    return make_feeds


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
        assert kwargs['choices'] == {'forecast', 'forecast2'}
        assert 'help' in kwargs

    def test_add_run_date_arg(self, m_worker, worker_module, lib_module):
        worker_module.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[1]
        assert args == ('--run-date',)
        assert kwargs['type'] == lib_module.arrow_date
        assert kwargs['default'] == arrow.now('Canada/Pacific').floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            worker_module.make_feeds,
            worker_module.success,
            worker_module.failure,
        )


class TestSuccess:
    """Unit tests for success() function.
    """
    def test_success_log_info(self, worker_module):
        parsed_args = Mock(
            run_type='forecast', run_date=arrow.get('2015-12-21'))
        with patch.object(worker_module.logger, 'info') as m_logger:
            worker_module.success(parsed_args)
        assert m_logger.called

    def test_success_msg_type(self, worker_module):
        parsed_args = Mock(
            run_type='forecast2', run_date=arrow.get('2015-12-21'))
        msg_type = worker_module.success(parsed_args)
        assert msg_type == 'success forecast2'


class TestFailure:
    """Unit tests for failure() function.
    """
    def test_failure_log_error(self, worker_module):
        parsed_args = Mock(
            run_type='forecast', run_date=arrow.get('2015-12-21'))
        with patch.object(worker_module.logger, 'critical') as m_logger:
            worker_module.failure(parsed_args)
        assert m_logger.called

    def test_failure_msg_type(self, worker_module):
        parsed_args = Mock(
            run_type='forecast2', run_date=arrow.get('2015-12-21'))
        msg_type = worker_module.failure(parsed_args)
        assert msg_type == 'failure forecast2'


class TestGenerateFeed:
    """Unit test for _generate_feed() function.
    """
    @patch.object(worker_module().arrow, 'utcnow')
    def test_generate_feed(self, m_utcnow, worker_module):
        web_config = {
            'domain': 'salishsea.eos.ubc.ca',
            'atom_path': 'storm-surge/atom',
            'feeds': {'pmv.xml': {'title': 'PMV Feed'}},
        }
        m_utcnow.return_value = arrow.get(2015, 12, 21, 17, 54, 42)
        fg = worker_module._generate_feed('pmv.xml', web_config)
        feed = fg.atom_str(pretty=True).decode('ascii')
        expected = [
            "<?xml version='1.0' encoding='UTF-8'?>",
            '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en-ca">',
            '  <id>tag:salishsea.eos.ubc.ca,2015-12-12:/storm-surge/atom/pmv/20151221175442</id>',
            '  <title>PMV Feed</title>',
        ]
        assert feed.splitlines()[:4] == expected
        # The updated element contains a UTC time stamp that we can't
        # mock out easily
        assert feed.splitlines()[4].startswith('  <updated>')
        assert feed.splitlines()[4].endswith('</updated>')
        expected = [
            '  <author>',
            '    <name>Salish Sea MEOPAR Project</name>',
            '    <url>http://salishsea.eos.ubc.ca/</url>',
            '  </author>',
            '  <link href="http://salishsea.eos.ubc.ca/storm-surge/atom/pmv.xml" '
            'rel="self" type="application/atom+xml"/>',
            '  <link href="http://salishsea.eos.ubc.ca/storm-surge/forecast.html" '
            'rel="related" type="text/html"/>',
            '  <generator version="0.3.2">python-feedgen</generator>',
            '  <rights>Copyright 2015, Salish Sea MEOPAR Project Contributors and The '
            'University of British Columbia</rights>',
            '</feed>',
        ]
        assert feed.splitlines()[5:] == expected


class TestBuildTagURI:
    """Unit test for _build_tag_uri() function.
    """
    def test_build_tag_uri(self, worker_module):
        web_config = {
            'domain': 'salishsea.eos.ubc.ca',
            'atom_path': 'storm-surge/atom',
        }
        tag = worker_module._build_tag_uri(
            '2015-12-12', 'pmv.xml', arrow.get(2015, 12, 21, 9, 31, 42),
            web_config)
        expected = (
            'tag:salishsea.eos.ubc.ca,2015-12-12:'
            '/storm-surge/atom/pmv/20151221093142')
        assert tag == expected


class TestCalcMaxSsh:
    """Unit test for _calc_max_ssh() function.
    """
    @patch.object(worker_module().nc, 'Dataset')
    @patch.object(worker_module().nc_tools, 'ssh_timeseries')
    @patch.object(worker_module().figures, 'get_tides', return_value={})
    @patch.object(worker_module().figures, 'correct_model_ssh')
    def test_calc_max_ssh(self, m_cmssh, m_gt, m_ssht, m_ncd, worker_module):
        config = {
            'ssh': {
                'tidal_predictions': '/nowcast/tidal_predictions/',
            },
            'run': {
                'results archive': {
                    'forecast': '/results/SalishSea/forecast/',
                },
            },
            'web': {
                'feeds': {'pmv.xml': {
                    'title': 'PMV Feed',
                    'tide_gauge_stn': 'Point Atkinson',
                }},
            },
        }
        m_ssht.return_value = (
            np.array([1.93]),
            np.array([datetime.datetime(2015, 12, 22, 22, 40, 42)]))
        m_cmssh.return_value = np.array(2)
        max_ssh, max_ssh_time = worker_module._calc_max_ssh(
            'pmv.xml', arrow.get(2015, 12, 22, 0, 0, 0), 'forecast', config)
        m_ncd.assert_called_once_with(
            '/results/SalishSea/forecast/22dec15/PointAtkinson.nc')
        m_ssht.assert_called_once_with(m_ncd(), datetimes=True)
        m_gt.assert_called_once_with(
            'Point Atkinson', '/nowcast/tidal_predictions/')
        np.testing.assert_array_equal(max_ssh, np.array([5.09]))
        np.testing.assert_array_equal(
            max_ssh_time,
            np.array([datetime.datetime(2015, 12, 22, 22, 40, 42)]))
