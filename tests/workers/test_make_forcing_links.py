#  Copyright 2013 – present The Salish Sea MEOPAR contributors
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
import os
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_forcing_links


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                ssh:
                  file template: "ssh_{:y%Ym%md%d}.nc"
                rivers:
                  file templates:
                    b201702: "R201702DFraCElse_{:y%Ym%md%d}.nc"
                  turbidity:
                    file template: "riverTurbDaily2_{:y%Ym%md%d}.nc"

                run:
                  enabled hosts:
                    arbutus.cloud:
                      run prep dir: runs/
                      forcing:
                        ssh dir: sshNeahBay/
                        rivers dir: rivers/
                        Fraser turbidity dir: rivers/river_turb/

                    salish-nowcast:
                      run prep dir: runs/
                      forcing:
                        ssh dir: sshNeahBay/
                        rivers dir: rivers/
                        Fraser turbidity dir: rivers/river_turb/
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
    """Unit tests for main() function."""

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
    """Unit tests for production YAML config file elements related to worker."""

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
            "graham-dtn",
            "optimum-hindcast",
        ]

    @pytest.mark.parametrize(
        "host, ssh_key",
        (
            ("arbutus.cloud-nowcast", "SalishSeaNEMO-nowcast_id_rsa"),
            ("salish-nowcast", "SalishSeaNEMO-nowcast_id_rsa"),
            ("orcinus-nowcast-agrif", "SalishSeaNEMO-nowcast_id_rsa"),
            ("graham-dtn", "SalishSeaNEMO-nowcast_id_rsa"),
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
            ("graham-dtn", "/project/def-allen/SalishSea/forcing/sshNeahBay/"),
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
            ("graham-dtn", "/project/def-allen/SalishSea/forcing/rivers/"),
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
                "graham-dtn",
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
                "graham-dtn",
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
            ("graham-dtn", "/project/def-allen/SalishSea/forcing/LiveOcean/"),
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
    """Unit tests for success() function."""

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
    """Unit tests for failure() function."""

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


@pytest.fixture()
def mock_clear_links(monkeypatch):
    def mock_clear_links(sftp_client, run_prep_dir, forcing_dir):
        pass

    monkeypatch.setattr(make_forcing_links, "_clear_links", mock_clear_links)


@pytest.fixture
def mock_sftp_client(monkeypatch):
    class MockSFTPClient:
        def symlink(self, src, dst):
            os.symlink(src, dst)

    return MockSFTPClient()


class TestMakeNeahBaySshLinks:
    """Unit tests for _make_NeahBay_ssh_links() function."""

    @staticmethod
    def prep_files(run_date, host_config, config, tmp_path):
        ssh_dir = tmp_path / host_config["forcing"]["ssh dir"]
        ssh_dir.mkdir()
        (ssh_dir / "fcst").mkdir()
        run_prep_dir = tmp_path / host_config["run prep dir"]
        run_prep_dir.mkdir()
        (run_prep_dir / "ssh").mkdir()
        filename_tmpl = config["ssh"]["file template"]
        filenames = [
            filename_tmpl.format(run_date.shift(days=day).date())
            for day in range(-1, 3)
        ]
        for filename in filenames:
            (ssh_dir / "fcst" / filename).write_text("")
        return ssh_dir, filenames, run_prep_dir

    def test_make_NeahBay_ssh_links(
        self, config, mock_clear_links, mock_sftp_client, caplog, tmp_path, monkeypatch
    ):
        run_date = arrow.get("2020-04-11")
        host_config = config["run"]["enabled hosts"]["arbutus.cloud"]
        ssh_dir, filenames, run_prep_dir = self.prep_files(
            run_date, host_config, config, tmp_path
        )
        monkeypatch.setitem(host_config, "run prep dir", run_prep_dir)
        monkeypatch.setitem(host_config["forcing"], "ssh dir", ssh_dir)
        caplog.set_level(logging.DEBUG)

        make_forcing_links._make_NeahBay_ssh_links(
            mock_sftp_client, run_date, config, "arbutus.cloud", shared_storage=False
        )

        for i, filename in enumerate(filenames):
            expected = run_prep_dir / "ssh" / filename
            assert expected.is_symlink()
            assert caplog.records[i].levelname == "DEBUG"
            assert (
                caplog.messages[i]
                == f"{ssh_dir/'fcst'/filename} symlinked as {expected} on arbutus.cloud"
            )

    def test_shared_storage_copy(
        self, config, mock_clear_links, mock_sftp_client, caplog, tmp_path, monkeypatch
    ):
        run_date = arrow.get("2020-04-12")
        host_config = config["run"]["enabled hosts"]["salish-nowcast"]
        ssh_dir, filenames, run_prep_dir = self.prep_files(
            run_date, host_config, config, tmp_path
        )
        monkeypatch.setitem(host_config["forcing"], "ssh dir", ssh_dir)
        monkeypatch.setitem(host_config, "run prep dir", run_prep_dir)
        caplog.set_level(logging.DEBUG)

        make_forcing_links._make_NeahBay_ssh_links(
            mock_sftp_client, run_date, config, "salish-nowcast", shared_storage=True
        )

        for i, filename in enumerate(filenames):
            expected = run_prep_dir / "ssh" / filename
            assert expected.is_file()
            assert caplog.records[i].levelname == "DEBUG"
            assert (
                caplog.messages[i]
                == f"{ssh_dir/'fcst'/filename} copied to {expected} on salish-nowcast"
            )


class TestMakeRunoffLinks:
    """Unit tests for _make_runoff_links() function."""

    @staticmethod
    def prep_files(run_date, host_config, config, tmp_path):
        rivers_dir = tmp_path / host_config["forcing"]["rivers dir"]
        rivers_dir.mkdir()
        run_prep_dir = tmp_path / host_config["run prep dir"]
        run_prep_dir.mkdir()
        (run_prep_dir / "rivers").mkdir()
        filename_tmpls = config["rivers"]["file templates"]
        filenames = [
            tmpl.format(run_date.shift(days=-1).date())
            for tmpl in filename_tmpls.values()
        ]
        for filename in filenames:
            (rivers_dir / filename).write_text("")
        return rivers_dir, filenames, run_prep_dir

    @pytest.mark.parametrize(
        "run_type, host",
        (
            ("nowcast+", "arbutus.cloud"),
            ("nowcast+", "salish-nowcast"),
            ("forecast2", "arbutus.cloud"),
            ("forecast2", "salish-nowcast"),
            ("ssh", "arbutus.cloud"),
            ("ssh", "salish-nowcast"),
            ("nowcast-green", "arbutus.cloud"),
            ("nowcast-agrif", "arbutus.cloud"),
        ),
    )
    def test_runoff_files_links(
        self,
        mock_clear_links,
        mock_sftp_client,
        run_type,
        host,
        config,
        caplog,
        tmp_path,
        monkeypatch,
    ):
        run_date = arrow.get("2020-04-12")
        host_config = config["run"]["enabled hosts"][host]
        rivers_dir, filenames, run_prep_dir = self.prep_files(
            run_date, host_config, config, tmp_path
        )
        monkeypatch.setitem(host_config, "run prep dir", run_prep_dir)
        monkeypatch.setitem(host_config["forcing"], "rivers dir", rivers_dir)
        caplog.set_level(logging.DEBUG)

        make_forcing_links._make_runoff_links(
            mock_sftp_client, run_type, run_date, config, host
        )

        filename_tmpls = config["rivers"]["file templates"]
        i = 0
        for tmpl in filename_tmpls.values():
            src_filename = tmpl.format(run_date.shift(days=-1).date())
            for day in range(-1, 3):
                filename = tmpl.format(run_date.shift(days=day).date())
                expected = run_prep_dir / "rivers" / filename
                assert expected.is_symlink()
                assert caplog.records[i].levelname == "DEBUG"
                expected = (
                    f"{rivers_dir/src_filename} symlinked as {expected} on {host}"
                )
                assert caplog.messages[i] == expected
                i += 1

    @pytest.mark.parametrize(
        "run_type, host",
        (
            ("nowcast-green", "arbutus.cloud"),
            ("nowcast-agrif", "arbutus.cloud"),
        ),
    )
    def test_runoff_files_links_turbidity(
        self,
        mock_clear_links,
        mock_sftp_client,
        run_type,
        host,
        config,
        caplog,
        tmp_path,
        monkeypatch,
    ):
        run_date = arrow.get("2020-04-12")
        host_config = config["run"]["enabled hosts"][host]
        rivers_dir, _, run_prep_dir = self.prep_files(
            run_date, host_config, config, tmp_path
        )
        monkeypatch.setitem(host_config, "run prep dir", run_prep_dir)
        monkeypatch.setitem(host_config["forcing"], "rivers dir", rivers_dir)
        rivers_turb_dir = tmp_path / host_config["forcing"]["Fraser turbidity dir"]
        rivers_turb_dir.mkdir()
        monkeypatch.setitem(
            host_config["forcing"], "Fraser turbidity dir", rivers_turb_dir
        )
        filename_tmpl = config["rivers"]["turbidity"]["file template"]
        turb_filename = filename_tmpl.format(run_date.date())
        (rivers_turb_dir / turb_filename).write_text("")
        caplog.set_level(logging.DEBUG)

        make_forcing_links._make_runoff_links(
            mock_sftp_client, run_type, run_date, config, host
        )

        expected = run_prep_dir / "rivers" / turb_filename
        assert expected.is_symlink()
        assert caplog.records[-1].levelname == "DEBUG"
        assert (
            caplog.messages[-1]
            == f"{rivers_turb_dir/turb_filename} symlinked as {expected} on {host}"
        )
