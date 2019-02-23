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
"""Unit tests for Salish Sea NEMO nowcast upload_forcing worker.
"""
import logging
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import pytest

from nowcast.workers import upload_forcing


@pytest.fixture
def config():
    """Nowcast system config dict data structure;
    a mock for :py:attr:`nemo_nowcast.config.Config._dict`.
    """
    return {
        "temperature salinity": {
            "bc dir": "/results/forcing/LiveOcean/modified",
            "file template": "single_LO_{:y%Ym%md%d}.nc",
        },
        "run": {
            "enabled hosts": {
                "west.cloud": {"forcing": {"bc dir": "/nemoShare/MEOPAR/LiveOcean/"}}
            }
        },
    }


@patch("nowcast.workers.upload_forcing.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_forcing.main()
        args, kwargs = m_worker.call_args
        assert args == ("upload_forcing",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_forcing.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast+", "forecast2", "ssh", "turbidity"}
        assert "help" in kwargs

    def test_add_run_date_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_forcing.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_forcing.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            upload_forcing.upload_forcing,
            upload_forcing.success,
            upload_forcing.failure,
        )


@pytest.mark.parametrize("run_type", ["nowcast+", "forecast2", "ssh", "turbidity"])
@patch("nowcast.workers.upload_forcing.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2017-01-02")
        )
        msg_type = upload_forcing.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["nowcast+", "forecast2", "ssh", "turbidity"])
@patch("nowcast.workers.upload_forcing.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2017-01-02")
        )
        msg_type = upload_forcing.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {run_type}"


@patch(
    "nowcast.workers.upload_forcing.ssh_sftp.upload_file",
    side_effect=[FileNotFoundError, None, FileNotFoundError, None],
    autospec=True,
)
@patch("nowcast.workers.upload_forcing.logger", autospec=True)
class TestUploadLiveOceanFiles:
    """Unit tests for _upload_live_ocean_files() function.
    """

    @pytest.mark.parametrize(
        "run_type, logging_level",
        [("nowcast+", logging.CRITICAL), ("forecast2", logging.INFO)],
    )
    def test_live_ocean_persistence_symlink_logging_level(
        self, m_logger, m_upload_file, run_type, logging_level, config
    ):
        sftp_client = Mock(namd="sftp_client")
        run_date = arrow.get("2017-09-03")
        host_config = config["run"]["enabled hosts"]["west.cloud"]
        with patch("nowcast.workers.upload_forcing.Path.symlink_to"):
            upload_forcing._upload_live_ocean_files(
                sftp_client, run_type, run_date, config, "west.cloud", host_config
            )
        if logging_level is None:
            assert not m_logger.log.called
        else:
            assert m_logger.log.call_args[0][0] == logging_level
