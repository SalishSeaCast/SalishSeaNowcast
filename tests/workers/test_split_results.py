#  Copyright 2013-2019 The Salish Sea MEOPAR contributors
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
"""Unit tests for Salish Sea NEMO nowcast split_results worker.
"""
import logging
from types import SimpleNamespace

import arrow
import attr
import nemo_nowcast
import pytest

from nowcast.workers import split_results


@pytest.fixture
def mock_worker(monkeypatch):
    @attr.s
    class MockWorker:
        name = attr.ib()
        description = attr.ib()
        package = attr.ib(default="nowcast.workers")
        cli = attr.ib(default=None)

        def init_cli(self):
            pass

        def run(self, *args):
            pass

    monkeypatch.setattr(MockWorker, "init_cli", nemo_nowcast.NowcastWorker.init_cli)
    monkeypatch.setattr(split_results, "NowcastWorker", MockWorker)


class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, mock_worker):
        worker = split_results.main()
        assert worker.name == "split_results"
        assert worker.description.startswith(
            "SalishSeaCast worker that splits downloaded results of multi-day runs"
        )

    def test_add_run_type_arg(self, mock_worker):
        worker = split_results.main()
        assert worker.cli.parser._actions[3].dest == "run_type"
        assert worker.cli.parser._actions[3].choices == {"hindcast"}
        assert worker.cli.parser._actions[3].help

    def test_add_run_date_arg(self, mock_worker):
        worker = split_results.main()
        assert worker.cli.parser._actions[4].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface._arrow_date
        assert worker.cli.parser._actions[4].type == expected
        assert worker.cli.parser._actions[4].help


class TestSuccess:
    """Unit test for success() function.
    """

    def test_success(self, caplog):
        parsed_args = SimpleNamespace(
            run_type="hindcast", run_date=arrow.get("2019-10-27")
        )
        caplog.set_level(logging.INFO)
        msg_type = split_results.success(parsed_args)
        assert caplog.records[0].levelname == "INFO"
        assert "results files split into daily directories" in caplog.messages[0]
        assert msg_type == "success hindcast"


class TestFailure:
    """Unit test for failure() function.
    """

    def test_failure(self, caplog):
        parsed_args = SimpleNamespace(
            run_type="hindcast", run_date=arrow.get("2019-10-27")
        )
        caplog.set_level(logging.CRITICAL)
        msg_type = split_results.failure(parsed_args)
        assert caplog.records[0].levelname == "CRITICAL"
        assert "results files splitting failed" in caplog.messages[0]
        assert msg_type == "failure hindcast"
