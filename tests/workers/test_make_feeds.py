#  Copyright 2013-2021 The Salish Sea MEOPAR contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Unit tests for Salish Sea NEMO nowcast make_feeds worker.
"""
import datetime
import os
import textwrap
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import numpy as np
import pytest
from nemo_nowcast import WorkerError

from nowcast.workers import make_feeds


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                ssh:
                  tidal predictions: tidal_predictions/
                results archive:
                  forecast: /results/SalishSea/forecast/
                figures:
                  storage path: /results/nowcast-sys/figures/
                  storm surge info portal path: storm-surge/
                storm surge feeds:
                  storage path: atom
                  domain: salishsea.eos.ubc.ca
                  feed entry template: storm_surge_advisory.mako
                  feeds:
                    pmv.xml:
                      title: SalishSeaCast for Port Metro Vancouver
                      city: Vancouver
                      tide gauge stn: Point Atkinson
                      tidal predictions: Point Atkinson_tidal_prediction_01-Jan-2013_31-Dec-2020.csv
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.make_feeds.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_feeds.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_feeds",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_feeds.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_feeds.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"forecast", "forecast2"}
        assert "help" in kwargs

    def test_add_run_date_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_feeds.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_feeds.main()
        args, kwargs = m_worker().run.call_args
        assert args == (make_feeds.make_feeds, make_feeds.success, make_feeds.failure)


@pytest.mark.parametrize("run_type", ["forecast", "forecast2"])
@patch("nowcast.workers.make_feeds.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2015-12-21")
        )
        msg_type = make_feeds.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["forecast", "forecast2"])
@patch("nowcast.workers.make_feeds.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2015-12-21")
        )
        msg_type = make_feeds.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {run_type}"


class TestMakeFeeds:
    """Unit test for make_feeds() function."""

    @patch("nowcast.workers.make_feeds._generate_feed", autospec=True)
    @patch("nowcast.workers.make_feeds._calc_max_ssh_risk", autospec=True)
    def test_checklist(self, m_cmsr, m_gf, config):
        parsed_args = SimpleNamespace(
            run_type="forecast", run_date=arrow.get("2016-11-12")
        )
        m_cmsr.return_value = {"risk_level": None}
        checklist = make_feeds.make_feeds(parsed_args, config)
        expected = {
            "forecast 2016-11-12": [
                "/results/nowcast-sys/figures/storm-surge/atom/pmv.xml"
            ]
        }
        assert checklist == expected


class TestGenerateFeed:
    """Unit test for _generate_feed() function."""

    @patch("nowcast.workers.make_feeds.arrow.utcnow", autospec=True)
    def test_generate_feed(self, m_utcnow, config):
        m_utcnow.return_value = arrow.get("2016-02-20 11:02:42")
        storm_surge_path = config["figures"]["storm surge info portal path"]
        atom_path = config["storm surge feeds"]["storage path"]
        fg = make_feeds._generate_feed(
            "pmv.xml",
            config["storm surge feeds"],
            os.path.join(storm_surge_path, atom_path),
        )
        feed = fg.atom_str(pretty=True).decode("ascii")
        expected = [
            "<?xml version='1.0' encoding='UTF-8'?>",
            '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en-ca">',
            "  <id>tag:salishsea.eos.ubc.ca,2015-12-12:/storm-surge/atom/pmv/"
            "20160220110242</id>",
            "  <title>SalishSeaCast for Port Metro Vancouver</title>",
        ]
        assert feed.splitlines()[:4] == expected
        # The updated element contains a UTC time stamp that we can't
        # mock out easily
        assert feed.splitlines()[4].startswith("  <updated>")
        assert feed.splitlines()[4].endswith("</updated>")
        expected = [
            "  <author>",
            "    <name>Salish Sea MEOPAR Project</name>",
            "    <uri>https://salishsea.eos.ubc.ca/</uri>",
            "  </author>",
            '  <link href="https://salishsea.eos.ubc.ca/storm-surge/atom/'
            'pmv.xml" rel="self" type="application/atom+xml"/>',
            '  <link href="https://salishsea.eos.ubc.ca/storm-surge/'
            'forecast.html" rel="related" type="text/html"/>',
            '  <generator uri="https://lkiesow.github.io/python-feedgen" '
            'version="0.9.0">python-feedgen</generator>',
            "  <rights>Copyright 2015-2016, Salish Sea MEOPAR Project Contributors "
            "and The University of British Columbia</rights>",
            "</feed>",
        ]
        assert feed.splitlines()[5:] == expected


@patch("nowcast.workers.make_feeds.arrow.now", autospec=True)
@patch("nowcast.workers.make_feeds._render_entry_content", return_value=b"", spec=True)
@patch("nowcast.workers.make_feeds.FeedEntry", autospec=True)
class TestGenerateFeedEntry:
    """Unit tests for _generate_feed_entry() function."""

    def test_title(self, m_fe, m_rec, m_now, config):
        storm_surge_path = config["figures"]["storm surge info portal path"]
        atom_path = config["storm surge feeds"]["storage path"]
        make_feeds._generate_feed_entry(
            "pmv.xml", "max_ssh_info", config, os.path.join(storm_surge_path, atom_path)
        )
        m_fe().title.assert_called_once_with("Storm Surge Alert for Point Atkinson")

    def test_id(self, m_fe, m_rec, m_now, config):
        storm_surge_path = config["figures"]["storm surge info portal path"]
        atom_path = config["storm surge feeds"]["storage path"]
        m_now.return_value = arrow.get("2015-12-24 15:10:42")
        make_feeds._generate_feed_entry(
            "pmv.xml", "max_ssh_info", config, os.path.join(storm_surge_path, atom_path)
        )
        m_fe().id.assert_called_once_with(
            make_feeds._build_tag_uri(
                "2015-12-24",
                "pmv.sml",
                m_now(),
                config["storm surge feeds"],
                os.path.join(storm_surge_path, atom_path),
            )
        )

    def test_author(self, m_fe, m_rec, m_now, config):
        storm_surge_path = config["figures"]["storm surge info portal path"]
        atom_path = config["storm surge feeds"]["storage path"]
        make_feeds._generate_feed_entry(
            "pmv.xml", "max_ssh_info", config, os.path.join(storm_surge_path, atom_path)
        )
        m_fe().author.assert_called_once_with(
            name="Salish Sea MEOPAR Project", uri="https://salishsea.eos.ubc.ca/"
        )

    def test_content(self, m_fe, m_rec, m_now, config):
        storm_surge_path = config["figures"]["storm surge info portal path"]
        atom_path = config["storm surge feeds"]["storage path"]
        make_feeds._generate_feed_entry(
            "pmv.xml", "max_ssh_info", config, os.path.join(storm_surge_path, atom_path)
        )
        m_fe().content.assert_called_once_with(m_rec(), type="html")

    def test_link(self, m_fe, m_rec, m_now, config):
        storm_surge_path = config["figures"]["storm surge info portal path"]
        atom_path = config["storm surge feeds"]["storage path"]
        make_feeds._generate_feed_entry(
            "pmv.xml", "max_ssh_info", config, os.path.join(storm_surge_path, atom_path)
        )
        m_fe().link.assert_called_once_with(
            href="https://salishsea.eos.ubc.ca/storm-surge/forecast.html",
            rel="alternate",
            type="text/html",
        )


class TestBuildTagURI:
    """Unit test for _build_tag_uri() function."""

    def test_build_tag_uri(self, config):
        storm_surge_path = config["figures"]["storm surge info portal path"]
        atom_path = config["storm surge feeds"]["storage path"]
        tag = make_feeds._build_tag_uri(
            "2015-12-12",
            "pmv.xml",
            arrow.get("2015-12-21 09:31:42"),
            config["storm surge feeds"],
            os.path.join(storm_surge_path, atom_path),
        )
        expected = (
            "tag:salishsea.eos.ubc.ca,2015-12-12:"
            "/storm-surge/atom/pmv/20151221093142"
        )
        assert tag == expected


class TestRenderEntryContent:
    """Unit test for _render_entry_content() function."""

    @patch("nowcast.workers.make_feeds._calc_wind_4h_avg", autospec=True)
    @patch("nowcast.workers.make_feeds.mako.template.Template", autospec=True)
    @patch("nowcast.workers.make_feeds.os.path.dirname", autospec=True)
    @patch("nowcast.workers.make_feeds.docutils.core.publish_parts", spec=True)
    def test_render_entry_content(self, m_pp, m_dirname, m_tmpl, m_cw4a, config):
        max_ssh_info = {
            "max_ssh": 5.0319,
            "max_ssh_time": arrow.get("2015-12-27 15:22:30"),
            "risk_level": "moderate risk",
        }
        m_cw4a.return_value = {"wind_speed_4h_avg": 0.826, "wind_dir_4h_avg": 236.97}
        m_dirname.return_value = "nowcast/workers/"
        content = make_feeds._render_entry_content("pmv.xml", max_ssh_info, config)
        m_tmpl.assert_called_once_with(
            filename="nowcast/workers/storm_surge_advisory.mako", input_encoding="utf-8"
        )
        assert m_tmpl().render.called
        assert content == m_pp()["body"]


class TestCalcMaxSshRisk:
    """Unit test for _calc_max_ssh_risk() function."""

    @patch("nowcast.workers.make_feeds.stormtools.load_tidal_predictions", spec=True)
    @patch("nowcast.workers.make_feeds._calc_max_ssh", autospec=True)
    @patch("nowcast.workers.make_feeds.stormtools.storm_surge_risk_level", spec=True)
    def test_calc_max_ssh_risk(self, m_ssrl, m_cms, m_ltp, config):
        run_date = arrow.get("2015-12-24").floor("day")
        max_ssh = np.array([5.09])
        max_ssh_time = np.array([datetime.datetime(2015, 12, 25, 19, 59, 42)])
        m_cms.return_value = (max_ssh, max_ssh_time)
        m_ltp.return_value = ("ttide", "msl")
        max_ssh_info = make_feeds._calc_max_ssh_risk(
            "pmv.xml", run_date, "forecast", config
        )
        m_ltp.assert_called_once_with(
            "tidal_predictions/Point Atkinson_tidal_prediction_"
            "01-Jan-2013_31-Dec-2020.csv"
        )
        m_cms.assert_called_once_with(
            "pmv.xml", m_ltp()[0], run_date, "forecast", config
        )
        m_ssrl.assert_called_once_with("Point Atkinson", max_ssh, m_ltp()[0])
        np.testing.assert_array_equal(max_ssh_info["max_ssh"], np.array([5.09]))
        np.testing.assert_array_equal(max_ssh_info["max_ssh_time"], max_ssh_time)
        assert max_ssh_info["risk_level"] == m_ssrl()


@patch("nowcast.workers.make_feeds.logger", autospec=True)
@patch("nowcast.workers.make_feeds.nc.Dataset", autospec=True)
@patch("nowcast.workers.make_feeds.nc_tools.ssh_timeseries_at_point", autospec=True)
@patch("nowcast.workers.make_feeds.nowcast.figures.shared.find_ssh_max", autospec=True)
class TestCalcMaxSsh:
    """Unit test for _calc_max_ssh() function."""

    def test_calc_max_ssh(self, m_fsshmax, m_sshtapt, m_ncd, m_logger, config):
        ssh_ts = namedtuple("ssh_ts", "ssh, time")
        m_sshtapt.return_value = ssh_ts(
            np.array([1.93]), np.array([datetime.datetime(2015, 12, 22, 22, 40, 42)])
        )
        m_fsshmax.return_value = (
            np.array([5.09]),
            np.array([datetime.datetime(2015, 12, 22, 22, 40, 42)]),
        )
        max_ssh, max_ssh_time = make_feeds._calc_max_ssh(
            "pmv.xml", "ttide", arrow.get("2015-12-22").floor("day"), "forecast", config
        )
        m_ncd.assert_called_once_with(
            "/results/SalishSea/forecast/22dec15/PointAtkinson.nc"
        )
        m_sshtapt.assert_called_once_with(m_ncd(), 0, 0, datetimes=True)
        assert not m_logger.critical.called
        np.testing.assert_array_equal(max_ssh, np.array([5.09]))
        np.testing.assert_array_equal(
            max_ssh_time, np.array([datetime.datetime(2015, 12, 22, 22, 40, 42)])
        )

    def test_max_ssh_is_nan(self, m_fsshmax, m_sshtapt, m_ncd, m_logger, config):
        ssh_ts = namedtuple("ssh_ts", "ssh, time")
        m_sshtapt.return_value = ssh_ts(
            np.array([np.nan]), np.array([datetime.datetime(2017, 10, 7, 17, 48, 42)])
        )
        m_fsshmax.return_value = (
            np.array([np.nan]),
            np.array([datetime.datetime(2015, 12, 22, 22, 40, 42)]),
        )
        with pytest.raises(WorkerError):
            max_ssh, max_ssh_time = make_feeds._calc_max_ssh(
                "pmv.xml",
                "ttide",
                arrow.get("2017-10-07").floor("day"),
                "forecast",
                config,
            )
        assert m_logger.critical.called
