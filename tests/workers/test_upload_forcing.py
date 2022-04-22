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
"""Unit tests for SalishSeaCast upload_forcing worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import upload_forcing


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                temperature salinity:
                    bc dir: /results/forcing/LiveOcean/modified
                    file template: 'single_LO_{:y%Ym%md%d}.nc'

                run:
                    enabled hosts:
                        arbutus.cloud-nowcast:
                            ssh key: SalishSeaNEMO-nowcast_id_rsa
                            forcing:
                                bc dir: /nemoShare/MEOPAR/LiveOcean/
                        orcinus-nowcast-agrif:
                            ssh key: SalishSeaNEMO-nowcast_id_rsa
                        graham-dtn:
                            ssh key: SalishSeaNEMO-nowcast_id_rsa
                        optimum-hindcast:
                            ssh key: SalishSeaNEMO-nowcast_id_rsa
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(upload_forcing, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = upload_forcing.main()
        assert worker.name == "upload_forcing"
        assert worker.description.startswith(
            "SalishSeaCast worker that upload forcing files for NEMO runs."
        )

    def test_add_host_name_arg(self, mock_worker):
        worker = upload_forcing.main()
        assert worker.cli.parser._actions[3].dest == "host_name"
        assert worker.cli.parser._actions[3].help

    def test_add_run_type_arg(self, mock_worker):
        worker = upload_forcing.main()
        assert worker.cli.parser._actions[4].dest == "run_type"
        expected = {"nowcast+", "forecast2", "ssh", "turbidity"}
        assert worker.cli.parser._actions[4].choices == expected
        assert worker.cli.parser._actions[4].help

    def test_add_run_date_option(self, mock_worker):
        worker = upload_forcing.main()
        assert worker.cli.parser._actions[5].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[5].type == expected
        assert worker.cli.parser._actions[5].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[5].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "upload_forcing" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["upload_forcing"]
        assert msg_registry["checklist key"] == "forcing upload"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["upload_forcing"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success nowcast+",
            "failure nowcast+",
            "success forecast2",
            "failure forecast2",
            "success ssh",
            "failure ssh",
            "success turbidity",
            "failure turbidity",
            "crash",
        ]

    def test_enabled_hosts(self, prod_config):
        enabled_hosts = list(prod_config["run"]["enabled hosts"].keys())
        assert enabled_hosts == [
            "arbutus.cloud-nowcast",
            "salish-nowcast",
            "orcinus-nowcast-agrif",
            "graham-dtn",
            "optimum-hindcast",
        ]

    def test_ssh_keys(self, prod_config):
        for host in prod_config["run"]["enabled hosts"]:
            ssh_key = prod_config["run"]["enabled hosts"][host]["ssh key"]
            assert ssh_key == "SalishSeaNEMO-nowcast_id_rsa"

    @pytest.mark.parametrize(
        "host, ssh_key",
        (
            ("arbutus.cloud-nowcast", "/nemoShare/MEOPAR/sshNeahBay/"),
            ("salish-nowcast", "/results/forcing/sshNeahBay/"),
            (
                "optimum-hindcast",
                "/data/sallen/shared/SalishSeaCast/forcing/sshNeahBay/",
            ),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/sshNeahBay/"),
            ("graham-dtn", "/project/def-allen/SalishSea/forcing/sshNeahBay/"),
        ),
    )
    def test_ssh_uploads(self, host, ssh_key, prod_config):
        assert prod_config["ssh"]["ssh dir"] == "/results/forcing/sshNeahBay/"
        host_config = prod_config["run"]["enabled hosts"][host]
        assert host_config["forcing"]["ssh dir"] == ssh_key

    @pytest.mark.parametrize(
        "host, expected",
        (
            ("arbutus.cloud-nowcast", "/nemoShare/MEOPAR/rivers/river_turb/"),
            (
                "optimum-hindcast",
                "/data/sallen/shared/SalishSeaCast/forcing/rivers/river_turb/",
            ),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/rivers/river_turb/"),
            (
                "graham-dtn",
                "/project/def-allen/SalishSea/forcing/rivers/river_turb/",
            ),
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
            ("arbutus.cloud-nowcast", "/nemoShare/MEOPAR/rivers/"),
            ("salish-nowcast", "/results/forcing/rivers/"),
            ("optimum-hindcast", "/data/sallen/shared/SalishSeaCast/forcing/rivers/"),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/rivers/"),
            ("graham-dtn", "/project/def-allen/SalishSea/forcing/rivers/"),
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
            ("arbutus.cloud-nowcast", "/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/"),
            ("salish-nowcast", "/results/forcing/atmospheric/GEM2.5/operational/"),
            (
                "optimum-hindcast",
                "/data/sallen/shared/SalishSeaCast/forcing/atmospheric/GEM2.5/operational/",
            ),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/GEM2.5/ops/NEMO-atmos/"),
            (
                "graham-dtn",
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
            ("arbutus.cloud-nowcast", "/nemoShare/MEOPAR/LiveOcean/"),
            ("salish-nowcast", "/results/forcing/LiveOcean/boundary_conditions/"),
            (
                "optimum-hindcast",
                "/data/sallen/shared/SalishSeaCast/forcing/LiveOcean/",
            ),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/LiveOcean/"),
            ("graham-dtn", "/project/def-allen/SalishSea/forcing/LiveOcean/"),
        ),
    )
    def test_live_ocean_uploads(self, host, expected, prod_config):
        live_ocean = prod_config["temperature salinity"]
        assert live_ocean["file template"] == "LiveOcean_v201905_{:y%Ym%md%d}.nc"
        assert live_ocean["bc dir"] == "/results/forcing/LiveOcean/boundary_conditions"
        host_config = prod_config["run"]["enabled hosts"][host]
        assert host_config["forcing"]["bc dir"] == expected


@pytest.mark.parametrize(
    "run_type, host_name",
    (
        ("nowcast+", "arbutus.cloud-nowcast"),
        ("nowcast+", "orcinus-nowcast-agrif"),
        ("nowcast+", "optimum-hindcast"),
        ("nowcast+", "graham-dtn"),
        ("ssh", "arbutus.cloud-nowcast"),
        ("forecast2", "arbutus.cloud-nowcast"),
        ("forecast2", "orcinus-nowcast-agrif"),
        ("forecast2", "optimum-hindcast"),
        ("forecast2", "graham-dtn"),
        ("turbidity", "arbutus.cloud-nowcast"),
        ("turbidity", "orcinus-nowcast-agrif"),
        ("turbidity", "optimum-hindcast"),
        ("turbidity", "graham-dtn"),
    ),
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, run_type, host_name, caplog):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
            run_date=arrow.get("2020-06-29"),
        )
        caplog.set_level(logging.INFO)

        msg_type = upload_forcing.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = (
            f"{run_type} 2020-06-29 forcing files upload to {host_name} completed"
        )
        assert caplog.messages[0] == expected
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize(
    "run_type, host_name",
    (
        ("nowcast+", "arbutus.cloud-nowcast"),
        ("nowcast+", "orcinus-nowcast-agrif"),
        ("nowcast+", "optimum-hindcast"),
        ("nowcast+", "graham-dtn"),
        ("ssh", "arbutus.cloud-nowcast"),
        ("forecast2", "arbutus.cloud-nowcast"),
        ("forecast2", "orcinus-nowcast-agrif"),
        ("forecast2", "optimum-hindcast"),
        ("forecast2", "graham-dtn"),
        ("turbidity", "arbutus.cloud-nowcast"),
        ("turbidity", "orcinus-nowcast-agrif"),
        ("turbidity", "optimum-hindcast"),
        ("turbidity", "graham-dtn"),
    ),
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, run_type, host_name, caplog):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
            run_date=arrow.get("2020-06-29"),
        )
        caplog.set_level(logging.CRITICAL)

        msg_type = upload_forcing.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"{run_type} 2020-06-29 forcing files upload to {host_name} failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {run_type}"


@pytest.fixture
def mock_ssh_client(monkeypatch):
    class MockSSHClient:
        def close(self):
            pass

    return MockSSHClient()


@pytest.fixture
def mock_sftp_client(monkeypatch):
    class MockSFTPClient:
        def close(self):
            pass

    return MockSFTPClient()


@pytest.mark.parametrize(
    "run_type, host_name, file_types",
    (
        (
            "nowcast+",
            "arbutus.cloud-nowcast",
            ["ssh", "rivers", "weather", "boundary conditions"],
        ),
        (
            "nowcast+",
            "orcinus-nowcast-agrif",
            ["ssh", "rivers", "weather", "boundary conditions"],
        ),
        (
            "nowcast+",
            "optimum-hindcast",
            ["ssh", "rivers", "weather", "boundary conditions"],
        ),
        (
            "nowcast+",
            "graham-dtn",
            ["ssh", "rivers", "weather", "boundary conditions"],
        ),
        ("ssh", "arbutus.cloud-nowcast", ["ssh"]),
        (
            "forecast2",
            "arbutus.cloud-nowcast",
            ["ssh", "rivers", "weather", "boundary conditions"],
        ),
        (
            "forecast2",
            "orcinus-nowcast-agrif",
            ["ssh", "rivers", "weather", "boundary conditions"],
        ),
        (
            "forecast2",
            "optimum-hindcast",
            ["ssh", "rivers", "weather", "boundary conditions"],
        ),
        (
            "forecast2",
            "graham-dtn",
            ["ssh", "rivers", "weather", "boundary conditions"],
        ),
        ("turbidity", "arbutus.cloud-nowcast", ["turbidity"]),
        ("turbidity", "orcinus-nowcast-agrif", ["turbidity"]),
        ("turbidity", "optimum-hindcast", ["turbidity"]),
        ("turbidity", "graham-dtn", ["turbidity"]),
    ),
)
class TestChecklist:
    """Unit tests for checklist returned by upload_forcing() function."""

    @staticmethod
    @pytest.fixture
    def mock_sftp(mock_ssh_client, mock_sftp_client, monkeypatch):
        def sftp(host_name, ssh_key):
            return mock_ssh_client, mock_sftp_client

        monkeypatch.setattr(upload_forcing.ssh_sftp, "sftp", sftp)

    @staticmethod
    @pytest.fixture
    def mock_upload_ssh_files(monkeypatch):
        def _upload_ssh_files(
            sftp_client, run_type, run_date, config, host_name, host_config
        ):
            pass

        monkeypatch.setattr(upload_forcing, "_upload_ssh_files", _upload_ssh_files)

    @staticmethod
    @pytest.fixture
    def mock_upload_fraser_turbidity_file(monkeypatch):
        def _upload_fraser_turbidity_file(
            sftp_client, run_date, config, host_name, host_config
        ):
            pass

        monkeypatch.setattr(
            upload_forcing,
            "_upload_fraser_turbidity_file",
            _upload_fraser_turbidity_file,
        )

    @staticmethod
    @pytest.fixture
    def mock_upload_river_runoff_files(monkeypatch):
        def _upload_river_runoff_files(
            sftp_client, run_date, config, host_name, host_config
        ):
            pass

        monkeypatch.setattr(
            upload_forcing, "_upload_river_runoff_files", _upload_river_runoff_files
        )

    @staticmethod
    @pytest.fixture
    def mock_upload_weather(monkeypatch):
        def _upload_weather(
            sftp_client, run_type, run_date, config, host_name, host_config
        ):
            pass

        monkeypatch.setattr(upload_forcing, "_upload_weather", _upload_weather)

    @staticmethod
    @pytest.fixture
    def mock_upload_live_ocean_files(monkeypatch):
        def _upload_live_ocean_files(
            sftp_client, run_type, run_date, config, host_name, host_config
        ):
            pass

        monkeypatch.setattr(
            upload_forcing, "_upload_live_ocean_files", _upload_live_ocean_files
        )

    def test_checklist(
        self,
        run_type,
        host_name,
        file_types,
        mock_sftp,
        mock_upload_ssh_files,
        mock_upload_fraser_turbidity_file,
        mock_upload_river_runoff_files,
        mock_upload_weather,
        mock_upload_live_ocean_files,
        config,
        monkeypatch,
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
            run_date=arrow.get("2020-06-29"),
        )
        checklist = upload_forcing.upload_forcing(parsed_args, config)
        expected = {
            host_name: {
                run_type: {
                    "run date": parsed_args.run_date.format("YYYY-MM-DD"),
                    "file types": file_types,
                }
            }
        }
        assert checklist == expected


@patch(
    "nowcast.workers.upload_forcing.ssh_sftp.upload_file",
    side_effect=[FileNotFoundError, None, FileNotFoundError, None],
    autospec=True,
)
class TestUploadLiveOceanFiles:
    """Unit tests for _upload_live_ocean_files() function."""

    @pytest.mark.parametrize(
        "run_type, logging_level",
        [("nowcast+", logging.CRITICAL), ("forecast2", logging.INFO)],
    )
    def test_live_ocean_persistence_symlink_logging_level(
        self, m_upload_file, run_type, logging_level, mock_sftp_client, config, caplog
    ):
        run_date = arrow.get("2017-09-03")
        host_config = config["run"]["enabled hosts"]["arbutus.cloud-nowcast"]
        caplog.set_level(logging_level)

        with patch("nowcast.workers.upload_forcing.Path.symlink_to"):
            upload_forcing._upload_live_ocean_files(
                mock_sftp_client,
                run_type,
                run_date,
                config,
                "arbutus.cloud",
                host_config,
            )

        if logging_level is None:
            assert not caplog.messages
        else:
            assert caplog.records[0].levelno == logging_level
