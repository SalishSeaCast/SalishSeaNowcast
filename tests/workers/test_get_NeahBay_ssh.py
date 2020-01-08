#  Copyright 2013-2020 The Salish Sea MEOPAR contributors
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
"""Unit tests for Salish Sea NEMO nowcast get_NeahBay_ssh worker.
"""
import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import pytz

from nowcast.workers import get_NeahBay_ssh


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    return base_config


@patch("nowcast.workers.get_NeahBay_ssh.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_NeahBay_ssh.main()
        args, kwargs = m_worker.call_args
        assert args == ("get_NeahBay_ssh",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_NeahBay_ssh.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_NeahBay_ssh.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast", "forecast2"}
        assert "help" in kwargs

    def test_add_text_file_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_NeahBay_ssh.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("--text-file",)
        assert kwargs["type"] == Path
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_NeahBay_ssh.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            get_NeahBay_ssh.get_NeahBay_ssh,
            get_NeahBay_ssh.success,
            get_NeahBay_ssh.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "get_NeahBay_ssh" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["get_NeahBay_ssh"]
        assert msg_registry["checklist key"] == "Neah Bay ssh"

    @pytest.mark.parametrize(
        "msg",
        (
            "success nowcast",
            "failure nowcast",
            "success forecast",
            "failure forecast",
            "success forecast2",
            "failure forecast2",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["get_NeahBay_ssh"]
        assert msg in msg_registry

    def test_ssh_sections(self, prod_config):
        ssh = prod_config["ssh"]
        assert (
            ssh["coordinates"]
            == "/SalishSeaCast/grid/coordinates_seagrid_SalishSea2.nc"
        )
        assert (
            ssh["tidal predictions"]
            == "/SalishSeaCast/SalishSeaNowcast/tidal_predictions/"
        )
        assert (
            ssh["neah bay hourly"]
            == "Neah Bay_1h_tidal_prediction_01-Jan-2013_31-Dec-2020.csv"
        )
        assert ssh["ssh dir"] == "/results/forcing/sshNeahBay/"
        assert ssh["file template"] == "ssh_{:y%Ym%md%d}.nc"
        assert (
            ssh["monitoring image"]
            == "/results/nowcast-sys/figures/monitoring/NBssh.png"
        )


@pytest.mark.parametrize("run_type", ["nowcast", "forecast", "forecast2"])
@patch("nowcast.workers.get_NeahBay_ssh.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(self, m_logger, run_type):
        parsed_args = Mock(run_type=run_type)
        msg_type = get_NeahBay_ssh.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == "success {}".format(run_type)


@pytest.mark.parametrize("run_type", ["nowcast", "forecast", "forecast2"])
@patch("nowcast.workers.get_NeahBay_ssh.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(self, m_logger, run_type):
        parsed_args = Mock(run_type=run_type)
        msg_type = get_NeahBay_ssh.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == "failure {}".format(run_type)


class TestUTCNowToRunDate:
    """Unit tests for _utc_now_to_run_date() function.
    """

    def test_nowcast(self):
        utc_now = datetime.datetime(
            2014, 12, 25, 17, 52, 42, tzinfo=pytz.timezone("UTC")
        )
        run_day = get_NeahBay_ssh._utc_now_to_run_date(utc_now, "nowcast")
        assert run_day == datetime.date(2014, 12, 25)

    def test_forecast(self):
        utc_now = datetime.datetime(
            2014, 12, 25, 19, 54, 42, tzinfo=pytz.timezone("UTC")
        )
        run_day = get_NeahBay_ssh._utc_now_to_run_date(utc_now, "forecast")
        assert run_day == datetime.date(2014, 12, 25)

    def test_forecast2(self):
        utc_now = datetime.datetime(
            2014, 12, 26, 12, 53, 42, tzinfo=pytz.timezone("UTC")
        )
        run_day = get_NeahBay_ssh._utc_now_to_run_date(utc_now, "forecast2")
        assert run_day == datetime.date(2014, 12, 25)
