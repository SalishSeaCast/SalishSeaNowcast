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


"""Unit tests for SalishSeaCast collect_NeahBay_ssh worker.
"""
import logging
import os
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import collect_NeahBay_ssh


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
                    url template: 'https://nomads.ncep.noaa.gov/pub/data/nccf/com/etss/prod/etss.{yyyymmdd}/etss.t{forecast}z.csv_tar'
                    tar file template: 'etss.{yyyymmdd}.t{forecast}z.csv_tar'
                    tarball csv file template: 'etss.{yyyymmdd}/t{forecast}z_csv/9443090.csv'

                  ssh dir: /results/forcing/sshNeahBay/
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(collect_NeahBay_ssh, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = collect_NeahBay_ssh.main()
        assert worker.name == "collect_NeahBay_ssh"
        assert worker.description.startswith(
            "SalishSeaCast worker that collects a file containing sea surface height observations"
        )

    def test_add_forecast_arg(self, mock_worker):
        worker = collect_NeahBay_ssh.main()
        assert worker.cli.parser._actions[3].dest == "forecast"
        assert worker.cli.parser._actions[3].choices == {"00", "06", "12", "18"}
        assert worker.cli.parser._actions[3].help

    def test_add_data_date_option(self, mock_worker):
        worker = collect_NeahBay_ssh.main()
        assert worker.cli.parser._actions[4].dest == "data_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[4].type == expected
        assert worker.cli.parser._actions[4].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[4].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "collect_NeahBay_ssh" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["collect_NeahBay_ssh"]
        assert msg_registry["checklist key"] == "Neah Bay ssh data"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["collect_NeahBay_ssh"]
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

    def test_ssh_section(self, prod_config):
        ssh = prod_config["ssh"]
        assert ssh["ssh dir"] == "/results/forcing/sshNeahBay/"

    def test_ssh_download_section(self, prod_config):
        ssh_download = prod_config["ssh"]["download"]
        assert (
            ssh_download["url template"]
            == "https://nomads.ncep.noaa.gov/pub/data/nccf/com/etss/prod/etss.{yyyymmdd}/etss.t{forecast}z.csv_tar"
        )
        assert (
            ssh_download["tar file template"] == "etss.{yyyymmdd}.t{forecast}z.csv_tar"
        )
        assert (
            ssh_download["tarball csv file template"]
            == "etss.{yyyymmdd}/t{forecast}z_csv/9443090.csv"
        )


@pytest.mark.parametrize(
    "forecast, data_date",
    (
        ("00", "2021-04-12"),
        ("06", "2021-04-12"),
        ("12", "2021-04-13"),
        ("18", "2021-04-14"),
    ),
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, forecast, data_date, caplog):
        parsed_args = SimpleNamespace(forecast=forecast, data_date=data_date)
        caplog.set_level(logging.DEBUG)

        msg_type = collect_NeahBay_ssh.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"{data_date} Neah Bay ssh {forecast}Z obs/forecast data collection complete"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {forecast}"


@pytest.mark.parametrize(
    "forecast, data_date",
    (
        ("00", "2021-04-12"),
        ("06", "2021-04-12"),
        ("12", "2021-04-13"),
        ("18", "2021-04-14"),
    ),
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, forecast, data_date, caplog):
        parsed_args = SimpleNamespace(forecast=forecast, data_date=data_date)
        caplog.set_level(logging.DEBUG)

        msg_type = collect_NeahBay_ssh.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = (
            f"{data_date} Neah Bay ssh {forecast}Z obs/forecast data collection failed"
        )
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {forecast}"


class TestCollectNeahBaySsh:
    """Unit tests for collect_NeahBay_ssh() function."""

    @pytest.mark.parametrize(
        "forecast, data_date",
        (
            ("00", "2021-04-12"),
            ("06", "2021-04-12"),
            ("12", "2021-04-13"),
            ("18", "2021-04-14"),
        ),
    )
    def test_checklist(self, forecast, data_date, config, caplog, monkeypatch):
        def mock_get_web_data(tar_url, logger_name, filepath):
            pass

        monkeypatch.setattr(collect_NeahBay_ssh, "get_web_data", mock_get_web_data)

        def mock_os_stat(path):
            return SimpleNamespace(st_size=43)

        monkeypatch.setattr(collect_NeahBay_ssh.os, "stat", mock_os_stat)

        def mock_extract_csv(tar_csv_member, tar_file_path, csv_file_path):
            pass

        monkeypatch.setattr(collect_NeahBay_ssh, "_extract_csv", mock_extract_csv)

        parsed_args = SimpleNamespace(forecast=forecast, data_date=arrow.get(data_date))
        caplog.set_level(logging.DEBUG)

        checklist = collect_NeahBay_ssh.collect_NeahBay_ssh(parsed_args, config)

        ssh_dir = Path(config["ssh"]["ssh dir"])
        yyyymmdd = arrow.get(data_date).format("YYYYMMDD")
        csv_file = Path(f"etss.{yyyymmdd}.t{forecast}z.csv")
        expected = {
            "data date": data_date,
            f"{forecast}": os.fspath(ssh_dir / "txt" / csv_file),
        }
        assert checklist == expected
