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
"""Unit tests for Vancouver Harbour & Fraser River FVCOM
upload_fvcom_atmos_forcing worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import upload_fvcom_atmos_forcing


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
vhfr fvcom runs:
  host: west.cloud
  ssh key: SalishSeaNEMO-nowcast_id_rsa
  
  atmospheric forcing:
    fvcom atmos dir: forcing/atmospheric/GEM2.5/vhfr-fvcom
    atmos file template: 'atmos_{model_config}_{run_type}_{field_type}_{yyyymmdd}.nc'
    field types:
      - hfx
      - precip
      - wnd

  input dir:
   x2: fvcom-runs/input.x2/
   r12: fvcom-runs/input.r12/
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.upload_fvcom_atmos_forcing.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_fvcom_atmos_forcing.main()
        args, kwargs = m_worker.call_args
        assert args == ("upload_fvcom_atmos_forcing",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_fvcom_atmos_forcing.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_model_config_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("model_config",)
        assert kwargs["choices"] == {"r12", "x2"}
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        upload_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            upload_fvcom_atmos_forcing.upload_fvcom_atmos_forcing,
            upload_fvcom_atmos_forcing.success,
            upload_fvcom_atmos_forcing.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert (
            "upload_fvcom_atmos_forcing" in prod_config["message registry"]["workers"]
        )
        msg_registry = prod_config["message registry"]["workers"][
            "upload_fvcom_atmos_forcing"
        ]
        assert msg_registry["checklist key"] == "FVCOM atmospheric forcing upload"

    @pytest.mark.parametrize(
        "msg",
        (
            "success x2 nowcast",
            "failure x2 nowcast",
            "success x2 forecast",
            "failure x2 forecast",
            "success r12 nowcast",
            "failure r12 nowcast",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "upload_fvcom_atmos_forcing"
        ]
        assert msg in msg_registry

    def test_atmospheric_forcing_section(self, prod_config):
        assert "vhfr fvcom runs" in prod_config
        assert "atmospheric forcing" in prod_config["vhfr fvcom runs"]
        atmos_forcing = prod_config["vhfr fvcom runs"]["atmospheric forcing"]
        assert (
            atmos_forcing["fvcom atmos dir"]
            == "/results/forcing/atmospheric/GEM2.5/vhfr-fvcom"
        )
        assert (
            atmos_forcing["atmos file template"]
            == "atmos_{model_config}_{run_type}_{field_type}_{yyyymmdd}.nc"
        )
        assert atmos_forcing["field types"] == ["hfx", "precip", "wnd"]

    def test_input_dir(self, prod_config):
        input_dir = prod_config["vhfr fvcom runs"]["input dir"]
        assert input_dir["x2"] == "/nemoShare/MEOPAR/nowcast-sys/fvcom-runs/input.x2/"
        assert input_dir["r12"] == "/nemoShare/MEOPAR/nowcast-sys/fvcom-runs/input.r12/"

    def test_ssh_key(self, prod_config):
        assert (
            prod_config["vhfr fvcom runs"]["ssh key"] == "SalishSeaNEMO-nowcast_id_rsa"
        )


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.upload_fvcom_atmos_forcing.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success_log_info(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-04-04"),
        )
        msg_type = upload_fvcom_atmos_forcing.success(parsed_args)
        assert msg_type == f"success {model_config} {run_type}"
        assert m_logger.info.called


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.upload_fvcom_atmos_forcing.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure_log_critical(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            host_name="west.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-04-04"),
        )
        msg_type = upload_fvcom_atmos_forcing.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {model_config} {run_type}"


@pytest.mark.parametrize(
    "model_config, run_type, run_date, atmos_file_date",
    (
        ("x2", "nowcast", arrow.get("2018-12-07"), "20181207"),
        ("x2", "forecast", arrow.get("2018-12-07"), "20181208"),
        ("r12", "nowcast", arrow.get("2019-02-21"), "20190221"),
    ),
)
@patch("nowcast.workers.upload_fvcom_atmos_forcing.ssh_sftp.sftp", autospec=True)
@patch("nowcast.workers.upload_fvcom_atmos_forcing.ssh_sftp.upload_file", autospec=True)
@patch("nowcast.workers.upload_fvcom_atmos_forcing.logger", autospec=True)
class TestUploadFVCOMAtmosForcing:
    """Unit tests for upload_fvcom_atmos_forcing() function.
    """

    def test_checklist(
        self,
        m_logger,
        m_upload_file,
        m_sftp,
        model_config,
        run_type,
        run_date,
        atmos_file_date,
        config,
    ):
        m_sftp.return_value = (Mock(name="ssh_client"), Mock(name="sftp_client"))
        parsed_args = SimpleNamespace(
            host_name="west.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=run_date,
        )
        checklist = upload_fvcom_atmos_forcing.upload_fvcom_atmos_forcing(
            parsed_args, config
        )
        expected = {
            "west.cloud": {
                run_type: {
                    "run date": run_date.format("YYYY-MM-DD"),
                    "model config": model_config,
                    "files": [
                        f"atmos_{model_config}_{run_type}_hfx_{atmos_file_date}.nc",
                        f"atmos_{model_config}_{run_type}_precip_{atmos_file_date}.nc",
                        f"atmos_{model_config}_{run_type}_wnd_{atmos_file_date}.nc",
                    ],
                }
            }
        }
        assert checklist == expected

    def test_upload_file(
        self,
        m_logger,
        m_upload_file,
        m_sftp,
        model_config,
        run_type,
        run_date,
        atmos_file_date,
        config,
    ):
        m_sftp_client = Mock(name="sftp_client")
        m_sftp.return_value = (Mock(name="ssh_client"), m_sftp_client)
        parsed_args = SimpleNamespace(
            host_name="west.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=run_date,
        )
        upload_fvcom_atmos_forcing.upload_fvcom_atmos_forcing(parsed_args, config)
        assert m_upload_file.call_args_list == [
            call(
                m_sftp_client,
                "west.cloud",
                Path(
                    f"forcing/atmospheric/GEM2.5/vhfr-fvcom/"
                    f"atmos_{model_config}_{run_type}_hfx_{atmos_file_date}.nc"
                ),
                Path(
                    f"fvcom-runs/input.{model_config}/atmos_{model_config}_{run_type}_hfx_{atmos_file_date}.nc"
                ),
                m_logger,
            ),
            call(
                m_sftp_client,
                "west.cloud",
                Path(
                    f"forcing/atmospheric/GEM2.5/vhfr-fvcom/"
                    f"atmos_{model_config}_{run_type}_precip_{atmos_file_date}.nc"
                ),
                Path(
                    f"fvcom-runs/input.{model_config}/atmos_{model_config}_{run_type}_precip_{atmos_file_date}.nc"
                ),
                m_logger,
            ),
            call(
                m_sftp_client,
                "west.cloud",
                Path(
                    f"forcing/atmospheric/GEM2.5/vhfr-fvcom/"
                    f"atmos_{model_config}_{run_type}_wnd_{atmos_file_date}.nc"
                ),
                Path(
                    f"fvcom-runs/input.{model_config}/atmos_{model_config}_{run_type}_wnd_{atmos_file_date}.nc"
                ),
                m_logger,
            ),
        ]
