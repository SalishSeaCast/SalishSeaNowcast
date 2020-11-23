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
"""Unit tests for SalishSeaCast collect_river_data worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import numpy
import pandas
import pytest

from nowcast.workers import collect_river_data


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
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
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(collect_river_data, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = collect_river_data.main()
        assert worker.name == "collect_river_data"
        assert worker.description.startswith(
            "SalishSeaCast worker that collects river discharge observations data"
        )

    def test_add_river_name_arg(self, mock_worker):
        worker = collect_river_data.main()
        assert worker.cli.parser._actions[3].dest == "river_name"
        assert worker.cli.parser._actions[3].default is None
        assert worker.cli.parser._actions[3].help

    def test_add_data_date_option(self, mock_worker):
        worker = collect_river_data.main()
        assert worker.cli.parser._actions[4].dest == "data_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[4].type == expected
        assert worker.cli.parser._actions[4].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[4].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "collect_river_data" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["collect_river_data"]
        assert msg_registry["checklist key"] == "river data"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["collect_river_data"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success",
            "failure",
            "crash",
        ]

    def test_rivers_sections(self, prod_config):
        rivers = prod_config["rivers"]
        assert rivers["datamart dir"] == "/SalishSeaCast/datamart/hydrometric/"
        assert rivers["csv file template"] == "BC_{stn_id}_hourly_hydrometric.csv"
        assert rivers["stations"] == {
            "Capilano": "08GA010",
            "ChilliwackVedder": "08MH001",
            "ClowhomClowhomLake": "08GB013",
            "Englishman": "08HB002",
            "Fraser": "08MF005",
            "HomathkoMouth": "08GD004",
            "SalmonSayward": "08HD006",
            "SanJuanPortRenfrew": "08HA010",
            "SquamishBrackendale": "08GA022",
            "TheodosiaScotty": "08GC008",
            "TheodosiaBypass": "08GC006",
            "TheodosiaDiversion": "08GC005",
        }
        assert rivers["SOG river files"] == {
            "Capilano": "/opp/observations/rivers/Capilano/Caplilano_08GA010_day_avg_flow",
            "ChilliwackVedder": "/results/forcing/rivers/observations/Chilliwack_Vedder_flow",
            "ClowhomClowhomLake": "/results/forcing/rivers/observations/Clowhom_ClowhomLake_flow",
            "Englishman": "/data/dlatorne/SOG-projects/SOG-forcing/ECget/Englishman_flow",
            "Fraser": "/data/dlatorne/SOG-projects/SOG-forcing/ECget/Fraser_flow",
            "HomathkoMouth": "/results/forcing/rivers/observations/Homathko_Mouth_flow",
            "SalmonSayward": "/results/forcing/rivers/observations/Salmon_Sayward_flow",
            "SanJuanPortRenfrew": "/results/forcing/rivers/observations/SanJuan_PortRenfrew_flow",
            "SquamishBrackendale": "/results/forcing/rivers/observations/Squamish_Brackendale_flow",
            "TheodosiaScotty": "/results/forcing/rivers/observations/Theodosia_Scotty_flow",
            "TheodosiaBypass": "/results/forcing/rivers/observations/Theodosia_Bypass_flow",
            "TheodosiaDiversion": "/results/forcing/rivers/observations/Theodosia_Diversion_flow",
        }


class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, caplog):
        parsed_args = SimpleNamespace(
            river_name="Fraser", data_date=arrow.get("2018-12-26")
        )
        caplog.set_level(logging.INFO)
        msg_type = collect_river_data.success(parsed_args)
        assert caplog.records[0].levelname == "INFO"
        expected = (
            "Fraser river average discharge for 2018-12-26 calculated and appended to Fraser_"
            "flow file"
        )
        assert caplog.messages[0] == expected
        assert msg_type == "success"


class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, caplog):
        parsed_args = SimpleNamespace(
            river_name="Fraser", data_date=arrow.get("2018-12-26")
        )
        caplog.set_level(logging.CRITICAL)
        msg_type = collect_river_data.failure(parsed_args)
        assert caplog.records[0].levelname == "CRITICAL"
        expected = (
            "Calculation of Fraser river average discharge for 2018-12-26 or "
            "appending it to Fraser_flow file failed"
        )
        assert caplog.messages[0] == expected
        assert msg_type == "failure"


@pytest.mark.parametrize("river_name", ("Fraser", "Englishman"))
@patch("nowcast.workers.collect_river_data.logger", autospec=True)
@patch("nowcast.workers.collect_river_data._calc_day_avg_discharge", spec=True)
@patch("nowcast.workers.collect_river_data._store_day_avg_discharge", autospec=True)
class TestCollectRiverData:
    """Unit test for collect_river_data() function."""

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


@patch("nowcast.workers.collect_river_data.pandas.read_csv", autospec=True)
class TestCalcDayAvgDischarge:
    """Unit test for _calc_day_avg_discharge() function."""

    def test_calc_day_avg_discharge(self, m_read_csv, caplog, tmp_path):
        data_date = arrow.get("2018-12-26")
        csv_file = tmp_path / "cvs_file"
        data_frame = pandas.DataFrame(
            numpy.linspace(41.9, 44.1, 290),
            index=pandas.date_range(
                "2018-12-25 23:55:00", "2018-12-27 00:00:00", freq="5min"
            ),
            columns=["Discharge / Débit (cms)"],
        )
        m_read_csv.return_value = data_frame

        caplog.set_level(logging.DEBUG)

        day_avg_discharge = collect_river_data._calc_day_avg_discharge(
            csv_file, data_date
        )
        numpy.testing.assert_almost_equal(day_avg_discharge, 43.0)
        assert caplog.records[0].levelname == "DEBUG"
        expected = f"average discharge for {data_date.format('YYYY-MM-DD')} from {csv_file}: {day_avg_discharge:.6e} m^3/s"
        assert caplog.messages[0] == expected


class TestStoreDayAvgDischarge:
    """Unit test for _store_day_avg_discharge() function."""

    def test_store_day_avg_discharge(self, caplog, tmp_path):
        data_date = arrow.get("2018-12-26")
        day_avg_discharge = 123.456
        sog_flow_file = tmp_path / "river_flow"
        sog_flow_file.write_text("2018 12 25 1.654320e+02\n")

        caplog.set_level(logging.DEBUG)

        collect_river_data._store_day_avg_discharge(
            data_date, day_avg_discharge, sog_flow_file
        )
        with sog_flow_file.open("rt") as fp:
            assert fp.readlines()[-1] == "2018 12 26 1.234560e+02\n"
        assert caplog.records[0].levelname == "DEBUG"
        expected = f"appended {data_date.format('YYYY MM DD')} {day_avg_discharge:.6e} to: {sog_flow_file}"
        assert caplog.messages[0] == expected
