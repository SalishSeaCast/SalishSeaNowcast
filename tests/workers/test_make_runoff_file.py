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


"""Unit tests for SalishSeaCast make_runoff_file worker."""
from pathlib import Path
import textwrap
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_runoff_file


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                rivers:
                  rivers dir: forcing/rivers/
                  file templates:
                    b201702: 'R201702DFraCElse_{:y%Ym%md%d}.nc'
                  monthly climatology:
                    b201702: rivers-climatology/rivers_month_201702.nc
                  prop_dict modules:
                    b201702: salishsea_tools.river_201702
                  SOG river files:
                    Fraser: SOG-forcing/ECget/Fraser_flow
                  Fraser climatology: tools/I_ForcingFiles/Rivers/FraserClimatologySeparation.yaml
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(make_runoff_file, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = make_runoff_file.main()
        assert worker.name == "make_runoff_file"
        assert worker.description.startswith(
            "SalishSeaCast runoff file generation worker."
        )

    def test_add_run_date_option(self, mock_worker):
        worker = make_runoff_file.main()
        assert worker.cli.parser._actions[3].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[3].type == expected
        assert worker.cli.parser._actions[3].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[3].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_runoff_file" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["make_runoff_file"]
        assert msg_registry["checklist key"] == "rivers forcing"

    @pytest.mark.parametrize("msg", ("success", "failure", "crash"))
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["make_runoff_file"]
        assert msg in msg_registry

    def test_rivers_sections(self, prod_config):
        rivers = prod_config["rivers"]
        assert rivers["file templates"]["b201702"] == "R201702DFraCElse_{:y%Ym%md%d}.nc"
        assert rivers["rivers dir"] == "/results/forcing/rivers/"
        assert rivers["prop_dict modules"]["b201702"] == "salishsea_tools.river_201702"
        assert (
            rivers["SOG river files"]["Capilano"]
            == "/opp/observations/rivers/Capilano/Caplilano_08GA010_day_avg_flow"
        )

    def test_rivers_climatology(self, prod_config):
        assert (
            prod_config["rivers"]["Fraser climatology"]
            == "/SalishSeaCast/tools/I_ForcingFiles/Rivers/FraserClimatologySeparation.yaml"
        )
        assert (
            prod_config["rivers"]["monthly climatology"]["b201702"]
            == "/SalishSeaCast/rivers-climatology/rivers_month_201702.nc"
        )


@patch("nowcast.workers.make_runoff_file.logger", autospec=True)
class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-05-17"))
        msg_type = make_runoff_file.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == "success"


@patch("nowcast.workers.make_runoff_file.logger", autospec=True)
class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-05-17"))
        msg_type = make_runoff_file.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == "failure"
