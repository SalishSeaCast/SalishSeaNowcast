#  Copyright 2013-2019 The Salish Sea MEOPAR contributors
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
"""Unit tests for SalishSeaCast collect_river_data worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import numpy
import pandas
import pytest

from nowcast.workers import collect_river_data


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
rivers:
  datamart dir: datamart/hydrometric/
  csv file template: 'BC_{stn_id}_hourly_hydrometric.csv'
  stations:
    Capilano: 08GA010
    Englishman: 08HB002
    Fraser: 08MF005
  SOG river files:
    Capilano: /opp/observations/rivers/Capilano/Caplilano_08GA010_day_avg_flow
    Englishman: SOG-projects/SOG-forcing/ECget/Englishman_flow
    Fraser: SOG-projects/SOG-forcing/ECget/Fraser_flow
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.collect_river_data.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        collect_river_data.main()
        args, kwargs = m_worker.call_args
        assert args == ("collect_river_data",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        collect_river_data.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        collect_river_data.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("river_name",)
        assert "help" in kwargs

    def test_add_data_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        collect_river_data.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--data-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        collect_river_data.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            collect_river_data.collect_river_data,
            collect_river_data.success,
            collect_river_data.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "collect_river_data" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["collect_river_data"]
        assert msg_registry["checklist key"] == "river data"

    @pytest.mark.parametrize("msg", ("success", "failure", "crash"))
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["collect_river_data"]
        assert msg in msg_registry

    def test_rivers_sections(self, prod_config):
        rivers = prod_config["rivers"]
        assert rivers["datamart dir"] == "/SalishSeaCast/datamart/hydrometric/"
        assert rivers["csv file template"] == "BC_{stn_id}_hourly_hydrometric.csv"
        assert rivers["stations"] == {
            "Capilano": "08GA010",
            "Englishman": "08HB002",
            "Fraser": "08MF005",
        }
        assert (
            rivers["SOG river files"]["Capilano"]
            == "/opp/observations/rivers/Capilano/Caplilano_08GA010_day_avg_flow"
        )
        assert (
            rivers["SOG river files"]["Englishman"]
            == "/data/dlatorne/SOG-projects/SOG-forcing/ECget/Englishman_flow"
        )
        assert (
            rivers["SOG river files"]["Fraser"]
            == "/data/dlatorne/SOG-projects/SOG-forcing/ECget/Fraser_flow"
        )


@patch("nowcast.workers.collect_river_data.logger", autospec=True)
class TestSuccess:
    """Unit test for success() function.
    """

    def test_success_log_info(self, m_logger):
        parsed_args = SimpleNamespace(
            river_name="Fraser", data_date=arrow.get("2018-12-26")
        )
        msg_type = collect_river_data.success(parsed_args)
        m_logger.info.assert_called_once_with(
            "Fraser river average discharge for 2018-12-26 calculated and appended to Fraser_"
            "flow file"
        )
        assert msg_type == "success"


@patch("nowcast.workers.collect_river_data.logger", autospec=True)
class TestFailure:
    """Unit test for failure() function.
    """

    def test_failure_log_critical_file_creation(self, m_logger):
        parsed_args = SimpleNamespace(
            river_name="Fraser", data_date=arrow.get("2018-12-26")
        )
        msg_type = collect_river_data.failure(parsed_args)
        m_logger.critical.assert_called_once_with(
            "Calculation of Fraser river average discharge for 2018-12-26 or "
            "appending it to Fraser_flow file failed"
        )
        assert msg_type == "failure"


@pytest.mark.parametrize("river_name", ("Fraser", "Englishman"))
@patch("nowcast.workers.collect_river_data.logger", autospec=True)
@patch("nowcast.workers.collect_river_data._calc_day_avg_discharge", spec=True)
@patch("nowcast.workers.collect_river_data._store_day_avg_discharge", autospec=True)
class TestCollectRiverData:
    """Unit test for collect_river_data() function.
    """

    def test_checklist(
        self, m_store_day_avg_q, m_calc_day_avg_q, m_logger, river_name, config
    ):
        parsed_args = SimpleNamespace(
            river_name=river_name, data_date=arrow.get("2018-12-26")
        )
        checklist = collect_river_data.collect_river_data(parsed_args, config)

        stn_id = config["rivers"]["stations"][river_name]
        csv_file_template = config["rivers"]["csv file template"]
        m_calc_day_avg_q.assert_called_once_with(
            Path(config["rivers"]["datamart dir"])
            / csv_file_template.format(stn_id=stn_id),
            arrow.get("2018-12-26"),
        )
        m_store_day_avg_q.assert_called_once_with(
            arrow.get("2018-12-26"),
            m_calc_day_avg_q(),
            Path(config["rivers"]["SOG river files"][river_name]),
        )
        expected = {"river name": river_name, "data date": "2018-12-26"}
        assert checklist == expected


@patch("nowcast.workers.collect_river_data.logger", autospec=True)
@patch("nowcast.workers.collect_river_data.pandas.read_csv", autospec=True)
class TestCalcDayAvgDischarge:
    """Unit tests for _calc_day_avg_discharge() function.
    """

    def test_calc_day_avg_discharge(self, m_read_csv, m_logger):
        data_frame = pandas.DataFrame(
            numpy.linspace(41.9, 44.1, 290),
            index=pandas.date_range(
                "2018-12-25 23:55:00", "2018-12-27 00:00:00", freq="5min"
            ),
            columns=["Discharge / Débit (cms)"],
        )
        m_read_csv.return_value = data_frame
        day_avg_discharge = collect_river_data._calc_day_avg_discharge(
            Path("cvs_file"), arrow.get("2018-12-26")
        )
        numpy.testing.assert_almost_equal(day_avg_discharge, 43.0)


@patch("nowcast.workers.collect_river_data.logger", autospec=True)
@patch("nowcast.workers.collect_river_data.Path.open", spec=True)
class TestStoreDayAvgDischarge:
    """Unit tests for _store_day_avg_discharge() function.
    """

    def test_store_day_avg_discharge(self, m_open, m_logger):
        collect_river_data._store_day_avg_discharge(
            arrow.get("2018-12-26"), 123.456, Path("river_flow")
        )
        m_open.assert_called_once_with("at")
        m_open().__enter__().write.assert_called_once_with("2018 12 26 1.234560e+02\n")
