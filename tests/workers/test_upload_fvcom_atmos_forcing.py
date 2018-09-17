# Copyright 2013-2018 The Salish Sea MEOPAR contributors
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
"""Unit tests for Vancouver Harbour & Fraser River FVCOM
upload_fvcom_atmos_forcing worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import upload_fvcom_atmos_forcing


@patch(
    "nowcast.workers.upload_fvcom_atmos_forcing.NowcastWorker",
    spec=nemo_nowcast.NowcastWorker,
)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        upload_fvcom_atmos_forcing.main()
        args, kwargs = m_worker.call_args
        assert args == ("upload_fvcom_atmos_forcing",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        upload_fvcom_atmos_forcing.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        upload_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        upload_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        upload_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        upload_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            upload_fvcom_atmos_forcing.upload_fvcom_atmos_forcing,
            upload_fvcom_atmos_forcing.success,
            upload_fvcom_atmos_forcing.failure,
        )


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.upload_fvcom_atmos_forcing.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2018-04-04")
        )
        upload_fvcom_atmos_forcing.success(parsed_args)
        assert m_logger.info.called

    def test_success_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2018-04-04")
        )
        msg_type = upload_fvcom_atmos_forcing.success(parsed_args)
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.upload_fvcom_atmos_forcing.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_critical(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2018-04-04")
        )
        upload_fvcom_atmos_forcing.failure(parsed_args)
        assert m_logger.critical.called

    def test_failure_msg_type(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2018-04-04")
        )
        msg_type = upload_fvcom_atmos_forcing.failure(parsed_args)
        assert msg_type == f"failure {run_type}"


@pytest.mark.parametrize(
    "run_type, file_date", [("nowcast", "20180404"), ("forecast", "20180405")]
)
@patch("nowcast.workers.upload_fvcom_atmos_forcing.ssh_sftp.sftp", autospec=True)
@patch("nowcast.workers.upload_fvcom_atmos_forcing.ssh_sftp.upload_file", autospec=True)
@patch("nowcast.workers.upload_fvcom_atmos_forcing.logger", autospec=True)
class TestUploadFVCOMAtmosForcing:
    """Unit tests for upload_fvcom_atmos_forcing() function.
    """

    config = {
        "vhfr fvcom runs": {
            "host": "west.cloud",
            "ssh key": "SalishSeaNEMO-nowcast_id_rsa",
            "atmospheric forcing": {
                "fvcom atmos dir": "forcing/atmospheric/GEM2.5/vhfr-fvcom",
                "atmos file template": "atmos_{run_type}_{field_type}_{yyyymmdd}.nc",
            },
            "input dir": "fvcom-runs/input",
        }
    }

    def test_checklist(self, m_logger, m_upload_file, m_sftp, run_type, file_date):
        m_sftp.return_value = (Mock(name="ssh_client"), Mock(name="sftp_client"))
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2018-04-04")
        )
        checklist = upload_fvcom_atmos_forcing.upload_fvcom_atmos_forcing(
            parsed_args, self.config
        )
        expected = {
            "west.cloud": {
                run_type: {
                    "run date": "2018-04-04",
                    "file": f"atmos_{run_type}_wnd_{file_date}.nc",
                }
            }
        }
        assert checklist == expected

    def test_upload_file(self, m_logger, m_upload_file, m_sftp, run_type, file_date):
        m_sftp_client = Mock(name="sftp_client")
        m_sftp.return_value = (Mock(name="ssh_client"), m_sftp_client)
        parsed_args = SimpleNamespace(
            host_name="west.cloud", run_type=run_type, run_date=arrow.get("2018-04-04")
        )
        upload_fvcom_atmos_forcing.upload_fvcom_atmos_forcing(parsed_args, self.config)
        m_upload_file.assert_called_once_with(
            m_sftp_client,
            "west.cloud",
            Path(
                f"forcing/atmospheric/GEM2.5/vhfr-fvcom/"
                f"atmos_{run_type}_wnd_{file_date}.nc"
            ),
            Path(f"fvcom-runs/input/atmos_{run_type}_wnd_{file_date}.nc"),
            m_logger,
        )
