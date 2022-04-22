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
"""Unit tests for Salish Sea NEMO nowcast ping_erddap worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace

import nemo_nowcast
import pytest

from nowcast.workers import ping_erddap


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                erddap:
                  flag dir: tmp_flag_dir/
                  datasetIDs:
                    weather:
                      - ubcSSaSurfaceAtmosphereFieldsV1
                    SCVIP-CTD:
                      - ubcONCSCVIPCTD15mV1
                    SEVIP-CTD:
                      - ubcONCSEVIPCTD15mV1
                    USDDL-CTD:
                      - ubcONCUSDDLCTD15mV1
                    TWDP-ferry:
                      - ubcONCTWDP1mV1
                    nowcast-green:
                      - ubcSSg3DBiologyFields1hV19-05
                      - ubcSSg3DuGridFields1hV19-05
                    nemo-forecast:
                      - ubcSSfSandyCoveSSH10m
                    wwatch3-forecast:
                      - ubcSSf2DWaveFields30mV17-02
                    VFPA-HADCP:
                      - ubcVFPA2ndNarrowsCurrent2sV1
                    fvcom-x2-nowcast:
                      - ubcSSFVCOM-VHFR-BaroclinicX2
                    fvcom-r12-nowcast:
                      - ubcSSFVCOM-VHFR-BaroclinicR12
                    fvcom-forecast:
                      - ubcSSFVCOM-VHFR-BaroclinicX2
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(ping_erddap, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = ping_erddap.main()
        assert worker.name == "ping_erddap"
        assert worker.description.startswith(
            "SalishSeaCast worker that creates flag files to tell the ERDDAP server"
        )

    def test_add_dataset_arg(self, mock_worker):
        worker = ping_erddap.main()
        assert worker.cli.parser._actions[3].dest == "dataset"
        assert worker.cli.parser._actions[3].choices == {
            "weather",
            "SCVIP-CTD",
            "SEVIP-CTD",
            "USDDL-CTD",
            "TWDP-ferry",
            "VFPA-HADCP",
            "nowcast-green",
            "nemo-forecast",
            "wwatch3-forecast",
            "fvcom-x2-nowcast",
            "fvcom-r12-nowcast",
            "fvcom-forecast",
        }
        assert worker.cli.parser._actions[3].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "ping_erddap" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["ping_erddap"]
        assert msg_registry["checklist key"] == "ERDDAP flag files"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["ping_erddap"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success weather",
            "failure weather",
            "success SCVIP-CTD",
            "failure SCVIP-CTD",
            "success SEVIP-CTD",
            "failure SEVIP-CTD",
            "success USDDL-CTD",
            "failure USDDL-CTD",
            "success TWDP-ferry",
            "failure TWDP-ferry",
            "success VFPA-HADCP",
            "failure VFPA-HADCP",
            "success nowcast-green",
            "failure nowcast-green",
            "success nemo-forecast",
            "failure nemo-forecast",
            "success wwatch3-forecast",
            "failure wwatch3-forecast",
            "success fvcom-x2-nowcast",
            "failure fvcom-x2-nowcast",
            "success fvcom-r12-nowcast",
            "failure fvcom-r12-nowcast",
            "crash",
        ]

    def test_erddap_section(self, prod_config):
        erddap = prod_config["erddap"]
        assert erddap["flag dir"] == "/results/erddap/flag/"
        assert erddap["datasetIDs"]["weather"] == ["ubcSSaSurfaceAtmosphereFieldsV1"]
        assert erddap["datasetIDs"]["SCVIP-CTD"] == ["ubcONCSCVIPCTD15mV1"]
        assert erddap["datasetIDs"]["SEVIP-CTD"] == ["ubcONCSEVIPCTD15mV1"]
        # USDDL-CTD went out of service since 22-Dec-2019; repair ETA unknown
        # assert erddap["datasetIDs"]["USDDL-CTD"] == ["ubcONCUSDDLCTD15mV1"]
        assert erddap["datasetIDs"]["TWDP-ferry"] == ["ubcONCTWDP1mV1"]
        assert erddap["datasetIDs"]["nowcast-green"] == [
            "ubcSSg3DBiologyFields1hV19-05",
            "ubcSSg3DTracerFields1hV19-05",
            "ubcSSg3DuGridFields1hV19-05",
            "ubcSSg3DvGridFields1hV19-05",
            "ubcSSg3DwGridFields1hV19-05",
            "ubcSSgSurfaceTracerFields1hV19-05",
            "ubcSSg3DAuxiliaryFields1hV19-05",
        ]
        assert erddap["datasetIDs"]["nemo-forecast"] == [
            "ubcSSfBoundaryBaySSH10m",
            "ubcSSfCampbellRiverSSH10m",
            "ubcSSfCherryPointSSH10m",
            "ubcSSfFridayHarborSSH10m",
            "ubcSSfHalfmoonBaySSH10m",
            "ubcSSfNanaimoSSH10m",
            "ubcSSfNeahBaySSH10m",
            "ubcSSfNewWestminsterSSH10m",
            "ubcSSfPatriciaBaySSH10m",
            "ubcSSfPointAtkinsonSSH10m",
            "ubcSSfPortRenfrewSSH10m",
            "ubcSSfSandHeadsSSH10m",
            "ubcSSfSandyCoveSSH10m",
            "ubcSSfSquamishSSH10m",
            "ubcSSfVictoriaSSH10m",
            "ubcSSfWoodwardsLandingSSH10m",
            # currents and tracers
            "ubcSSfDepthAvgdCurrents1h",
            "ubcSSf3DuGridFields1h",
            "ubcSSf3DvGridFields1h",
            "ubcSSfSurfaceTracerFields1h",
        ]
        assert erddap["datasetIDs"]["wwatch3-forecast"] == [
            "ubcSSf2DWaveFields30mV17-02"
        ]
        assert erddap["datasetIDs"]["VFPA-HADCP"] == ["ubcVFPA2ndNarrowsCurrent2sV1"]
        assert erddap["datasetIDs"]["fvcom-x2-nowcast"] == [
            "ubcSSFVCOM-VHFR-BaroclinicX2"
        ]
        assert erddap["datasetIDs"]["fvcom-r12-nowcast"] == [
            "ubcSSFVCOM-VHFR-BaroclinicR12"
        ]


@pytest.mark.parametrize(
    "dataset",
    [
        "weather",
        "SCVIP-CTD",
        "SEVIP-CTD",
        "USDDL-CTD",
        "TWDP-ferry",
        "VFPA-HADCP",
        "nowcast-green",
        "nemo-forecast",
        "wwatch3-forecast",
        "fvcom-x2-nowcast",
        "fvcom-r12-nowcast",
        "fvcom-forecast",
    ],
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, dataset, caplog):
        caplog.set_level(logging.DEBUG)

        parsed_args = SimpleNamespace(dataset=dataset)
        msg_type = ping_erddap.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"{dataset} ERDDAP dataset flag file(s) created"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {dataset}"


@pytest.mark.parametrize(
    "dataset",
    [
        "weather",
        "SCVIP-CTD",
        "SEVIP-CTD",
        "USDDL-CTD",
        "TWDP-ferry",
        "VFPA-HADCP",
        "nowcast-green",
        "nemo-forecast",
        "wwatch3-forecast",
        "fvcom-x2-nowcast",
        "fvcom-r12-nowcast",
        "fvcom-forecast",
    ],
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, dataset, caplog):
        caplog.set_level(logging.DEBUG)

        parsed_args = SimpleNamespace(dataset=dataset)
        msg_type = ping_erddap.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"{dataset} ERDDAP dataset flag file(s) creation failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {dataset}"


class TestPingErddap:
    """Unit tests for ping_erddap() function."""

    @pytest.mark.parametrize(
        "dataset",
        [
            "weather",
            "SCVIP-CTD",
            "SEVIP-CTD",
            "USDDL-CTD",
            "TWDP-ferry",
            "VFPA-HADCP",
            "nowcast-green",
            "nemo-forecast",
            "wwatch3-forecast",
            "fvcom-x2-nowcast",
            "fvcom-r12-nowcast",
            "fvcom-forecast",
        ],
    )
    def test_ping_erddap(self, dataset, config, tmp_path, caplog, monkeypatch):
        caplog.set_level(logging.DEBUG)
        tmp_flag_dir = tmp_path / "flag"
        tmp_flag_dir.mkdir()
        monkeypatch.setitem(config["erddap"], "flag dir", tmp_flag_dir)

        parsed_args = SimpleNamespace(dataset=dataset)
        checklist = ping_erddap.ping_erddap(parsed_args, config)
        dataset_ids = config["erddap"]["datasetIDs"][dataset]

        for i, dataset_id in enumerate(dataset_ids):
            assert (tmp_flag_dir / dataset_id).exists()
            assert caplog.messages[i] == f"{tmp_flag_dir / dataset_id} touched"
        expected = {dataset: config["erddap"]["datasetIDs"][dataset]}
        assert checklist == expected

    def test_no_datasetID(self, config, tmp_path, caplog, monkeypatch):
        caplog.set_level(logging.DEBUG)
        tmp_flag_dir = tmp_path / "flag"
        tmp_flag_dir.mkdir()
        monkeypatch.setitem(config["erddap"], "flag dir", tmp_flag_dir)
        monkeypatch.setitem(config["erddap"], "datasetIDs", {"nowcast-green": []})

        parsed_args = SimpleNamespace(dataset="nowcast-green")
        checklist = ping_erddap.ping_erddap(parsed_args, config)

        assert not caplog.records
        assert checklist == {"nowcast-green": []}
