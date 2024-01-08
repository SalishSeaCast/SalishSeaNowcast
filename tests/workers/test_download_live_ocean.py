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


"""Unit tests for SalishSeaCast download_live_ocean worker.
"""
import grp
import logging
import os
import textwrap
from pathlib import Path
from types import SimpleNamespace

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
                    status file url template: 'https://liveocean.apl.uw.edu/output/f{yyyymmdd}/ubc_done.txt'
                    bc file url template: 'https://liveocean.apl.uw.edu/output/f{yyyymmdd}/ubc.nc'
                    file name: low_passed_UBC.nc
                    dest dir: forcing/LiveOcean/downloaded
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
    """Unit tests for production YAML config file elements related to worker."""

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

    def test_file_group(self, prod_config):
        assert "file group" in prod_config
        assert prod_config["file group"] == "sallen"

    def test_download_section(self, prod_config):
        download = prod_config["temperature salinity"]["download"]
        assert (
            download["status file url template"]
            == "https://liveocean.apl.uw.edu/output/f{yyyymmdd}/ubc_done.txt"
        )
        assert (
            download["bc file url template"]
            == "https://liveocean.apl.uw.edu/output/f{yyyymmdd}/ubc.nc"
        )
        assert download["dest dir"] == "/results/forcing/LiveOcean/downloaded/"
        assert download["file name"] == "low_passed_UBC.nc"


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

    def test_checklist(self, config, caplog, tmp_path, monkeypatch):
        def mock_is_file_ready(process_status_path, session):
            return True

        monkeypatch.setattr(download_live_ocean, "_is_file_ready", mock_is_file_ready)

        def mock_get_web_data(file_url, logger_name, filepath, session):
            (dest_dir / "20201022" / "low_passed_UBC.nc").write_text("mock contents")

        monkeypatch.setattr(download_live_ocean, "get_web_data", mock_get_web_data)

        def mock_deflate(filepaths, max_concurrent_jobs):
            pass

        monkeypatch.setattr(download_live_ocean.nemo_cmd.api, "deflate", mock_deflate)

        dest_dir = tmp_path / config["temperature salinity"]["download"]["dest dir"]
        dest_dir.mkdir(parents=True)
        monkeypatch.setitem(
            config["temperature salinity"]["download"], "dest dir", dest_dir
        )
        grp_name = grp.getgrgid(os.getgid()).gr_name
        monkeypatch.setitem(config, "file group", grp_name)

        parsed_args = SimpleNamespace(run_date=arrow.get("2020-10-22"))
        caplog.set_level(logging.DEBUG)

        checklist = download_live_ocean.download_live_ocean(parsed_args, config)

        expected = {
            "2020-10-22": os.fspath(dest_dir / "20201022" / "low_passed_UBC.nc")
        }
        assert checklist == expected
