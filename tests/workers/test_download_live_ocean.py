# Copyright 2013-2018 The Salish Sea MEOPAR Contributors
# and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for Salish Sea NEMO nowcast download_live_ocean worker.
"""
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import arrow

from nowcast.workers import download_live_ocean


@patch("nowcast.workers.download_live_ocean.NowcastWorker")
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        download_live_ocean.main()
        args, kwargs = m_worker.call_args
        assert args == ("download_live_ocean",)
        assert "description" in kwargs

    def test_init_cli(self, m_worker):
        download_live_ocean.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_date_arg(self, m_worker):
        download_live_ocean.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        download_live_ocean.main()
        args, kwargs = m_worker().run.call_args
        expected = (
            download_live_ocean.download_live_ocean,
            download_live_ocean.success,
            download_live_ocean.failure,
        )
        assert args == expected


@patch("nowcast.workers.download_live_ocean.logger")
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2016-11-24"))
        download_live_ocean.success(parsed_args)
        assert m_logger.info.called
        assert m_logger.info.call_args[1]["extra"]["run_date"] == "2016-11-24"

    def test_success_msg_type(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2016-11-24"))
        msg_type = download_live_ocean.success(parsed_args)
        assert msg_type == "success"


@patch("nowcast.workers.download_live_ocean.logger")
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_critical(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2016-11-24"))
        download_live_ocean.failure(parsed_args)
        assert m_logger.critical.called
        expected = "2016-11-24"
        assert m_logger.critical.call_args[1]["extra"]["run_date"] == expected

    def test_failure_msg_type(self, m_logger):
        parsed_args = SimpleNamespace(run_date=arrow.get("2016-11-24"))
        msg_type = download_live_ocean.failure(parsed_args)
        assert msg_type == "failure"


class TestDownloadLiveOcean:
    """Unit test for download_live_ocean() function.
    """

    @patch("nowcast.workers.download_live_ocean.lib.mkdir")
    @patch("nowcast.workers.download_live_ocean._get_file")
    @patch("nowcast.workers.download_live_ocean.nemo_cmd.api.deflate")
    def test_checklist(self, m_deflate, m_get_file, m_mkdir):
        parsed_args = SimpleNamespace(run_date=arrow.get("2016-12-28"))
        config = {
            "file group": "foo",
            "temperature salinity": {
                "download": {
                    "url": "https://pm2.blob.core.windows.net/",
                    "directory prefix": "f",
                    "file name": "low_passed_UBC.nc",
                    "dest dir": "/results/forcing/LiveOcean/downloaded",
                }
            },
        }
        m_get_file.return_value = Path(
            "/results/forcing/LiveOcean/downloaded/20161228/low_passed_UBC.nc"
        )
        checklist = download_live_ocean.download_live_ocean(parsed_args, config)
        expected = {
            "2016-12-28": "/results/forcing/LiveOcean/downloaded/20161228/low_passed_UBC.nc"
        }
        assert checklist == expected
