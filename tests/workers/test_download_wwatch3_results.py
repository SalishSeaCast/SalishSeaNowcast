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


"""Unit tests for SalishSeaCast system download_wwatch3_results worker."""
import logging
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import download_wwatch3_results


@pytest.fixture
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    return base_config


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(download_wwatch3_results, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = download_wwatch3_results.main()
        assert worker.name == "download_wwatch3_results"
        assert worker.description.startswith(
            "SalishSeaCast system worker that downloads the results files\nfrom a WaveWatch3 run"
        )

    def test_add_host_name_arg(self, mock_worker):
        worker = download_wwatch3_results.main()
        assert worker.cli.parser._actions[3].dest == "host_name"
        assert worker.cli.parser._actions[3].help

    def test_add_run_type_arg(self, mock_worker):
        worker = download_wwatch3_results.main()
        assert worker.cli.parser._actions[4].dest == "run_type"
        assert worker.cli.parser._actions[4].choices == {
            "nowcast",
            "forecast",
            "forecast2",
        }
        assert worker.cli.parser._actions[4].help

    def test_add_run_date_option(self, mock_worker):
        worker = download_wwatch3_results.main()
        assert worker.cli.parser._actions[5].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[5].type == expected
        assert worker.cli.parser._actions[5].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[5].help


@pytest.mark.parametrize(
    "run_type, host_name",
    [
        ("nowcast", "arbutus.cloud-nowcast"),
        ("forecast", "arbutus.cloud-nowcast"),
        ("forecast2", "arbutus.cloud-nowcast"),
    ],
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, run_type, host_name, caplog):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2025-03-18")
        )
        caplog.set_level(logging.DEBUG)

        msg_type = download_wwatch3_results.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"{run_type} 2025-03-18 results files from {host_name} downloaded"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize(
    "run_type, host_name",
    [
        ("nowcast", "arbutus.cloud-nowcast"),
        ("forecast", "arbutus.cloud-nowcast"),
        ("forecast2", "arbutus.cloud-nowcast"),
    ],
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, run_type, host_name, caplog):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2025-03-18")
        )
        caplog.set_level(logging.DEBUG)

        msg_type = download_wwatch3_results.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = (
            f"{run_type} 2025-03-18 results files download from {host_name} failed"
        )
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {run_type}"
