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


"""Unit tests for SalishSeaCast make_201702_runoff_file worker."""
import logging
import os
from pathlib import Path
import textwrap
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_201702_runoff_file


@pytest.fixture
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                rivers:
                  SOG river files:
                    Fraser: SOG-forcing/ECget/Fraser_flow
                  bathy params:
                    v201702:  # **Required for runoff files used by nowcast-agrif**
                      Fraser climatology: tools/I_ForcingFiles/Rivers/FraserClimatologySeparation.yaml
                      monthly climatology: rivers-climatology/rivers_month_201702.nc
                      file template: "R201702DFraCElse_{:y%Ym%md%d}.nc"
                      prop_dict module: salishsea_tools.river_201702
                  rivers dir: forcing/rivers/
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(make_201702_runoff_file, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = make_201702_runoff_file.main()
        assert worker.name == "make_201702_runoff_file"
        assert worker.description.startswith(
            "SalishSeaCast runoff file generation worker for v201702 bathymetry."
        )

    def test_add_run_date_option(self, mock_worker):
        worker = make_201702_runoff_file.main()
        assert worker.cli.parser._actions[3].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[3].type == expected
        assert worker.cli.parser._actions[3].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[3].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_201702_runoff_file" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"][
            "make_201702_runoff_file"
        ]
        assert msg_registry["checklist key"] == "rivers forcing"

    @pytest.mark.parametrize("msg", ("success", "failure", "crash"))
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "make_201702_runoff_file"
        ]
        assert msg in msg_registry

    def test_rivers_section(self, prod_config):
        rivers = prod_config["rivers"]
        assert rivers["rivers dir"] == "/results/forcing/rivers/"
        assert (
            rivers["SOG river files"]["Capilano"]
            == "/opp/observations/rivers/Capilano/Caplilano_08GA010_day_avg_flow"
        )

    def test_bathy_params(self, prod_config):
        bathy_params = prod_config["rivers"]["bathy params"]["v201702"]
        assert bathy_params["file template"] == "R201702DFraCElse_{:y%Ym%md%d}.nc"
        assert bathy_params["prop_dict module"] == "salishsea_tools.river_201702"
        assert (
            bathy_params["Fraser climatology"]
            == "/SalishSeaCast/tools/I_ForcingFiles/Rivers/FraserClimatologySeparation.yaml"
        )
        assert (
            bathy_params["monthly climatology"]
            == "/SalishSeaCast/rivers-climatology/rivers_month_201702.nc"
        )


class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, caplog):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-05-17"))
        caplog.set_level(logging.DEBUG)

        msg_type = make_201702_runoff_file.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = "2017-05-17 runoff file creation from Fraser at Hope and climatology elsewhere complete"
        assert caplog.messages[0] == expected
        assert msg_type == "success"


class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, caplog):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-05-17"))
        caplog.set_level(logging.DEBUG)

        msg_type = make_201702_runoff_file.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        assert caplog.messages[0] == "2017-05-17 runoff file creation failed"
        assert msg_type == "failure"


class TestMake201702RunoffFile:
    """Unit test for make_201702_runoff_file() function."""

    @staticmethod
    @pytest.fixture
    def mock_fraser_climatology(monkeypatch):
        def _mock_fraser_climatology(filename):
            return {
                "Ratio that is Fraser": 0.984,
                "Ratio that is not Fraser": 0.016,
                "after Hope by Month": [
                    764.1547237094221,
                    691.1521248104726,
                    737.0447810295404,
                    692.621413757194,
                    1590.0495569959855,
                    1151.9673805479404,
                    996.5735144714745,
                    722.0115400388124,
                    556.2719028784948,
                    546.710484751018,
                    935.1573966639444,
                    758.4038697988258,
                ],
                "non Fraser by Month": [
                    51.20758097807783,
                    46.31552655671484,
                    49.390887915772055,
                    46.41398663343098,
                    106.55249378526449,
                    77.19570538955959,
                    66.78244255977556,
                    48.38347949243763,
                    37.27692524650521,
                    36.636194936482006,
                    62.66682208605566,
                    50.82220441992422,
                ],
            }

        monkeypatch.setattr(
            make_201702_runoff_file, "_fraser_climatology", _mock_fraser_climatology
        )

    @staticmethod
    @pytest.fixture
    def mock_get_river_climatology(monkeypatch):
        def _mock_get_river_climatology(climatology_file):
            return 10_000.0, 18_5243.16

        monkeypatch.setattr(
            make_201702_runoff_file,
            "_get_river_climatology",
            _mock_get_river_climatology,
        )

    @staticmethod
    @pytest.fixture
    def mock_calculate_daily_flow(monkeypatch):
        def _mock_calculate_daily_flow(yesterday, criverflow):
            return 10_000.0

        monkeypatch.setattr(
            make_201702_runoff_file, "_calculate_daily_flow", _mock_calculate_daily_flow
        )

    @staticmethod
    @pytest.fixture
    def mock_combine_runoff(monkeypatch):
        def _mock_combine_runoff(
            prop_dict,
            flow_at_hope,
            yesterday,
            afterHope,
            nonFraser,
            fraserratio,
            otherratio,
            driverflow,
            area,
            directory,
            filename_tmpl,
        ):
            return directory / filename_tmpl.format(yesterday.date())

        monkeypatch.setattr(
            make_201702_runoff_file, "_combine_runoff", _mock_combine_runoff
        )

    def test_checklist(
        self,
        mock_fraser_climatology,
        mock_get_river_climatology,
        mock_calculate_daily_flow,
        mock_combine_runoff,
        config,
        caplog,
        tmp_path,
        monkeypatch,
    ):
        fraser_flow_file = Path(config["rivers"]["SOG river files"]["Fraser"])
        tmp_fraser_flow_dir = tmp_path / fraser_flow_file.parent
        tmp_fraser_flow_dir.mkdir(parents=True)
        tmp_fraser_flow_file = tmp_fraser_flow_dir / fraser_flow_file.name
        tmp_fraser_flow_file.write_text(
            "2025 04 16 2.609132e+03\n2025 04 17 2.593646e+03"
        )
        monkeypatch.setitem(
            config["rivers"]["SOG river files"], "Fraser", tmp_fraser_flow_file
        )
        rivers_dir = Path(config["rivers"]["rivers dir"])
        tmp_rivers_dir = tmp_path / rivers_dir
        tmp_rivers_dir.mkdir(parents=True)
        monkeypatch.setitem(config["rivers"], "rivers dir", tmp_rivers_dir)

        parsed_args = SimpleNamespace(run_date=arrow.get("2025-04-18"))

        checklist = make_201702_runoff_file.make_201702_runoff_file(parsed_args, config)

        expected = {
            "v201702": os.fspath(tmp_rivers_dir / "R201702DFraCElse_y2025m04d17.nc")
        }
        assert checklist == expected
