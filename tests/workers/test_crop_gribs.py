#  Copyright 2013 – present by the SalishSeaCast Project contributors
#  and The University of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# SPDX-License-Identifier: Apache-2.0


"""Unit test for SalishSeaCast crop_gribs worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import crop_gribs


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                weather:
                  download:
                    2.5 km:
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(crop_gribs, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = crop_gribs.main()
        assert worker.name == "crop_gribs"
        assert worker.description.startswith(
            "SalishSeaCast worker that loads ECCC MSC 2.5 km rotated lat-lon continental grid "
        )

    def test_add_forecast_arg(self, mock_worker):
        worker = crop_gribs.main()
        assert worker.cli.parser._actions[3].dest == "forecast"
        assert worker.cli.parser._actions[3].choices == {"00", "06", "12", "18"}
        assert worker.cli.parser._actions[3].help

    def test_add_forecast_date_option(self, mock_worker):
        worker = crop_gribs.main()
        assert worker.cli.parser._actions[4].dest == "fcst_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[4].type == expected
        assert worker.cli.parser._actions[4].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[4].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "crop_gribs" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["crop_gribs"]
        assert msg_registry["checklist key"] == "weather forecast"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["crop_gribs"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success 00",
            "failure 00",
            "success 06",
            "failure 06",
            "success 12",
            "failure 12",
            "success 18",
            "failure 18",
            "crash",
        ]


@pytest.mark.parametrize(
    "forecast, forecast_date",
    (
        ("00", "2023-04-02"),
        ("06", "2023-04-02"),
        ("12", "2023-04-02"),
        ("18", "2023-04-02"),
    ),
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, forecast, forecast_date, caplog):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            fcst_date=forecast_date,
        )
        caplog.set_level(logging.DEBUG)

        msg_type = crop_gribs.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"{forecast_date} {forecast} GRIBs cropping complete"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {forecast}"


@pytest.mark.parametrize(
    "forecast, forecast_date",
    (
        ("00", "2023-04-02"),
        ("06", "2023-04-02"),
        ("12", "2023-04-02"),
        ("18", "2023-04-02"),
    ),
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, forecast, forecast_date, caplog):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            fcst_date=forecast_date,
        )
        caplog.set_level(logging.DEBUG)

        msg_type = crop_gribs.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"{forecast_date} {forecast} GRIBs cropping failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {forecast}"


class TestCropGribs:
    """Unit tests for crop_gribs() function."""

    def test_crop_gribs(self):
        # TODO: test something
        pass
