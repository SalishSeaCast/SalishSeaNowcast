#  Copyright 2013-2020 The Salish Sea MEOPAR contributors
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
"""Unit tests for SalishSeaCast download_live_ocean worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import download_live_ocean


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                file group: allen
                
                temperature salinity:
                  download:
                    url: https://pm2.blob.core.windows.net/
                    directory prefix: f
                    file name: 'low_passed_UBC.nc'
                    dest dir: /results/forcing/LiveOcean/downloaded
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(download_live_ocean, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = download_live_ocean.main()
        assert worker.name == "download_live_ocean"
        assert worker.description.startswith(
            "SalishSeaCast worker that downloads a daily averaged file from the"
        )

    def test_add_run_date_option(self, mock_worker):
        worker = download_live_ocean.main()
        assert worker.cli.parser._actions[3].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[3].type == expected
        assert worker.cli.parser._actions[3].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[3].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "download_live_ocean" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["download_live_ocean"]
        assert msg_registry["checklist key"] == "Live Ocean products"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["download_live_ocean"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success",
            "failure",
            "crash",
        ]

    def test_download_url(self, prod_config):
        download_url = prod_config["temperature salinity"]["download"]["url"]
        assert download_url == "https://pm2.blob.core.windows.net/"

    def test_download_dir_prefix(self, prod_config):
        download_url = prod_config["temperature salinity"]["download"][
            "directory prefix"
        ]
        assert download_url == "f"

    def test_download_file_name(self, prod_config):
        download_url = prod_config["temperature salinity"]["download"]["file name"]
        assert download_url == "low_passed_UBC.nc"

    def test_download_dest_dir(self, prod_config):
        download_url = prod_config["temperature salinity"]["download"]["dest dir"]
        assert download_url == "/results/forcing/LiveOcean/downloaded/"

    def test_file_group(self, prod_config):
        assert "file group" in prod_config
        assert prod_config["file group"] == "sallen"


class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, caplog):
        parsed_args = SimpleNamespace(run_date=arrow.get("2020-10-20"))
        caplog.set_level(logging.INFO)

        msg_type = download_live_ocean.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = (
            "2020-10-20 Live Ocean file for Salish Sea western boundary downloaded"
        )
        assert caplog.messages[0] == expected
        assert msg_type == "success"


class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, caplog):
        parsed_args = SimpleNamespace(run_date=arrow.get("2020-10-20"))
        caplog.set_level(logging.CRITICAL)

        msg_type = download_live_ocean.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = (
            "2020-10-20 Live Ocean file for Salish Sea western boundary download failed"
        )
        assert caplog.messages[0] == expected
        assert msg_type == "failure"


class TestDownloadLiveOcean:
    """Unit test for download_live_ocean() function."""

    @patch("nowcast.workers.download_live_ocean.logger", autospec=True)
    @patch("nowcast.workers.download_live_ocean.lib.mkdir", spec=True)
    @patch("nowcast.workers.download_live_ocean._get_file", spec=True)
    @patch("nowcast.workers.download_live_ocean.nemo_cmd.api.deflate", spec=True)
    def test_checklist(self, m_deflate, m_get_file, m_mkdir, m_logger, config):
        parsed_args = SimpleNamespace(run_date=arrow.get("2016-12-28"))
        m_get_file.return_value = Path(
            "/results/forcing/LiveOcean/downloaded/20161228/low_passed_UBC.nc"
        )
        checklist = download_live_ocean.download_live_ocean(parsed_args, config)
        expected = {
            "2016-12-28": "/results/forcing/LiveOcean/downloaded/20161228/low_passed_UBC.nc"
        }
        assert checklist == expected
