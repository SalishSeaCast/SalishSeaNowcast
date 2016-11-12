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

"""Unit tests for Salish Sea NEMO nowcast make_feeds worker.
"""
from collections import namedtuple
import datetime
import os
from types import SimpleNamespace
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


@pytest.fixture
def config():
    return {
        'ssh': {'tidal predictions': 'tidal_predictions/'},
        'results archive': {
            'forecast': '/results/SalishSea/forecast/',
        },
        'figures': {
            'storage path': '/results/nowcast-sys/figures/',
            'storm surge info portal path': 'storm-surge/',
        },
        'storm surge feeds': {
            'storage path': 'atom',
            'domain': 'salishsea.eos.ubc.ca',
            'feed entry template': 'storm_surge_advisory.mako',
            'feeds': {
                'pmv.xml': {
                    'title': 'SalishSeaCast for Port Metro Vancouver',
                    'city': 'Vancouver',
                    'tide gauge stn': 'Point Atkinson',
                    'tidal predictions':
                        'Point Atkinson_tidal_prediction_'
                        '01-Jan-2013_31-Dec-2020.csv',
        }}},
    }


@patch.object(worker_module(), 'NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    def test_instantiate_worker(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker.call_args
        assert args == ('make_feeds',)
        assert list(kwargs.keys()) == ['description']

    def test_add_run_type_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ('run_type',)
        assert kwargs['choices'] == {'forecast', 'forecast2'}
        assert 'help' in kwargs

    def test_add_run_date_arg(self, m_worker, worker_module):
        worker_module.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['default'] == arrow.now().floor('day')
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


@patch.object(worker_module().logger, 'critical')
class TestFailure:
    """Unit tests for failure() function.
    """
    def test_failure_log_error(self, m_logger, worker_module):
        parsed_args = Mock(
            run_type='forecast', run_date=arrow.get('2015-12-21'))
        worker_module.failure(parsed_args)
        assert m_logger.called

    def test_failure_msg_type(self, m_logger, worker_module):
        parsed_args = Mock(
            run_type='forecast2', run_date=arrow.get('2015-12-21'))
        msg_type = worker_module.failure(parsed_args)
        assert msg_type == 'failure forecast2'


class TestMakeFeeds:
    """Unit tests for make_feeds() function.
    """
    @patch.object(worker_module(), '_generate_feed')
    @patch.object(worker_module(), '_calc_max_ssh_risk')
    def test_checklist(self, m_cmsr, m_gf, worker_module, config):
        parsed_args = SimpleNamespace(
            run_type='forecast', run_date=arrow.get('2016-11-12'))
        m_cmsr.return_value = {'risk_level': None}
        checklist = worker_module.make_feeds(parsed_args, config)
        expected = {
            'forecast 2016-11-12':
                ['/results/nowcast-sys/figures/storm-surge/atom/pmv.xml']}
        assert checklist == expected


class TestGenerateFeed:
    """Unit test for _generate_feed() function.
    """
    @patch.object(worker_module().arrow, 'utcnow')
    def test_generate_feed(self, m_utcnow, worker_module, config):
        m_utcnow.return_value = arrow.get('2016-02-20 11:02:42')
        storm_surge_path = config['figures']['storm surge info portal path']
        atom_path = config['storm surge feeds']['storage path']
        fg = worker_module._generate_feed(
            'pmv.xml', config['storm surge feeds'],
            os.path.join(storm_surge_path, atom_path))
        feed = fg.atom_str(pretty=True).decode('ascii')
        expected = [
            "<?xml version='1.0' encoding='UTF-8'?>",
            '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en-ca">',
            '  <id>tag:salishsea.eos.ubc.ca,2015-12-12:/storm-surge/atom/pmv/'
            '20160220110242</id>',
            '  <title>SalishSeaCast for Port Metro Vancouver</title>',
        ]
        assert feed.splitlines()[:4] == expected
        # The updated element contains a UTC time stamp that we can't
        # mock out easily
        assert feed.splitlines()[4].startswith('  <updated>')
        assert feed.splitlines()[4].endswith('</updated>')
        expected = [
            '  <author>',
            '    <name>Salish Sea MEOPAR Project</name>',
            '    <url>https://salishsea.eos.ubc.ca/</url>',
            '  </author>',
            '  <link href="https://salishsea.eos.ubc.ca/storm-surge/atom/'
            'pmv.xml" rel="self" type="application/atom+xml"/>',
            '  <link href="https://salishsea.eos.ubc.ca/storm-surge/'
            'forecast.html" rel="related" type="text/html"/>',
            '  <generator version="0.4.0">python-feedgen</generator>',
            '  <rights>Copyright 2015-2016, Salish Sea MEOPAR Project Contributors '
            'and The University of British Columbia</rights>',
            '</feed>',
        ]
        assert feed.splitlines()[5:] == expected


@patch.object(worker_module().arrow, 'now')
@patch.object(worker_module(), '_render_entry_content', return_value=b'')
@patch.object(worker_module(), 'FeedEntry')
class TestGenerateFeedEntry:
    """Unit tests for _generate_feed_entry() function.
    """
    def test_title(self, m_fe, m_rec, m_now, worker_module, config):
        storm_surge_path = config['figures']['storm surge info portal path']
        atom_path = config['storm surge feeds']['storage path']
        worker_module._generate_feed_entry(
            'pmv.xml', 'max_ssh_info', config,
            os.path.join(storm_surge_path, atom_path))
        m_fe().title.assert_called_once_with(
            'Storm Surge Alert for Point Atkinson')

    def test_id(self, m_fe, m_rec, m_now, worker_module, config):
        storm_surge_path = config['figures']['storm surge info portal path']
        atom_path = config['storm surge feeds']['storage path']
        m_now.return_value = arrow.get('2015-12-24 15:10:42')
        worker_module._generate_feed_entry(
            'pmv.xml', 'max_ssh_info', config,
            os.path.join(storm_surge_path, atom_path))
        m_fe().id.assert_called_once_with(
            worker_module._build_tag_uri(
                '2015-12-24', 'pmv.sml', m_now(), config['storm surge feeds'],
                os.path.join(storm_surge_path, atom_path)))

    def test_author(self, m_fe, m_rec, m_now, worker_module, config):
        storm_surge_path = config['figures']['storm surge info portal path']
        atom_path = config['storm surge feeds']['storage path']
        worker_module._generate_feed_entry(
            'pmv.xml', 'max_ssh_info', config,
            os.path.join(storm_surge_path, atom_path))
        m_fe().author.assert_called_once_with(
            name='Salish Sea MEOPAR Project',
            uri='https://salishsea.eos.ubc.ca/')

    def test_content(self, m_fe, m_rec, m_now, worker_module, config):
        storm_surge_path = config['figures']['storm surge info portal path']
        atom_path = config['storm surge feeds']['storage path']
        worker_module._generate_feed_entry(
            'pmv.xml', 'max_ssh_info', config,
            os.path.join(storm_surge_path, atom_path))
        m_fe().content.assert_called_once_with(m_rec(), type='html')

    def test_link(self, m_fe, m_rec, m_now, worker_module, config):
        storm_surge_path = config['figures']['storm surge info portal path']
        atom_path = config['storm surge feeds']['storage path']
        worker_module._generate_feed_entry(
            'pmv.xml', 'max_ssh_info', config,
            os.path.join(storm_surge_path, atom_path))
        m_fe().link.assert_called_once_with(
            href='https://salishsea.eos.ubc.ca/storm-surge/forecast.html',
            rel='alternate', type='text/html')


class TestBuildTagURI:
    """Unit test for _build_tag_uri() function.
    """
    def test_build_tag_uri(self, worker_module, config):
        storm_surge_path = config['figures']['storm surge info portal path']
        atom_path = config['storm surge feeds']['storage path']
        tag = worker_module._build_tag_uri(
            '2015-12-12', 'pmv.xml', arrow.get('2015-12-21 09:31:42'),
            config['storm surge feeds'],
            os.path.join(storm_surge_path, atom_path))
        expected = (
            'tag:salishsea.eos.ubc.ca,2015-12-12:'
            '/storm-surge/atom/pmv/20151221093142')
        assert tag == expected


class TestRenderEntryContent:
    """Unit test for _render_entry_content() function.
    """
    @patch.object(worker_module(), '_calc_wind_4h_avg')
    @patch.object(worker_module().mako.template, 'Template')
    @patch.object(worker_module().os.path, 'dirname')
    @patch.object(worker_module().docutils.core, 'publish_parts')
    def test_render_entry_content(
        self, m_pp, m_dirname, m_tmpl, m_cw4a, worker_module, config,
    ):
        max_ssh_info = {
            'max_ssh': 5.0319,
            'max_ssh_time': arrow.get('2015-12-27 15:22:30'),
            'risk_level': 'moderate risk',
        }
        m_cw4a.return_value = {
            'wind_speed_4h_avg': 0.826,
            'wind_dir_4h_avg': 236.97,
        }
        m_dirname.return_value = 'nowcast/workers/'
        content = worker_module._render_entry_content(
            'pmv.xml', max_ssh_info, config)
        m_tmpl.assert_called_once_with(
            filename='nowcast/workers/storm_surge_advisory.mako',
            input_encoding='utf-8')
        assert m_tmpl().render.called
        assert content == m_pp()['body']


class TestCalcMaxSshRisk:
    """Unit test for _calc_max_ssh_risk() function.
    """
    @patch.object(worker_module().stormtools, 'load_tidal_predictions')
    @patch.object(worker_module(), '_calc_max_ssh')
    @patch.object(worker_module().stormtools, 'storm_surge_risk_level')
    def test_calc_max_ssh_risk(
        self, m_ssrl, m_cms, m_ltp, worker_module, config,
    ):
        run_date = arrow.get('2015-12-24').floor('day')
        max_ssh = np.array([5.09])
        max_ssh_time = np.array([datetime.datetime(2015, 12, 25, 19, 59, 42)])
        m_cms.return_value = (max_ssh, max_ssh_time)
        m_ltp.return_value = ('ttide', 'msl')
        max_ssh_info = worker_module._calc_max_ssh_risk(
            'pmv.xml', run_date, 'forecast', config)
        m_ltp.assert_called_once_with(
            'tidal_predictions/Point Atkinson_tidal_prediction_'
            '01-Jan-2013_31-Dec-2020.csv')
        m_cms.assert_called_once_with(
            'pmv.xml', m_ltp()[0], run_date, 'forecast', config)
        m_ssrl.assert_called_once_with('Point Atkinson', max_ssh, m_ltp()[0])
        np.testing.assert_array_equal(
            max_ssh_info['max_ssh'], np.array([5.09]))
        np.testing.assert_array_equal(
            max_ssh_info['max_ssh_time'], max_ssh_time)
        assert max_ssh_info['risk_level'] == m_ssrl()


class TestCalcMaxSsh:
    """Unit test for _calc_max_ssh() function.
    """
    @patch.object(worker_module().nc, 'Dataset')
    @patch.object(worker_module().nc_tools, 'ssh_timeseries_at_point')
    @patch.object(worker_module().nowcast.figures.shared, 'correct_model_ssh')
    def test_calc_max_ssh(
        self, m_cmssh, m_sshtapt, m_ncd, worker_module, config,
    ):
        ssh_ts = namedtuple('ssh_ts', 'ssh, time')
        m_sshtapt.return_value = ssh_ts(
            np.array([1.93]),
            np.array([datetime.datetime(2015, 12, 22, 22, 40, 42)]))
        m_cmssh.return_value = np.array(2)
        max_ssh, max_ssh_time = worker_module._calc_max_ssh(
            'pmv.xml', 'ttide', arrow.get('2015-12-22').floor('day'),
            'forecast', config)
        m_ncd.assert_called_once_with(
            '/results/SalishSea/forecast/22dec15/PointAtkinson.nc')
        m_sshtapt.assert_called_once_with(m_ncd(), 0, 0, datetimes=True)
        np.testing.assert_array_equal(max_ssh, np.array([5.09]))
        np.testing.assert_array_equal(
            max_ssh_time,
            np.array([datetime.datetime(2015, 12, 22, 22, 40, 42)]))
