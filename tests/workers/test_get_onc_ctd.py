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


"""Unit tests for SalishSeaCast get_onc_ctd worker."""
import logging
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import get_onc_ctd


@pytest.fixture
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    return base_config


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(get_onc_ctd, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = get_onc_ctd.main()
        assert worker.name == "get_onc_ctd"
        assert worker.description.startswith(
            "Salish Sea nowcast worker that downloads CTD temperature and salinity data"
        )

    def test_add_onc_station_arg(self, mock_worker):
        worker = get_onc_ctd.main()
        assert worker.cli.parser._actions[3].dest == "onc_station"
        assert worker.cli.parser._actions[3].choices == {"SCVIP", "SEVIP", "USDDL"}
        assert worker.cli.parser._actions[3].help

    def test_add_run_date_option(self, mock_worker):
        worker = get_onc_ctd.main()
        assert worker.cli.parser._actions[4].dest == "data_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[4].type == expected
        expected = arrow.utcnow().floor("day").shift(days=-1)
        assert worker.cli.parser._actions[4].default == expected
        assert worker.cli.parser._actions[4].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "get_onc_ctd" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["get_onc_ctd"]
        assert msg_registry["checklist key"] == "ONC CTD data"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["get_onc_ctd"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success SCVIP",
            "success SEVIP",
            "success USDDL",
            "failure",
            "crash",
        ]

    def test_obs_ctd_data_section(self, prod_config):
        ctd_data = prod_config["observations"]["ctd data"]
        assert ctd_data["dest dir"] == "/results/observations/ONC/CTD/"
        expected = "{station}/{station}_CTD_15m_{yyyymmdd}.nc"
        assert ctd_data["filepath template"] == expected


@pytest.mark.parametrize("onc_station", ["SCVIP", "SEVIP", "USDDL"])
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, onc_station, caplog):
        parsed_args = SimpleNamespace(
            onc_station=onc_station, data_date=arrow.get("2016-09-09")
        )
        caplog.set_level(logging.DEBUG)

        msg_type = get_onc_ctd.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"2016-09-09 ONC {onc_station} CTD T&S file created"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {onc_station}"


@pytest.mark.parametrize("onc_station", ["SCVIP", "SEVIP", "USDDL"])
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, onc_station, caplog):
        parsed_args = SimpleNamespace(
            onc_station=onc_station, data_date=arrow.get("2016-09-09")
        )
        caplog.set_level(logging.DEBUG)

        msg_type = get_onc_ctd.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"2016-09-09 ONC {onc_station} CTD T&S file creation failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure"
