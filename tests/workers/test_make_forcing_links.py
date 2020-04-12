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
"""Unit tests for SalishSeaCast make_forcing_links worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_forcing_links


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                rivers:
                  file templates:
                    short: "RFraserCElse_{:y%Ym%md%d}.nc"
                    long: "RLonFraCElse_{:y%Ym%md%d}.nc"
                  turbidity:
                    file template: "riverTurbDaily2_{:y%Ym%md%d}.nc"
                      
                run:
                  enabled hosts:
                    salish-nowcast:
                      run prep dir: runs/
                      forcing:
                        rivers dir: /results/forcing/rivers/
                        Fraser turbidity dir: /results/forcing/rivers/river_turb/
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(make_forcing_links, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, mock_worker):
        worker = make_forcing_links.main()
        assert worker.name == "make_forcing_links"
        assert worker.description.startswith(
            "SalishSeaCast worker that creates forcing files symlinks for NEMO runs."
        )

    def test_add_host_name_arg(self, mock_worker):
        worker = make_forcing_links.main()
        assert worker.cli.parser._actions[3].dest == "host_name"
        assert worker.cli.parser._actions[3].help

    def test_add_run_type_arg(self, mock_worker):
        worker = make_forcing_links.main()
        assert worker.cli.parser._actions[4].dest == "run_type"
        expected = {
            "nowcast+",
            "forecast2",
            "ssh",
            "nowcast-green",
            "nowcast-agrif",
        }
        assert worker.cli.parser._actions[4].choices == expected
        assert worker.cli.parser._actions[4].help

    def test_add_shared_storage_arg(self, mock_worker):
        worker = make_forcing_links.main()
        assert worker.cli.parser._actions[5].dest == "shared_storage"
        assert worker.cli.parser._actions[5].default is False
        assert worker.cli.parser._actions[5].help

    def test_add_run_date_option(self, mock_worker):
        worker = make_forcing_links.main()
        assert worker.cli.parser._actions[6].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[6].type == expected
        assert worker.cli.parser._actions[6].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[6].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "make_forcing_links" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["make_forcing_links"]
        assert msg_registry["checklist key"] == "forcing links"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["make_forcing_links"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success nowcast+",
            "failure nowcast+",
            "success forecast2",
            "failure forecast2",
            "success ssh",
            "failure ssh",
            "success nowcast-green",
            "failure nowcast-green",
            "success nowcast-agrif",
            "failure nowcast-agrif",
            "crash",
        ]

    def test_enabled_hosts(self, prod_config):
        assert list(prod_config["run"]["enabled hosts"].keys()) == [
            "arbutus.cloud-nowcast",
            "salish-nowcast",
            "orcinus-nowcast-agrif",
            "graham-hindcast",
            "optimum-hindcast",
        ]

    @pytest.mark.parametrize(
        "host, ssh_key",
        (
            ("arbutus.cloud-nowcast", "SalishSeaNEMO-nowcast_id_rsa"),
            ("salish-nowcast", "SalishSeaNEMO-nowcast_id_rsa"),
            ("orcinus-nowcast-agrif", "SalishSeaNEMO-nowcast_id_rsa"),
            ("graham-hindcast", "SalishSeaNEMO-nowcast_id_rsa"),
            ("optimum-hindcast", "SalishSeaNEMO-nowcast_id_rsa"),
        ),
    )
    def test_ssh_keys(self, host, ssh_key, prod_config):
        assert prod_config["run"]["enabled hosts"][host]["ssh key"] == ssh_key

    @pytest.mark.parametrize(
        "host, run_prep_dir",
        (
            ("arbutus.cloud-nowcast", "/nemoShare/MEOPAR/nowcast-sys/runs"),
            ("salish-nowcast", "/SalishSeaCast/runs/"),
            ("orcinus-nowcast-agrif", "/home/dlatorne/nowcast-agrif-sys/runs"),
        ),
    )
    def test_run_prep_dir(self, host, run_prep_dir, prod_config):
        assert prod_config["run"]["enabled hosts"][host]["run prep dir"] == run_prep_dir

    def test_ssh_file_template(self, prod_config):
        assert prod_config["ssh"]["file template"] == "ssh_{:y%Ym%md%d}.nc"

    @pytest.mark.parametrize(
        "host, ssh_dir",
        (
            ("arbutus.cloud-nowcast", "/nemoShare/MEOPAR/sshNeahBay/"),
            ("salish-nowcast", "/results/forcing/sshNeahBay/"),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/sshNeahBay/"),
            ("graham-hindcast", "/project/def-allen/SalishSea/forcing/sshNeahBay/"),
            (
                "optimum-hindcast",
                "/data/sallen/shared/SalishSeaCast/forcing/sshNeahBay/",
            ),
        ),
    )
    def test_ssh_dir(self, host, ssh_dir, prod_config):
        assert (
            prod_config["run"]["enabled hosts"][host]["forcing"]["ssh dir"] == ssh_dir
        )

    def test_rivers_file_templates(self, prod_config):
        expected = {"b201702": "R201702DFraCElse_{:y%Ym%md%d}.nc"}
        assert prod_config["rivers"]["file templates"] == expected

    @pytest.mark.parametrize(
        "host, rivers_dir",
        (
            ("arbutus.cloud-nowcast", "/nemoShare/MEOPAR/rivers/"),
            ("salish-nowcast", "/results/forcing/rivers/"),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/rivers/"),
            ("graham-hindcast", "/project/def-allen/SalishSea/forcing/rivers/"),
            ("optimum-hindcast", "/data/sallen/shared/SalishSeaCast/forcing/rivers/"),
        ),
    )
    def test_rivers_dir(self, host, rivers_dir, prod_config):
        assert (
            prod_config["run"]["enabled hosts"][host]["forcing"]["rivers dir"]
            == rivers_dir
        )

    @pytest.mark.parametrize(
        "host, fraser_turbidity_dir",
        (
            ("arbutus.cloud-nowcast", "/nemoShare/MEOPAR/rivers/river_turb/"),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/rivers/river_turb/"),
            (
                "graham-hindcast",
                "/project/def-allen/SalishSea/forcing/rivers/river_turb/",
            ),
            (
                "optimum-hindcast",
                "/data/sallen/shared/SalishSeaCast/forcing/rivers/river_turb/",
            ),
        ),
    )
    def test_fraser_turbidity_dir(self, host, fraser_turbidity_dir, prod_config):
        config_fraser_turbidity_dir = prod_config["run"]["enabled hosts"][host][
            "forcing"
        ]["Fraser turbidity dir"]
        assert config_fraser_turbidity_dir == fraser_turbidity_dir

    def test_fraser_turbidity_file_template(self, prod_config):
        assert (
            prod_config["rivers"]["turbidity"]["file template"]
            == "riverTurbDaily2_{:y%Ym%md%d}.nc"
        )

    def test_weather_file_template(self, prod_config):
        assert prod_config["weather"]["file template"] == "ops_{:y%Ym%md%d}.nc"

    @pytest.mark.parametrize(
        "host, weather_dir",
        (
            ("arbutus.cloud-nowcast", "/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/"),
            ("salish-nowcast", "/results/forcing/atmospheric/GEM2.5/operational/"),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/GEM2.5/ops/NEMO-atmos/"),
            (
                "graham-hindcast",
                "/project/def-allen/SalishSea/forcing/atmospheric/GEM2.5/operational/",
            ),
            (
                "optimum-hindcast",
                "/data/sallen/shared/SalishSeaCast/forcing/atmospheric/GEM2.5/operational/",
            ),
        ),
    )
    def test_weather_dir(self, host, weather_dir, prod_config):
        assert (
            prod_config["run"]["enabled hosts"][host]["forcing"]["weather dir"]
            == weather_dir
        )

    def test_temperature_salinity_file_template(self, prod_config):
        assert (
            prod_config["temperature salinity"]["file template"]
            == "LiveOcean_v201905_{:y%Ym%md%d}.nc"
        )

    @pytest.mark.parametrize(
        "host, bc_dir",
        (
            ("arbutus.cloud-nowcast", "/nemoShare/MEOPAR/LiveOcean/"),
            ("salish-nowcast", "/results/forcing/LiveOcean/boundary_conditions/"),
            ("orcinus-nowcast-agrif", "/home/sallen/MEOPAR/LiveOcean/"),
            ("graham-hindcast", "/project/def-allen/SalishSea/forcing/LiveOcean/"),
            (
                "optimum-hindcast",
                "/data/sallen/shared/SalishSeaCast/forcing/LiveOcean/",
            ),
        ),
    )
    def test_boundary_condition_dir(self, host, bc_dir, prod_config):
        assert prod_config["run"]["enabled hosts"][host]["forcing"]["bc dir"] == bc_dir


@pytest.mark.parametrize(
    "run_type, host_name, shared_storage",
    (
        ("nowcast+", "arbutus.cloud-nowcast", False),
        ("nowcast+", "orcinus-nowcast-agrif", False),
        ("nowcast+", "salish-nowcast", True),
        ("ssh", "arbutus.cloud-nowcast", False),
        ("nowcast-green", "arbutus.cloud-nowcast", False),
        ("nowcast-agrif", "orcinus-nowcast-agrif", False),
        ("forecast2", "arbutus.cloud-nowcast", False),
        ("forecast2", "orcinus-nowcast-agrif", False),
    ),
)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(self, run_type, host_name, shared_storage, caplog):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
            shared_storage=shared_storage,
            run_date=arrow.get("2020-04-11"),
        )
        caplog.set_level(logging.INFO)

        msg_type = make_forcing_links.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"{run_type} 2020-04-11 forcing file links on {host_name} created"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize(
    "run_type, host_name, shared_storage",
    (
        ("nowcast+", "arbutus.cloud-nowcast", False),
        ("nowcast+", "orcinus-nowcast-agrif", False),
        ("nowcast+", "salish-nowcast", True),
        ("ssh", "arbutus.cloud-nowcast", False),
        ("nowcast-green", "arbutus.cloud-nowcast", False),
        ("nowcast-agrif", "orcinus-nowcast-agrif", False),
        ("forecast2", "arbutus.cloud-nowcast", False),
        ("forecast2", "orcinus-nowcast-agrif", False),
    ),
)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(self, run_type, host_name, shared_storage, caplog):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
            shared_storage=shared_storage,
            run_date=arrow.get("2020-04-11"),
        )
        caplog.set_level(logging.CRITICAL)

        msg_type = make_forcing_links.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = (
            f"{run_type} 2020-04-11 forcing file links creation on {host_name} failed"
        )
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {run_type}"


@patch("nowcast.workers.make_forcing_links._create_symlink", autospec=True)
@patch("nowcast.workers.make_forcing_links._clear_links", autospec=True)
class TestMakeRunoffLinks:
    """Unit tests for _make_runoff_links() function.
    """

    @pytest.mark.parametrize("run_type", ["nowcast+", "forecast2", "ssh"])
    def test_clear_links(self, m_clear_links, m_create_symlink, run_type, config):
        run_date = arrow.get("2016-03-11")
        m_sftp_client = Mock(name="sftp_client")
        make_forcing_links._make_runoff_links(
            m_sftp_client, run_type, run_date, config, "salish-nowcast"
        )
        m_clear_links.assert_called_once_with(
            m_sftp_client,
            Path(config["run"]["enabled hosts"]["salish-nowcast"]["run prep dir"]),
            "rivers",
        )

    @pytest.mark.parametrize("run_type", ["nowcast+", "forecast2", "ssh"])
    def test_runoff_files_links(
        self, m_clear_links, m_create_symlink, run_type, config
    ):
        run_date = arrow.get("2016-03-11")
        m_sftp_client = Mock(name="sftp_client")
        make_forcing_links._make_runoff_links(
            m_sftp_client, run_type, run_date, config, "salish-nowcast"
        )
        start = run_date.shift(days=-1)
        end = run_date.shift(days=+2)
        for date in arrow.Arrow.range("day", start, end):
            expected = call(
                m_sftp_client,
                "salish-nowcast",
                Path(
                    "/results/forcing/rivers/RFraserCElse_{:y%Ym%md%d}.nc".format(
                        start.date()
                    )
                ),
                Path("runs/rivers/RFraserCElse_{:y%Ym%md%d}.nc".format(date.date())),
            )
            assert expected in m_create_symlink.call_args_list
            expected = call(
                m_sftp_client,
                "salish-nowcast",
                Path(
                    "/results/forcing/rivers/RLonFraCElse_{:y%Ym%md%d}.nc".format(
                        start.date()
                    )
                ),
                Path("runs/rivers/RLonFraCElse_{:y%Ym%md%d}.nc".format(date.date())),
            )
            assert expected in m_create_symlink.call_args_list

    def test_runoff_files_links_turbidity(
        self, m_clear_links, m_create_symlink, config
    ):
        run_date = arrow.get("2017-08-12")
        m_sftp_client = Mock(name="sftp_client")
        make_forcing_links._make_runoff_links(
            m_sftp_client, "nowcast-green", run_date, config, "salish-nowcast"
        )
        start = run_date.shift(days=-1)
        end = run_date.shift(days=+2)
        for date in arrow.Arrow.range("day", start, end):
            expected = call(
                m_sftp_client,
                "salish-nowcast",
                Path(
                    "/results/forcing/rivers/RFraserCElse_{:y%Ym%md%d}.nc".format(
                        start.date()
                    )
                ),
                Path("runs/rivers/RFraserCElse_{:y%Ym%md%d}.nc".format(date.date())),
            )
            assert expected in m_create_symlink.call_args_list
            expected = call(
                m_sftp_client,
                "salish-nowcast",
                Path(
                    "/results/forcing/rivers/RLonFraCElse_{:y%Ym%md%d}.nc".format(
                        start.date()
                    )
                ),
                Path("runs/rivers/RLonFraCElse_{:y%Ym%md%d}.nc".format(date.date())),
            )
            assert expected in m_create_symlink.call_args_list
        expected = call(
            m_sftp_client,
            "salish-nowcast",
            Path(
                "/results/forcing/rivers/river_turb/"
                "riverTurbDaily2_{:y%Ym%md%d}.nc".format(run_date.date())
            ),
            Path("runs/rivers/riverTurbDaily2_{:y%Ym%md%d}.nc".format(run_date.date())),
        )
        assert expected in m_create_symlink.call_args_list
