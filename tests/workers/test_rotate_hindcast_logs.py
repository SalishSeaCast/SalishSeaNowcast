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


"""Unit tests for SalishSeaCast rotate_hindcast_logs worker.
"""
import logging
import logging.config
import textwrap
from pathlib import Path
from types import SimpleNamespace

import nemo_nowcast
import pytest

from nowcast.workers import rotate_hindcast_logs


@pytest.fixture()
def config(base_config, tmp_path):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                f"""\
                logging:
                  aggregator:
                    handlers: {{}}
                  publisher:
                    version: 1
                    disable_existing_loggers: False
                    formatters:
                      simple:
                        format: '%(asctime)s %(levelname)s [%(name)s] %(message)s'
                    handlers:
                      hindcast_info:
                        class: logging.handlers.RotatingFileHandler
                        level: INFO
                        formatter: simple
                        filename: {tmp_path}/hindcast.log
                      hindcast_debug:
                        class: logging.handlers.RotatingFileHandler
                        level: DEBUG
                        formatter: simple
                        filename: {tmp_path}/hindcast.debug.log
                    loggers:
                      run_NEMO_hindcast:
                        qualname: run_NEMO_hindcast
                        level: DEBUG
                        propagate: False
                        handlers:
                          - hindcast_info
                          - hindcast_debug
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(rotate_hindcast_logs, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit test for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = rotate_hindcast_logs.main()
        assert worker.name == "rotate_hindcast_logs"
        assert worker.description.startswith(
            "SalishSeaCast worker that rotates hindcast processing logs"
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "rotate_hindcast_logs" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"][
            "rotate_hindcast_logs"
        ]
        assert msg_registry["checklist key"] == "hindcast log rotation"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "rotate_hindcast_logs"
        ]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success",
            "failure",
            "crash",
        ]

    @pytest.mark.parametrize(
        "name, level, filename",
        (
            ("hindcast_info", "INFO", "hindcast.log"),
            ("hindcast_debug", "DEBUG", "hindcast.debug.log"),
        ),
    )
    def test_logging_publisher_handlers(
        self, name, level, filename, prod_config, tmp_path
    ):
        handlers = prod_config["logging"]["publisher"]["handlers"]
        assert handlers[name]["class"] == "logging.handlers.RotatingFileHandler"
        assert handlers[name]["level"] == level
        assert handlers[name]["formatter"] == "simple"
        assert handlers[name]["filename"] == f"{tmp_path/'nowcast_logs'/filename}"
        assert handlers[name]["backupCount"] == 7

    @pytest.mark.parametrize("name", ("run_NEMO_hindcast", "watch_NEMO_hindcast"))
    def test_logging_publisher_loggers(self, name, prod_config, tmp_path):
        loggers = prod_config["logging"]["publisher"]["loggers"]
        assert loggers[name]["qualname"] == name
        assert loggers[name]["level"] == "DEBUG"
        assert loggers[name]["propagate"] is False
        assert loggers[name]["handlers"] == ["hindcast_info", "hindcast_debug"]


class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, caplog):
        parsed_args = SimpleNamespace()
        caplog.set_level(logging.INFO)
        msg_type = rotate_hindcast_logs.success(parsed_args)
        assert caplog.records[0].levelname == "INFO"
        assert caplog.messages[0] == "hindcast log files rotated"
        assert msg_type == "success"


class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, caplog):
        parsed_args = SimpleNamespace()
        caplog.set_level(logging.CRITICAL)
        msg_type = rotate_hindcast_logs.failure(parsed_args)
        assert caplog.records[0].levelname == "CRITICAL"
        assert caplog.messages[0] == "failed to rotate hindcast log files"
        assert msg_type == "failure"


class TestRotateHindcastLogs:
    """Unit tests for rotate_hindcast_logs() function."""

    def test_checklist(self, config, tmp_path):
        logging.config.dictConfig(config["logging"]["publisher"])
        parsed_args = SimpleNamespace()
        checklist = rotate_hindcast_logs.rotate_hindcast_logs(parsed_args, config)
        expected = {
            "hindcast log files": [
                f"{tmp_path}/hindcast.log",
                f"{tmp_path}/hindcast.debug.log",
            ]
        }
        assert checklist == expected
