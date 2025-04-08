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


"""Fixtures for SalishSeaCast test suite."""
from pathlib import Path
import textwrap
from typing import Mapping
from unittest.mock import patch

import attr
import nemo_nowcast
import pytest
import structlog


@pytest.fixture()
def base_config(tmp_path: Path) -> nemo_nowcast.Config | Mapping:
    """:py:class:`nemo_nowcast.Config` instance from a YAML fragment containing the elements
    required by all unit tests.
    """
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        textwrap.dedent(
            """
            # Items required by the Config instance
            checklist file: nowcast_checklist.yaml
            python: python
            logging:
              handlers: []

            """
        )
    )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture()
def prod_config(tmp_path):
    """:py:class:`nemo_nowcast.Config` instance from the production config YAML file to use for
    testing its contents.
    """
    prod_config_ = nemo_nowcast.Config()
    p_logs_dir = tmp_path / "nowcast_logs"
    p_logs_dir.mkdir()
    p_env_dir = tmp_path / "nowcast-env"
    p_env_dir.mkdir()
    p_environ = patch.dict(
        nemo_nowcast.config.os.environ,
        {"NOWCAST_LOGS": str(p_logs_dir), "NOWCAST_ENV": str(p_env_dir)},
    )
    prod_config_file = (Path(__file__).parent / "../config/nowcast.yaml").resolve()
    with p_environ:
        prod_config_.load(prod_config_file)
    return prod_config_


@pytest.fixture
def mock_nowcast_worker(monkeypatch):
    """Mock of :py:class:`nemo_nowcast.NowcastWorker` class for testing worker main()
    functions, especially their CLIs.
    """

    @attr.s
    class MockNowcastWorker:
        name = attr.ib()
        description = attr.ib()
        package = attr.ib(default="nowcast.workers")
        cli = attr.ib(default=None)

        def init_cli(self):
            pass

        def run(self, *args):
            pass

    monkeypatch.setattr(
        MockNowcastWorker, "init_cli", nemo_nowcast.NowcastWorker.init_cli
    )
    return MockNowcastWorker


@pytest.fixture(name="log_output")
def fixture_log_output():
    """Capture structlog log output from Reshapr for testing.

    Reference: https://www.structlog.org/en/stable/testing.html
    """
    return structlog.testing.LogCapture()


@pytest.fixture(autouse=True)
def fixture_configure_structlog(log_output):
    """Configure structlog log capture fixture.

    Reference: https://www.structlog.org/en/stable/testing.html
    """
    structlog.configure(processors=[log_output])
