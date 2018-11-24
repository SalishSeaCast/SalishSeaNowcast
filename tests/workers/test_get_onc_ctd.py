#  Copyright 2013-2018 The Salish Sea MEOPAR contributors
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
"""Unit tests for Salish Sea NEMO nowcast get_onc_ctd worker.
"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import get_onc_ctd


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    return base_config


@patch("nowcast.workers.get_onc_ctd.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_onc_ctd.main()
        args, kwargs = m_worker.call_args
        assert args == ("get_onc_ctd",)
        assert "description" in kwargs

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_onc_ctd.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_onc_station_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_onc_ctd.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("onc_station",)
        assert kwargs["choices"] == {"SCVIP", "SEVIP", "USDDL"}
        assert "help" in kwargs

    def test_add_data_date_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_onc_ctd.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--data-date",)
        assert kwargs["default"] == arrow.utcnow().floor("day").shift(days=-1)
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        get_onc_ctd.main()
        args, kwargs = m_worker().run.call_args
        expected = (get_onc_ctd.get_onc_ctd, get_onc_ctd.success, get_onc_ctd.failure)
        assert args == expected


@pytest.mark.parametrize("onc_station", ["SCVIP", "SEVIP", "USDDL"])
@patch("nowcast.workers.get_onc_ctd.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, onc_station):
        parsed_args = SimpleNamespace(
            onc_station=onc_station, data_date=arrow.get("2016-09-09")
        )
        get_onc_ctd.success(parsed_args)
        assert m_logger.info.called
        assert m_logger.info.call_args[1]["extra"]["onc_station"] == onc_station
        assert m_logger.info.call_args[1]["extra"]["data_date"] == "2016-09-09"

    def test_success_msg_type(self, m_logger, onc_station):
        parsed_args = SimpleNamespace(
            onc_station=onc_station, data_date=arrow.get("2016-09-09")
        )
        msg_type = get_onc_ctd.success(parsed_args)
        assert msg_type == "success {}".format(onc_station)


@pytest.mark.parametrize("onc_station", ["SCVIP", "SEVIP", "USDDL"])
@patch("nowcast.workers.get_onc_ctd.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_critical(self, m_logger, onc_station):
        parsed_args = SimpleNamespace(
            onc_station=onc_station, data_date=arrow.get("2016-09-09")
        )
        get_onc_ctd.failure(parsed_args)
        assert m_logger.critical.called
        extra_value = m_logger.critical.call_args[1]["extra"]["onc_station"]
        assert extra_value == onc_station
        extra_value = m_logger.critical.call_args[1]["extra"]["data_date"]
        assert extra_value == "2016-09-09"

    def test_failure_msg_type(self, m_logger, onc_station):
        parsed_args = SimpleNamespace(
            onc_station=onc_station, data_date=arrow.get("2016-09-09")
        )
        msg_type = get_onc_ctd.failure(parsed_args)
        assert msg_type == "failure"
