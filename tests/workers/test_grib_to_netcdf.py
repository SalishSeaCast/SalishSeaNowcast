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


"""Unit tests for SalishSeaCast grib_to_netcdf worker.
"""
import logging
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import grib_to_netcdf


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    return base_config


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(grib_to_netcdf, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = grib_to_netcdf.main()
        assert worker.name == "grib_to_netcdf"
        assert worker.description.startswith(
            "SalishSeaCast worker that generates weather forcing file from GRIB2 forecast files."
        )

    def test_add_run_type_arg(self, mock_worker):
        worker = grib_to_netcdf.main()
        assert worker.cli.parser._actions[3].dest == "run_type"
        assert worker.cli.parser._actions[3].choices == {"nowcast+", "forecast2"}
        assert worker.cli.parser._actions[3].help

    def test_add_run_date_option(self, mock_worker):
        worker = grib_to_netcdf.main()
        assert worker.cli.parser._actions[4].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[4].type == expected
        assert worker.cli.parser._actions[4].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[4].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "grib_to_netcdf" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["grib_to_netcdf"]
        assert msg_registry["checklist key"] == "weather forcing"

    @pytest.mark.parametrize(
        "msg",
        (
            "success nowcast+",
            "failure nowcast+",
            "success forecast2",
            "failure forecast2",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["grib_to_netcdf"]
        assert msg in msg_registry

    def test_file_group_item(self, prod_config):
        assert "file group" in prod_config

    def test_weather_section(self, prod_config):
        weather = prod_config["weather"]
        assert weather["wgrib2"] == "/SalishSeaCast/private-tools/grib2/wgrib2/wgrib2"
        assert (
            weather["grid_defn.pl"]
            == "/SalishSeaCast/private-tools/PThupaki/grid_defn.pl"
        )
        assert weather["ops dir"] == "/results/forcing/atmospheric/GEM2.5/operational/"
        assert (
            weather["monitoring image"]
            == "/results/nowcast-sys/figures/monitoring/wg.png"
        )

    def test_weather_download_2_5_km_section(self, prod_config):
        weather_download = prod_config["weather"]["download"]["2.5 km"]
        assert (
            weather_download["GRIB dir"]
            == "/results/forcing/atmospheric/continental2.5/GRIB/"
        )


@pytest.mark.parametrize("run_type", ("nowcast+", "forecast2"))
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, run_type, caplog):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2023-02-26")
        )
        caplog.set_level(logging.DEBUG)

        msg_type = grib_to_netcdf.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"2023-02-26 NEMO-atmos forcing file for {run_type} created"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ("nowcast+", "forecast2"))
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, run_type, caplog):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2023-02-26")
        )
        caplog.set_level(logging.DEBUG)

        msg_type = grib_to_netcdf.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"2023-02-26 NEMO-atmos forcing file creation for {run_type} failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {run_type}"
