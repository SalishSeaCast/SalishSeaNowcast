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
                SOG river files:
                  Fraser: SOG-forcing/ECget/Fraser_flow
                rivers:
                  bathy params:
                    v201702:  # **Required for runoff files used by nowcast-agrif**
                      Fraser climatology: tools/I_ForcingFiles/Rivers/FraserClimatologySeparation.yaml
                      monthly climatology: rivers-climatology/rivers_month_201702.nc
                      file template: "R201702DFraCElse_{:y%Ym%md%d}.nc"
                      prop_dict modules: salishsea_tools.river_201702
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
        assert msg_registry["checklist key"] == "v201702 rivers forcing"

    @pytest.mark.parametrize("msg", ("success", "failure", "crash"))
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "make_201702_runoff_file"
        ]
        assert msg in msg_registry

    def test_rivers_sections(self, prod_config):
        rivers = prod_config["rivers"]
        assert (
            rivers["bathy params"]["v201702"]["file template"]
            == "R201702DFraCElse_{:y%Ym%md%d}.nc"
        )
        assert rivers["rivers dir"] == "/results/forcing/rivers/"
        assert (
            rivers["bathy params"]["v201702"]["prop_dict module"]
            == "salishsea_tools.river_201702"
        )
        assert (
            rivers["SOG river files"]["Capilano"]
            == "/opp/observations/rivers/Capilano/Caplilano_08GA010_day_avg_flow"
        )

    def test_rivers_climatology(self, prod_config):
        climatolgies = prod_config["rivers"]["bathy params"]["v201702"]
        assert (
            climatolgies["Fraser climatology"]
            == "/SalishSeaCast/tools/I_ForcingFiles/Rivers/FraserClimatologySeparation.yaml"
        )
        assert (
            climatolgies["monthly climatology"]
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
