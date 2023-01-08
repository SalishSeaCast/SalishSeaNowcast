#  Copyright 2013 – present by the SalishSeaCast Project contributors
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

# SPDX-License-Identifier: Apache-2.0


"""Unit tests for SalishSeaCast collect_river_data worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import httpx
import nemo_nowcast
import numpy
import pandas
import pytest
from nemo_nowcast import WorkerError

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
                  usgs url: https://waterservices.usgs.gov/nwis/dv/
                  usgs params:
                    format: json
                    parameterCd: "00060"
                    sites: ""
                    startDT: ""
                    endDT: ""
                  stations:
                    ECCC:
                      Fraser: 08MF005
                    USGS:
                      SkagitMountVernon: 12200500
                  SOG river files:
                    Fraser: Fraser_flow
                    SkagitMountVernon: Skagit_MountVernon_flow
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
            "SalishSeaCast worker that collects river discharge observation data"
        )

    def test_add_data_source_arg(self, mock_worker):
        worker = collect_river_data.main()
        assert worker.cli.parser._actions[3].dest == "data_src"
        assert worker.cli.parser._actions[3].choices == {"ECCC", "USGS"}
        assert worker.cli.parser._actions[3].help

    def test_add_river_name_arg(self, mock_worker):
        worker = collect_river_data.main()
        assert worker.cli.parser._actions[4].dest == "river_name"
        assert worker.cli.parser._actions[4].default is None
        assert worker.cli.parser._actions[4].help

    def test_add_data_date_option(self, mock_worker):
        worker = collect_river_data.main()
        assert worker.cli.parser._actions[5].dest == "data_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[5].type == expected
        assert worker.cli.parser._actions[5].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[5].help


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

    def test_ECCC_rivers_paths_files(self, prod_config):
        rivers = prod_config["rivers"]
        assert rivers["datamart dir"] == "/SalishSeaCast/datamart/hydrometric/"
        assert rivers["csv file template"] == "BC_{stn_id}_hourly_hydrometric.csv"

    def test_USGS_url_params(self, prod_config):
        rivers = prod_config["rivers"]
        assert rivers["usgs url"] == "https://waterservices.usgs.gov/nwis/dv/"
        expected = {
            "format": "json",
            "parameterCd": "00060",
            "sites": "",
            "startDT": "",
            "endDT": "",
        }
        assert rivers["usgs params"] == expected

    def test_ECCC_rivers(self, prod_config):
        rivers = prod_config["rivers"]
        assert rivers["stations"]["ECCC"] == {
            "Capilano": "08GA010",
            "ChilliwackVedder": "08MH001",
            "ClowhomClowhomLake": "08GB013",
            "Englishman": "08HB002",
            "Fraser": "08MF005",
            "HomathkoMouth": "08GD004",
            "NicomeklLangley": "08MH155",
            "RobertsCreek": "08GA047",
            "SalmonSayward": "08HD006",
            "SanJuanPortRenfrew": "08HA010",
            "SquamishBrackendale": "08GA022",
            "TheodosiaScotty": "08GC008",
            "TheodosiaBypass": "08GC006",
            "TheodosiaDiversion": "08GC005",
        }

    def test_USGS_rivers(self, prod_config):
        rivers = prod_config["rivers"]
        assert rivers["stations"]["USGS"] == {
            "SkagitMountVernon": 12200500,
            "SnohomishMonroe": 12150800,
            "NisquallyMcKenna": 12089500,
            "GreenwaterGreenwater": 12097500,
        }

    def test_SOG_river_files(self, prod_config):
        rivers = prod_config["rivers"]
        assert rivers["SOG river files"] == {
            "Capilano": "/opp/observations/rivers/Capilano/Caplilano_08GA010_day_avg_flow",
            "ChilliwackVedder": "/results/forcing/rivers/observations/Chilliwack_Vedder_flow",
            "ClowhomClowhomLake": "/results/forcing/rivers/observations/Clowhom_ClowhomLake_flow",
            "Englishman": "/data/dlatorne/SOG-projects/SOG-forcing/ECget/Englishman_flow",
            "Fraser": "/data/dlatorne/SOG-projects/SOG-forcing/ECget/Fraser_flow",
            "GreenwaterGreenwater": "/results/forcing/rivers/observations/Greenwater_Greenwater_flow",
            "HomathkoMouth": "/results/forcing/rivers/observations/Homathko_Mouth_flow",
            "NisquallyMcKenna": "/results/forcing/rivers/observations/Nisqually_McKenna_flow",
            "NicomeklLangley": "/results/forcing/rivers/observations/Nicomekl_Langley_flow",
            "RobertsCreek": "/results/forcing/rivers/observations/RobertsCreek_flow",
            "SalmonSayward": "/results/forcing/rivers/observations/Salmon_Sayward_flow",
            "SanJuanPortRenfrew": "/results/forcing/rivers/observations/SanJuan_PortRenfrew_flow",
            "SkagitMountVernon": "/results/forcing/rivers/observations/Skagit_MountVernon_flow",
            "SnohomishMonroe": "/results/forcing/rivers/observations/Snohomish_Monroe_flow",
            "SquamishBrackendale": "/results/forcing/rivers/observations/Squamish_Brackendale_flow",
            "TheodosiaScotty": "/results/forcing/rivers/observations/Theodosia_Scotty_flow",
            "TheodosiaBypass": "/results/forcing/rivers/observations/Theodosia_Bypass_flow",
            "TheodosiaDiversion": "/results/forcing/rivers/observations/Theodosia_Diversion_flow",
        }


class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, caplog):
        parsed_args = SimpleNamespace(
            data_src="ECCC", river_name="Fraser", data_date=arrow.get("2018-12-26")
        )
        caplog.set_level(logging.INFO)
        msg_type = collect_river_data.success(parsed_args)
        assert caplog.records[0].levelname == "INFO"
        expected = "ECCC Fraser river data collection for 2018-12-26 completed"
        assert caplog.messages[0] == expected
        assert msg_type == "success"


class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, caplog):
        parsed_args = SimpleNamespace(
            data_src="ECCC", river_name="Fraser", data_date=arrow.get("2018-12-26")
        )
        caplog.set_level(logging.CRITICAL)
        msg_type = collect_river_data.failure(parsed_args)
        assert caplog.records[0].levelname == "CRITICAL"
        expected = (
            "Calculation of ECCC Fraser river average discharge for 2018-12-26 or "
            "appending it to Fraser_flow file failed"
        )
        assert caplog.messages[0] == expected
        assert msg_type == "failure"


@pytest.mark.parametrize(
    "data_src, river_name",
    (
        ("ECCC", "Fraser"),
        ("USGS", "SkagitMountVernon"),
    ),
)
class TestCollectRiverData:
    """Unit test for collect_river_data() function."""

    def test_checklist(
        self, data_src, river_name, config, caplog, tmp_path, monkeypatch
    ):
        def mock_calc_eccc_day_avg_discharge(river_name, data_date, config):
            return 12345.6

        monkeypatch.setattr(
            collect_river_data,
            "_calc_eccc_day_avg_discharge",
            mock_calc_eccc_day_avg_discharge,
        )

        def mock_get_usgs_day_avg_discharge(river_name, data_date, config):
            return 12345.6

        monkeypatch.setattr(
            collect_river_data,
            "_get_usgs_day_avg_discharge",
            mock_get_usgs_day_avg_discharge,
        )

        sog_river_file = config["rivers"]["SOG river files"][river_name]
        monkeypatch.setitem(
            config["rivers"]["SOG river files"], river_name, tmp_path / sog_river_file
        )

        parsed_args = SimpleNamespace(
            data_src=data_src, river_name=river_name, data_date=arrow.get("2018-12-26")
        )

        caplog.set_level(logging.DEBUG)

        checklist = collect_river_data.collect_river_data(parsed_args, config)

        assert caplog.records[0].levelname == "INFO"
        expected = f"Collecting {data_src} {river_name} river data for 2018-12-26"
        assert caplog.messages[0] == expected
        assert caplog.records[2].levelname == "INFO"
        expected = (
            f"Appended {data_src} {river_name} river average discharge for 2018-12-26 to: "
            f"{Path(config['rivers']['SOG river files'][river_name])}"
        )
        assert caplog.messages[2] == expected
        expected = {"river name": river_name, "data date": "2018-12-26"}
        assert checklist == expected


class TestCalcECCC_DayAvgDischarge:
    """Unit test for _calc_eccc_day_avg_discharge() function."""

    def test_calc_eccc_day_avg_discharge(self, config, caplog, tmp_path, monkeypatch):
        def mock_read_csv(csv_file, usecols, index_col, date_parser):
            return pandas.DataFrame(
                numpy.linspace(41.9, 44.1, 290),
                index=pandas.date_range(
                    "2018-12-25 23:55:00", "2018-12-27 00:00:00", freq="5min"
                ),
                columns=["Discharge / Débit (cms)"],
            )

        monkeypatch.setattr(collect_river_data.pandas, "read_csv", mock_read_csv)

        caplog.set_level(logging.DEBUG)

        day_avg_discharge = collect_river_data._calc_eccc_day_avg_discharge(
            "Fraser", "2018-12-26", config
        )

        numpy.testing.assert_almost_equal(day_avg_discharge, 43.0)
        assert caplog.records[0].levelname == "DEBUG"
        expected = (
            f"average discharge for 2018-12-26 from "
            f"datamart/hydrometric/BC_08MF005_hourly_hydrometric.csv: "
            f"{day_avg_discharge:.6e} m^3/s"
        )
        assert caplog.messages[0] == expected


class TestGetUSGS_DayAvgDischarge:
    """Unit test for _get_usgs_day_avg_discharge() function."""

    def test_get_usgs_day_avg_discharge(self, config, httpx_mock, caplog):
        httpx_mock.add_response(
            json={
                "value": {
                    "timeSeries": [
                        {
                            "variable": {
                                "noDataValue": -999999,
                            },
                            "values": [{"value": [{"value": 43 / 0.0283168}]}],
                        }
                    ]
                }
            }
        )
        caplog.set_level(logging.DEBUG)

        day_avg_discharge = collect_river_data._get_usgs_day_avg_discharge(
            "SkagitMountVernon", "2023-01-06", config
        )

        numpy.testing.assert_almost_equal(day_avg_discharge, 43.0)
        assert caplog.records[1].levelname == "DEBUG"
        expected = (
            f"average discharge for SkagitMountVernon on 2023-01-06 from "
            f"https://waterservices.usgs.gov/nwis/dv/: {day_avg_discharge:.6e} m^3/s"
        )
        assert caplog.messages[1] == expected

    def test_http_RequestError(self, config, httpx_mock, caplog):
        httpx_mock.add_exception(httpx.RequestError("error issuing request"))
        caplog.set_level(logging.DEBUG)

        with pytest.raises(WorkerError):
            collect_river_data._get_usgs_day_avg_discharge(
                "SkagitMountVernon", "2023-01-06", config
            )

        assert caplog.records[0].levelname == "CRITICAL"
        usgs_url = config["rivers"]["usgs url"]
        assert caplog.messages[0].startswith(f"Error while requesting {usgs_url}")

    def test_HTTPStatusError(self, config, httpx_mock, caplog):
        httpx_mock.add_response(status_code=500)
        caplog.set_level(logging.DEBUG)

        with pytest.raises(WorkerError):
            collect_river_data._get_usgs_day_avg_discharge(
                "SkagitMountVernon", "2023-01-06", config
            )

        assert caplog.records[1].levelname == "CRITICAL"
        usgs_url = config["rivers"]["usgs url"]
        assert caplog.messages[1].startswith(
            f"Error response 500 while requesting {usgs_url}"
        )

    def test_empty_timeseries(self, config, httpx_mock, caplog):
        httpx_mock.add_response(json={"value": {"timeSeries": []}})
        caplog.set_level(logging.DEBUG)

        with pytest.raises(WorkerError):
            collect_river_data._get_usgs_day_avg_discharge(
                "SkagitMountVernon", "2023-01-06", config
            )

        assert caplog.records[1].levelname == "CRITICAL"
        assert caplog.messages[1] == "SkagitMountVernon 2023-01-06 timeSeries is empty"

    @pytest.mark.parametrize(
        "values",
        (
            [],
            [{"value": []}],
        ),
    )
    def test_cfs_value_IndexError(self, values, config, httpx_mock, caplog):
        httpx_mock.add_response(
            json={
                "value": {
                    "timeSeries": [
                        {
                            "variable": {
                                "noDataValue": -999999,
                            },
                            "values": values,
                        }
                    ]
                }
            }
        )
        caplog.set_level(logging.DEBUG)

        with pytest.raises(WorkerError):
            collect_river_data._get_usgs_day_avg_discharge(
                "SkagitMountVernon", "2023-01-06", config
            )

        assert caplog.records[1].levelname == "CRITICAL"
        expected = "IndexError in SkagitMountVernon 2023-01-06 timeSeries JSON"
        assert caplog.messages[1] == expected

    @pytest.mark.parametrize(
        "value",
        (
            {
                "timeSeries": [
                    {
                        "variable": {
                            "noDataValue": -999999,
                        },
                        "not values": [],
                    }
                ]
            },
            {
                "timeSeries": [
                    {
                        "variable": {
                            "noDataValue": -999999,
                        },
                        "values": [{"not value": []}],
                    }
                ]
            },
            {
                "timeSeries": [
                    {
                        "variable": {
                            "noDataValue": -999999,
                        },
                        "values": [{"value": [{"not value": 43}]}],
                    }
                ]
            },
        ),
    )
    def test_cfs_value_KeyError(self, value, config, httpx_mock, caplog):
        httpx_mock.add_response(
            json={
                "value": value,
            }
        )
        caplog.set_level(logging.DEBUG)

        with pytest.raises(WorkerError):
            collect_river_data._get_usgs_day_avg_discharge(
                "SkagitMountVernon", "2023-01-06", config
            )

        assert caplog.records[1].levelname == "CRITICAL"
        expectged = "KeyError in SkagitMountVernon 2023-01-06 timeSeries JSON"
        assert caplog.messages[1] == expectged

    def test_no_data(self, config, httpx_mock, caplog):
        httpx_mock.add_response(
            json={
                "value": {
                    "timeSeries": [
                        {
                            "variable": {
                                "noDataValue": -999999,
                            },
                            "values": [
                                {
                                    "value": [
                                        {
                                            "value": -999999,
                                        }
                                    ]
                                }
                            ],
                        }
                    ]
                }
            }
        )
        caplog.set_level(logging.DEBUG)

        with pytest.raises(WorkerError):
            collect_river_data._get_usgs_day_avg_discharge(
                "SkagitMountVernon", "2023-01-06", config
            )

        assert caplog.records[1].levelname == "CRITICAL"
        expected = (
            "Got no-data value (-999999) in SkagitMountVernon 2023-01-06 timeSeries"
        )
        assert caplog.messages[1] == expected


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
