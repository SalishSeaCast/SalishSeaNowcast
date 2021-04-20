#  Copyright 2013-2021 The Salish Sea MEOPAR contributors
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
"""Unit tests for SalishSeaCast make_ssh_file worker.
"""
import logging
import os
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_ssh_file


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                ssh:
                  download:
                    tar file template: 'etss.{yyyymmdd}.t{forecast}z.csv_tar'

                  tidal predictions: /SalishSeaCast/SalishSeaNowcast/tidal_predictions/
                  neah bay hourly: Neah Bay Hourly_tidal_prediction_30-Dec-2006_31-Dec-2030.csv
                  ssh dir: /results/forcing/sshNeahBay/
                  
                results archive:
                  nowcast: /results/SalishSea/nowcast-blue.201905/
                  forecast2: /results/SalishSea/forecast2.201905/
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(make_ssh_file, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = make_ssh_file.main()
        assert worker.name == "make_ssh_file"
        assert worker.description.startswith(
            "SalishSeaCast worker that generates a sea surface height boundary conditions file"
        )

    def test_add_run_type_arg(self, mock_worker):
        worker = make_ssh_file.main()
        assert worker.cli.parser._actions[3].dest == "run_type"
        assert worker.cli.parser._actions[3].choices == {"nowcast", "forecast2"}
        assert worker.cli.parser._actions[3].help

    def test_add_run_date_option(self, mock_worker):
        worker = make_ssh_file.main()
        assert worker.cli.parser._actions[4].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[4].type == expected
        assert worker.cli.parser._actions[4].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[4].help

    def test_add_text_file_option(self, mock_worker):
        worker = make_ssh_file.main()
        assert worker.cli.parser._actions[5].dest == "text_file"
        assert worker.cli.parser._actions[5].type == Path
        assert worker.cli.parser._actions[5].help

    def test_add_archive_option(self, mock_worker):
        worker = make_ssh_file.main()
        assert worker.cli.parser._actions[6].dest == "archive"
        assert worker.cli.parser._actions[6].default is False
        assert worker.cli.parser._actions[6].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_ssh_file" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["make_ssh_file"]
        assert msg_registry["checklist key"] == "sea surface height forcing"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["make_ssh_file"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success nowcast",
            "failure nowcast",
            "success forecast2",
            "failure forecast2",
            "crash",
        ]

    def test_file_group(self, prod_config):
        assert prod_config["file group"] == "sallen"

    def test_ssh_section(self, prod_config):
        ssh = prod_config["ssh"]
        assert ssh["tidal predictions"] == "/SalishSeaCast/SalishSeaNowcast/tidal_predictions/"
        assert ssh["neah bay hourly"] == "Neah Bay Hourly_tidal_prediction_30-Dec-2006_31-Dec-2030.csv"
        assert ssh["ssh dir"] == "/results/forcing/sshNeahBay/"

    def test_ssh_download_section(self, prod_config):
        ssh_download = prod_config["ssh"]["download"]
        assert (
            ssh_download["tar file template"] == "etss.{yyyymmdd}.t{forecast}z.csv_tar"
        )

    def test_results_archive_section(self, prod_config):
        results_archive = prod_config["results archive"]
        assert results_archive["nowcast"] == "/results/SalishSea/nowcast-blue.201905/"
        assert results_archive["forecast2"] == "/results/SalishSea/forecast2.201905/"


@pytest.mark.parametrize(
    "run_type, run_date",
    (
        ("nowcast", "2021-04-19"),
        ("forecast2", "2021-04-19"),
    ),
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, run_type, run_date, caplog):
        parsed_args = SimpleNamespace(run_type=run_type, run_date=arrow.get(run_date))
        caplog.set_level(logging.DEBUG)

        msg_type = make_ssh_file.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"sea surface height boundary file for {run_date.format('YYYY-MM-DD')} {run_type} run created"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize(
    "run_type, run_date",
    (
        ("nowcast", "2021-04-19"),
        ("forecast2", "2021-04-19"),
    ),
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, run_type, run_date, caplog):
        parsed_args = SimpleNamespace(run_type=run_type, run_date=arrow.get(run_date))
        caplog.set_level(logging.DEBUG)

        msg_type = make_ssh_file.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"sea surface height boundary file for {run_date.format('YYYY-MM-DD')} {run_type} run creation failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {run_type}"


@pytest.mark.parametrize(
    "run_type, run_date",
    (
        ("nowcast", "2021-04-19"),
        ("forecast2", "2021-04-19"),
    ),
)
class TestMakeSshFile:
    """Unit tests for make_ssh_file() function."""

    def test_checklist(self, run_type, run_date, config, caplog, monkeypatch):
        def mock_copy_csv_to_results_dir(data_file, run_date, run_type, config):
            pass

        monkeypatch.setattr(
            make_ssh_file, "_copy_csv_to_results_dir", mock_copy_csv_to_results_dir
        )
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get(run_date), text_file=None, archive=False,
        )
        caplog.set_level(logging.DEBUG)

        checklist = make_ssh_file.make_ssh_file(parsed_args, config)

        ssh_dir = Path(config["ssh"]["ssh dir"])
        yyyymmdd = arrow.get(run_date).format("YYYYMMDD")
        forecast = "12" if run_type == "nowcast" else "00"
        csv_file = Path(f"etss.{yyyymmdd}.t{forecast}z.csv")
        expected = {run_type: {"csv": os.fspath(ssh_dir / "txt" / csv_file)}}
        assert checklist == expected
