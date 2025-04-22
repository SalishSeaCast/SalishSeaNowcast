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


"""Unit tests for SalishSeaCast make_turbidity_file worker."""
import logging
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_turbidity_file


@pytest.fixture
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    return base_config


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(make_turbidity_file, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = make_turbidity_file.main()
        assert worker.name == "make_turbidity_file"
        assert worker.description.startswith(
            "SalishSeaCast worker that produces daily average Fraser River"
        )

    def test_add_run_date_option(self, mock_worker):
        worker = make_turbidity_file.main()
        assert worker.cli.parser._actions[3].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[3].type == expected
        assert worker.cli.parser._actions[3].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[3].help


class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, caplog):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-07-08"))
        caplog.set_level(logging.DEBUG)

        msg_type = make_turbidity_file.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = "2017-07-08 Fraser River turbidity file creation complete"
        assert caplog.records[0].message == expected
        assert msg_type == "success"


class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, caplog):
        parsed_args = SimpleNamespace(run_date=arrow.get("2017-07-08"))
        caplog.set_level(logging.DEBUG)

        msg_type = make_turbidity_file.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = "2017-07-08 Fraser River turbidity file creation failed"
        assert caplog.records[0].message == expected
        assert msg_type == "failure"
