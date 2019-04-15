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
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import upload_forcing


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
temperature salinity:
    bc dir: /results/forcing/LiveOcean/modified
    file template: 'single_LO_{:y%Ym%md%d}.nc'
    
run:
    enabled hosts:
        west.cloud:
            forcing:
                bc dir: /nemoShare/MEOPAR/LiveOcean/
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


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


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "upload_forcing" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["upload_forcing"]
        assert msg_registry["checklist key"] == "forcing upload"

    @pytest.mark.parametrize(
        "msg",
        (
            "success nowcast+",
            "failure nowcast+",
            "success forecast2",
            "failure forecast2",
            "success ssh",
            "failure ssh",
            "success turbidity",
            "failure turbidity",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["upload_forcing"]
        assert msg in msg_registry

    def test_enabled_hosts(self, prod_config):
        enabled_hosts = list(prod_config["run"]["enabled hosts"].keys())
        assert enabled_hosts == [
            "west.cloud-nowcast",
            "salish-nowcast",
            "orcinus-nowcast-agrif",
            "beluga-hindcast",
            "cedar-hindcast",
            "graham-hindcast",
            "optimum-hindcast",
        ]

    def test_ssh_keys(self, prod_config):
        for host in prod_config["run"]["enabled hosts"]:
            ssh_key = prod_config["run"]["enabled hosts"][host]["ssh key"]
            assert ssh_key == "SalishSeaNEMO-nowcast_id_rsa"

    @pytest.mark.parametrize(
        "host, expected",
        (
            ("west.cloud-nowcast", "/nemoShare/MEOPAR/sshNeahBay/"),
            ("salish-nowcast", "/results/forcing/sshNeahBay/"),
            (
                "optimum-hindcast",
                "/data/sallen/shared/SalishSeaCast/forcing/sshNeahBay/",
            ),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/sshNeahBay/"),
            ("beluga-hindcast", "/project/def-allen/SalishSea/forcing/sshNeahBay/"),
            ("cedar-hindcast", "/project/6001313/SalishSea/forcing/sshNeahBay/"),
            ("graham-hindcast", "/project/def-allen/SalishSea/forcing/sshNeahBay/"),
        ),
    )
    def test_ssh_uploads(self, host, expected, prod_config):
        assert prod_config["ssh"]["ssh dir"] == "/results/forcing/sshNeahBay/"
        host_config = prod_config["run"]["enabled hosts"][host]
        assert host_config["forcing"]["ssh dir"] == expected

    @pytest.mark.parametrize(
        "host, expected",
        (
            ("west.cloud-nowcast", "/nemoShare/MEOPAR/rivers/river_turb/"),
            (
                "optimum-hindcast",
                "/data/sallen/shared/SalishSeaCast/forcing/rivers/river_turb/",
            ),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/rivers/river_turb/"),
            (
                "beluga-hindcast",
                "/project/def-allen/SalishSea/forcing/rivers/river_turb/",
            ),
            ("cedar-hindcast", "/project/6001313/SalishSea/forcing/rivers/river_turb/"),
        ),
    )
    def test_fraser_turbidity_uploads(self, host, expected, prod_config):
        turbidity = prod_config["rivers"]["turbidity"]
        assert turbidity["file template"] == "riverTurbDaily2_{:y%Ym%md%d}.nc"
        assert turbidity["forcing dir"] == "/results/forcing/rivers/river_turb/"
        host_config = prod_config["run"]["enabled hosts"][host]
        assert host_config["forcing"]["Fraser turbidity dir"] == expected

    @pytest.mark.parametrize(
        "host, expected",
        (
            ("west.cloud-nowcast", "/nemoShare/MEOPAR/rivers/"),
            ("salish-nowcast", "/results/forcing/rivers/"),
            ("optimum-hindcast", "/data/sallen/shared/SalishSeaCast/forcing/rivers/"),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/rivers/"),
            ("beluga-hindcast", "/project/def-allen/SalishSea/forcing/rivers/"),
            ("cedar-hindcast", "/project/6001313/SalishSea/forcing/rivers/"),
            ("graham-hindcast", "/project/def-allen/SalishSea/forcing/rivers/"),
        ),
    )
    def test_river_runoff_uploads(self, host, expected, prod_config):
        rivers = prod_config["rivers"]
        assert rivers["file templates"] == {
            "b201702": "R201702DFraCElse_{:y%Ym%md%d}.nc"
        }
        assert rivers["rivers dir"] == "/results/forcing/rivers/"
        host_config = prod_config["run"]["enabled hosts"][host]
        assert host_config["forcing"]["rivers dir"] == expected

    @pytest.mark.parametrize(
        "host, expected",
        (
            ("west.cloud-nowcast", "/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/"),
            ("salish-nowcast", "/results/forcing/atmospheric/GEM2.5/operational/"),
            (
                "optimum-hindcast",
                "/data/sallen/shared/SalishSeaCast/forcing/atmospheric/GEM2.5/operational/",
            ),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/GEM2.5/ops/NEMO-atmos/"),
            (
                "beluga-hindcast",
                "/project/def-allen/SalishSea/forcing/atmospheric/GEM2.5/operational/",
            ),
            (
                "cedar-hindcast",
                "/project/6001313/SalishSea/forcing/atmospheric/GEM2.5/operational/",
            ),
            (
                "graham-hindcast",
                "/project/def-allen/SalishSea/forcing/atmospheric/GEM2.5/operational/",
            ),
        ),
    )
    def test_weather_uploads(self, host, expected, prod_config):
        weather = prod_config["weather"]
        assert weather["file template"] == "ops_{:y%Ym%md%d}.nc"
        assert weather["ops dir"] == "/results/forcing/atmospheric/GEM2.5/operational/"
        host_config = prod_config["run"]["enabled hosts"][host]
        assert host_config["forcing"]["weather dir"] == expected

    @pytest.mark.parametrize(
        "host, expected",
        (
            ("west.cloud-nowcast", "/nemoShare/MEOPAR/LiveOcean/"),
            ("salish-nowcast", "/results/forcing/LiveOcean/boundary_conditions/"),
            (
                "optimum-hindcast",
                "/data/sallen/shared/SalishSeaCast/forcing/LiveOcean/",
            ),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/LiveOcean/"),
            ("beluga-hindcast", "/project/def-allen/SalishSea/forcing/LiveOcean/"),
            ("cedar-hindcast", "/project/6001313/SalishSea/forcing/LiveOcean/"),
            ("graham-hindcast", "/project/def-allen/SalishSea/forcing/LiveOcean/"),
        ),
    )
    def test_live_ocean_uploads(self, host, expected, prod_config):
        live_ocean = prod_config["temperature salinity"]
        assert live_ocean["file template"] == "LiveOcean_v201712_{:y%Ym%md%d}.nc"
        assert live_ocean["bc dir"] == "/results/forcing/LiveOcean/boundary_conditions"
        host_config = prod_config["run"]["enabled hosts"][host]
        assert host_config["forcing"]["bc dir"] == expected


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
