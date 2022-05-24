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


"""Unit tests for SalishSeaCast archive_tarball worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import archive_tarball


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                results archive:
                  nowcast: SalishSea/nowcast/
                  nowcast-green: SalishSea/nowcast-green/
                  nowcast-agrif: SalishSea/nowcast-agrif/

                results tarballs:
                  temporary tarball dir: ocean/dlatorne/
                  graham-dtn: /nearline/rrg-allen/SalishSea/
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(archive_tarball, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = archive_tarball.main()
        assert worker.name == "archive_tarball"
        assert worker.description.startswith(
            "SalishSeaCast worker that creates a tarball of a month's run results"
        )

    def test_add_run_type_arg(self, mock_worker):
        worker = archive_tarball.main()
        assert worker.cli.parser._actions[3].dest == "run_type"
        expected = {
            "nowcast",
            "nowcast-green",
            "nowcast-agrif",
        }
        assert worker.cli.parser._actions[3].choices == expected
        assert worker.cli.parser._actions[3].help

    def test_add_yyyy_mmm_arg(self, mock_worker):
        worker = archive_tarball.main()
        assert worker.cli.parser._actions[4].dest == "yyyy_mmm"
        assert worker.cli.parser._actions[4].type == archive_tarball._arrow_yyyy_mmm
        assert worker.cli.parser._actions[4].help

    def test_add_dest_host_arg(self, mock_worker):
        worker = archive_tarball.main()
        assert worker.cli.parser._actions[5].dest == "dest_host"
        assert worker.cli.parser._actions[5].default == "graham-dtn"
        assert worker.cli.parser._actions[5].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "archive_tarball" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["archive_tarball"]
        assert msg_registry["checklist key"] == "archived tarballs"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["archive_tarball"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success nowcast",
            "failure nowcast",
            "success nowcast-green",
            "failure nowcast-green",
            "success nowcast-agrif",
            "failure nowcast-agrif",
            "crash",
        ]

    def test_results_tarballs(self, prod_config):
        assert prod_config["results tarballs"]["temporary tarball dir"] == "/ocean/dlatorne/"

    @pytest.mark.parametrize("run_type, results_path", (
        ("nowcast", "/results/SalishSea/nowcast-blue.201905/"),
        ("nowcast-green", "/results2/SalishSea/nowcast-green.201905/"),
        ("nowcast-agrif", "/results/SalishSea/nowcast-agrif.201702/"),

    ))
    def test_results_archive(self, run_type, results_path, prod_config):
        assert prod_config["results archive"][run_type] == results_path


@pytest.mark.parametrize(
    "run_type",
    [
        "nowcast",
        "nowcast-green",
        "nowcast-agrif",
    ],
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, run_type, caplog):
        yyyy_mmm = arrow.get("2022-may", "YYYY-MMM")
        dest_host = "graham-dtn"
        parsed_args = SimpleNamespace(run_type=run_type, yyyy_mmm=yyyy_mmm, dest_host=dest_host)
        caplog.set_level(logging.INFO)
        msg_type = archive_tarball.success(parsed_args)
        assert caplog.records[0].levelname == "INFO"
        expected = (
            f"{run_type} {yyyy_mmm.format('*MMMYY').lower()} "
            f"results files archived to {dest_host}"
        )
        assert caplog.messages[0] == expected
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize(
    "run_type",
    [
        "nowcast",
        "nowcast-green",
        "nowcast-agrif",
    ],
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, run_type, caplog):
        yyyy_mmm = arrow.get("2022-may", "YYYY-MMM")
        dest_host = "graham-dtn"
        parsed_args = SimpleNamespace(run_type=run_type, yyyy_mmm=yyyy_mmm, dest_host=dest_host)
        caplog.set_level(logging.CRITICAL)
        msg_type = archive_tarball.failure(parsed_args)
        assert caplog.records[0].levelname == "CRITICAL"
        expected = (
            f"{run_type} {yyyy_mmm.format('*MMMYY').lower()} "
            f"results files archiving to {dest_host} failed"
        )
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {run_type}"


class TestArchiveTarball:
    """Unit tests for archive_tarball() function."""

    def test_checklist(self, config, caplog, monkeypatch):
        def mock_create_tarball(tarball, results_path_pattern):
            pass

        monkeypatch.setattr(archive_tarball, "_create_tarball", mock_create_tarball)

        def mock_create_tarball_index(tarball):
            pass

        monkeypatch.setattr(archive_tarball, "_create_tarball_index", mock_create_tarball_index)

        yyyy_mmm = arrow.get("2022-may", "YYYY-MMM")
        parsed_args = SimpleNamespace(run_type="nowcast-green", yyyy_mmm=yyyy_mmm, dest_host="graham-dtn")
        caplog.set_level(logging.INFO)
        checklist = archive_tarball.archive_tarball(parsed_args, config)
        assert caplog.records[0].levelname == "INFO"
        expected = (
            "creating ocean/dlatorne/nowcast-green-may22.tar from SalishSea/nowcast-green/*may22/"
        )
        assert caplog.messages[0] == expected
        expected = (
            "creating ocean/dlatorne/nowcast-green-may22.index from "
            "ocean/dlatorne/nowcast-green-may22.tar"
        )
        assert caplog.messages[1] == expected
        expected = {
            "tarball archived": {
                "tarball": "ocean/dlatorne/nowcast-green-may22.tar",
                "index": "ocean/dlatorne/nowcast-green-may22.index",
            }
        }
        assert checklist == expected
