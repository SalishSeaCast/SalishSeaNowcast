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
"""Unit tests for SalishSeaCast download_results worker.
"""
import logging
import shlex
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import pytest

from nowcast import lib
from nowcast.workers import download_results


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                file group: allen

                results archive:
                  nowcast: SalishSea/nowcast/
                  forecast: SalishSea/forecast/
                  forecast2: SalishSea/forecast2/
                  nowcast-green: SalishSea/nowcast-green/
                  nowcast-agrif: SalishSea/nowcast-agrif/
                  hindcast:
                    localhost: SalishSea/hindcast/
                    graham-dtn: nearline/SalishSea/hindcast/

                run:
                  enabled hosts:
                    arbutus.cloud-nowcast:
                      run types:
                        nowcast:
                          results: SalishSea/nowcast/
                        forecast:
                          results: SalishSea/forecast/
                        forecast2:
                          results: SalishSea/forecast2/
                        nowcast-green:
                          results: SalishSea/nowcast-green/
                    orcinus-nowcast-agrif:
                      run types:
                        nowcast-agrif:
                          results: SalishSea/nowcast-agrif/
                    graham-dtn:
                      ssh key: SalishSeaNEMO-nowcast_id_rsa

                  hindcast hosts:
                      optimum-hindcast:
                        run types:
                          hindcast:
                            results: SalishSea/hindcast
                      sockeye-hindcast:
                        run types:
                          hindcast:
                            results: SalishSea/hindcast
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(download_results, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = download_results.main()
        assert worker.name == "download_results"
        assert worker.description.startswith(
            "SalishSeaCast worker that downloads the results files from a run"
        )

    def test_add_host_name_arg(self, mock_worker):
        worker = download_results.main()
        assert worker.cli.parser._actions[3].dest == "host_name"
        assert worker.cli.parser._actions[3].help

    def test_add_run_type_arg(self, mock_worker):
        worker = download_results.main()
        assert worker.cli.parser._actions[4].dest == "run_type"
        expected = {
            "nowcast",
            "nowcast-green",
            "forecast",
            "forecast2",
            "hindcast",
            "nowcast-agrif",
        }
        assert worker.cli.parser._actions[4].choices == expected
        assert worker.cli.parser._actions[4].help

    def test_add_dest_host_option(self, mock_worker):
        worker = download_results.main()
        assert worker.cli.parser._actions[5].dest == "dest_host"
        assert worker.cli.parser._actions[5].default == "localhost"
        assert worker.cli.parser._actions[5].help

    def test_add_run_date_option(self, mock_worker):
        worker = download_results.main()
        assert worker.cli.parser._actions[6].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[6].type == expected
        assert worker.cli.parser._actions[6].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[6].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "download_results" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["download_results"]
        assert msg_registry["checklist key"] == "results files"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["download_results"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success nowcast",
            "failure nowcast",
            "success nowcast-green",
            "failure nowcast-green",
            "success forecast",
            "failure forecast",
            "success forecast2",
            "failure forecast2",
            "success hindcast",
            "failure hindcast",
            "success nowcast-agrif",
            "failure nowcast-agrif",
            "crash",
        ]

    def test_hindcast_hosts(self, prod_config):
        assert list(prod_config["run"]["hindcast hosts"].keys()) == [
            "optimum-hindcast",
            "sockeye-hindcast",
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
        "host, run_types",
        (
            (
                "arbutus.cloud-nowcast",
                ["nowcast", "forecast", "forecast2", "nowcast-green"],
            ),
            ("salish-nowcast", ["nowcast-dev", "nowcast-green"]),
            ("orcinus-nowcast-agrif", ["nowcast-agrif"]),
            ("graham-dtn", []),
            ("optimum-hindcast", []),
        ),
    )
    def test_enabled_host_run_types(self, host, run_types, prod_config):
        assert list(prod_config["run"]["enabled hosts"][host]["run types"]) == run_types

    @pytest.mark.parametrize(
        "host_group, host, run_type, results_dir",
        (
            (
                "enabled hosts",
                "arbutus.cloud-nowcast",
                "nowcast",
                "/nemoShare/MEOPAR/SalishSea/nowcast/",
            ),
            (
                "enabled hosts",
                "arbutus.cloud-nowcast",
                "forecast",
                "/nemoShare/MEOPAR/SalishSea/forecast/",
            ),
            (
                "enabled hosts",
                "arbutus.cloud-nowcast",
                "forecast2",
                "/nemoShare/MEOPAR/SalishSea/forecast2/",
            ),
            (
                "enabled hosts",
                "arbutus.cloud-nowcast",
                "nowcast-green",
                "/nemoShare/MEOPAR/SalishSea/nowcast-green/",
            ),
            (
                "enabled hosts",
                "salish-nowcast",
                "nowcast-dev",
                "/results/SalishSea/nowcast-dev.201905/",
            ),
            (
                "enabled hosts",
                "salish-nowcast",
                "nowcast-green",
                "/results2/SalishSea/nowcast-green.201905/",
            ),
            (
                "enabled hosts",
                "orcinus-nowcast-agrif",
                "nowcast-agrif",
                "/global/scratch/dlatorne/nowcast-agrif/",
            ),
            (
                "hindcast hosts",
                "optimum-hindcast",
                "hindcast",
                "/scratch/sallen/dlatorne/v201905r/",
            ),
            (
                "hindcast hosts",
                "sockeye-hindcast",
                "hindcast",
                "/scratch/sallen1/hindcast_v201905_long/",
            ),
        ),
    )
    def test_run_type_results_dir(
        self, host_group, host, run_type, results_dir, prod_config
    ):
        assert (
            prod_config["run"][host_group][host]["run types"][run_type]["results"]
            == results_dir
        )

    def test_results_archive(self, prod_config):
        archives = {
            "nowcast": "/results/SalishSea/nowcast-blue.201905/",
            "nowcast-dev": "/results/SalishSea/nowcast-dev.201905/",
            "forecast": "/results/SalishSea/forecast.201905/",
            "forecast2": "/results/SalishSea/forecast2.201905/",
            "nowcast-green": "/results2/SalishSea/nowcast-green.201905/",
            "nowcast-agrif": "/results/SalishSea/nowcast-agrif.201702/",
            "hindcast": {
                "localhost": "/results2/SalishSea/nowcast-green.201905/",
                "graham-dtn": "/nearline/rrg-allen/SalishSea/nowcast-green.201905/",
            },
        }
        assert prod_config["results archive"].keys() == archives.keys()
        for run_type, results_dir in archives.items():
            assert prod_config["results archive"][run_type] == results_dir

    def test_file_group(self, prod_config):
        assert prod_config["file group"] == "sallen"


@pytest.mark.parametrize(
    "run_type, host_name",
    [
        ("nowcast", "arbutus.cloud-nowcast"),
        ("nowcast-green", "arbutus.cloud-nowcast"),
        ("forecast", "arbutus.cloud-nowcast"),
        ("forecast2", "arbutus.cloud-nowcast"),
        ("hindcast", "optimum-hindcast"),
        ("nowcast-agrif", "orcinus-nowcast-agrif"),
    ],
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, run_type, host_name, caplog):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2017-12-24")
        )
        caplog.set_level(logging.INFO)
        msg_type = download_results.success(parsed_args)
        assert caplog.records[0].levelname == "INFO"
        assert caplog.messages[0].endswith(f"results files from {host_name} downloaded")
        assert msg_type == "success {}".format(run_type)


@pytest.mark.parametrize(
    "run_type, host_name",
    [
        ("nowcast", "arbutus.cloud-nowcast"),
        ("nowcast-green", "arbutus.cloud-nowcast"),
        ("forecast", "arbutus.cloud-nowcast"),
        ("forecast2", "arbutus.cloud-nowcast"),
        ("hindcast", "optimum-hindcast"),
        ("nowcast-agrif", "orcinus-nowcast-agrif"),
    ],
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, run_type, host_name, caplog):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2017-12-24")
        )
        caplog.set_level(logging.CRITICAL)
        msg_type = download_results.failure(parsed_args)
        assert caplog.records[0].levelname == "CRITICAL"
        assert caplog.messages[0].endswith(
            f"results files download from {host_name} failed"
        )
        assert msg_type == "failure {}".format(run_type)


@patch("nowcast.workers.download_results.lib.run_in_subprocess", spec=True)
@patch("nowcast.workers.download_results.lib.fix_perms", autospec=True)
class TestDownloadResults:
    """Unit tests for download_results() function."""

    @pytest.mark.parametrize(
        "run_type",
        [
            "nowcast",
            "nowcast-green",
            "forecast",
            "forecast2",
            "hindcast",
            "nowcast-agrif",
        ],
    )
    def test_unrecognized_host(
        self, m_fix_perms, m_run_in_subproc, run_type, config, caplog, monkeypatch
    ):
        parsed_args = SimpleNamespace(
            host_name="foo",
            run_type=run_type,
            dest_host="localhost",
            run_date=arrow.get("2018-05-22"),
        )
        monkeypatch.setitem(config, "run", {"hindcast hosts": {"optimum-hindcast": {}}})
        monkeypatch.setitem(
            config, "run", {"enabled hosts": {"arbutus.cloud-nowcast": {}}}
        )
        caplog.set_level(logging.CRITICAL)
        with pytest.raises(nemo_nowcast.WorkerError):
            download_results.download_results(parsed_args, config)
        assert caplog.records[0].levelname == "CRITICAL"
        assert caplog.messages[0] == "unrecognized host: foo"

    @pytest.mark.parametrize(
        "run_type, host_name",
        [
            ("nowcast", "arbutus.cloud-nowcast"),
            ("nowcast-green", "arbutus.cloud-nowcast"),
            ("forecast", "arbutus.cloud-nowcast"),
            ("forecast2", "arbutus.cloud-nowcast"),
            ("hindcast", "optimum-hindcast"),
            ("nowcast-agrif", "orcinus-nowcast-agrif"),
        ],
    )
    def test_scp_to_localhost_subprocess(
        self, m_fix_perms, m_run_in_subproc, run_type, host_name, config
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
            dest_host="localhost",
            run_date=arrow.get("2018-05-22"),
        )
        download_results.download_results(parsed_args, config)
        m_run_in_subproc.assert_called_once_with(
            shlex.split(
                f"scp -pr {host_name}:SalishSea/{run_type}/22may18 SalishSea/{run_type}"
            ),
            download_results.logger.debug,
            download_results.logger.error,
        )

    def test_scp_to_dest_host_subprocess(
        self, m_fix_perms, m_run_in_subproc, config, monkeypatch
    ):
        def mock_tidy_dest_host(*args):
            pass

        monkeypatch.setattr(download_results, "_tidy_dest_host", mock_tidy_dest_host)

        parsed_args = SimpleNamespace(
            host_name="sockeye-hindcast",
            run_type="hindcast",
            dest_host="graham-dtn",
            run_date=arrow.get("2019-09-03"),
        )
        download_results.download_results(parsed_args, config)
        m_run_in_subproc.assert_called_once_with(
            shlex.split(
                "scp -pr sockeye-hindcast:SalishSea/hindcast/03sep19 graham-dtn:nearline/SalishSea/hindcast"
            ),
            download_results.logger.debug,
            download_results.logger.error,
        )

    @pytest.mark.parametrize(
        "run_type, host_name",
        [
            ("nowcast", "arbutus.cloud-nowcast"),
            ("forecast", "arbutus.cloud-nowcast"),
            ("forecast2", "arbutus.cloud-nowcast"),
        ],
    )
    def test_unlink_fvcom_boundary_files(
        self,
        m_fix_perms,
        m_run_in_subproc,
        run_type,
        host_name,
        config,
        tmp_path,
        monkeypatch,
    ):
        fvcom_t = tmp_path / "FVCOM_T.nc"
        fvcom_t.write_bytes(b"")
        fvcom_u = tmp_path / "FVCOM_U.nc"
        fvcom_u.write_bytes(b"")
        fvcom_v = tmp_path / "FVCOM_V.nc"
        fvcom_v.write_bytes(b"")
        fvcom_w = tmp_path / "FVCOM_W.nc"
        fvcom_w.write_bytes(b"")

        def mock_glob(path, pattern):
            return (
                [fvcom_t, fvcom_u, fvcom_v, fvcom_w]
                if pattern.startswith("FVCOM")
                else []
            )

        monkeypatch.setattr(download_results.Path, "glob", mock_glob)

        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
            dest_host="localhost",
            run_date=arrow.get("2018-05-22"),
        )
        download_results.download_results(parsed_args, config)
        assert not fvcom_t.exists()
        assert not fvcom_u.exists()
        assert not fvcom_v.exists()
        assert not fvcom_w.exists()

    @pytest.mark.parametrize(
        "host_name, dest_host",
        (("optimum-hindcast", "localhost"), ("sockeye-hindcast", "graham-dtn")),
    )
    def test_hindcast_not_unlink_fvcom_boundary_files(
        self,
        m_fix_perms,
        m_run_in_subproc,
        host_name,
        dest_host,
        config,
        tmp_path,
        monkeypatch,
    ):
        def mock_glob(*args):
            return []

        monkeypatch.setattr(download_results.Path, "glob", mock_glob)

        def mock_tidy_dest_host(*args):
            pass

        monkeypatch.setattr(download_results, "_tidy_dest_host", mock_tidy_dest_host)

        fvcom_t = tmp_path / "FVCOM_T.nc"
        fvcom_t.write_bytes(b"")
        fvcom_u = tmp_path / "FVCOM_U.nc"
        fvcom_u.write_bytes(b"")
        fvcom_v = tmp_path / "FVCOM_V.nc"
        fvcom_v.write_bytes(b"")
        fvcom_w = tmp_path / "FVCOM_W.nc"
        fvcom_w.write_bytes(b"")

        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type="hindcast",
            dest_host=dest_host,
            run_date=arrow.get("2019-09-03"),
        )
        download_results.download_results(parsed_args, config)
        assert fvcom_t.exists()
        assert fvcom_u.exists()
        assert fvcom_v.exists()
        assert fvcom_w.exists()

    @pytest.mark.parametrize(
        "run_type, host_name",
        [
            ("nowcast", "arbutus.cloud-nowcast"),
            ("nowcast-green", "arbutus.cloud-nowcast"),
            ("forecast", "arbutus.cloud-nowcast"),
            ("forecast2", "arbutus.cloud-nowcast"),
            ("hindcast", "optimum-hindcast"),
            ("nowcast-agrif", "orcinus-nowcast-agrif"),
        ],
    )
    def test_results_dir_fix_perms(
        self, m_fix_perms, m_run_in_subproc, run_type, host_name, config
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
            dest_host="localhost",
            run_date=arrow.get("2018-05-22"),
        )
        download_results.download_results(parsed_args, config)
        assert m_fix_perms.call_args_list[0][0] == (
            Path("SalishSea", run_type, "22may18"),
        )
        assert m_fix_perms.call_args_list[0][1] == {
            "mode": int(lib.FilePerms(user="rwx", group="rwx", other="rx")),
            "grp_name": "allen",
        }

    @pytest.mark.parametrize(
        "run_type, host_name",
        [
            ("nowcast", "arbutus.cloud-nowcast"),
            ("nowcast-green", "arbutus.cloud-nowcast"),
            ("forecast", "arbutus.cloud-nowcast"),
            ("forecast2", "arbutus.cloud-nowcast"),
            ("hindcast", "optimum-hindcast"),
            ("nowcast-agrif", "orcinus-nowcast-agrif"),
        ],
    )
    def test_results_files_fix_perms(
        self, m_fix_perms, m_run_in_subproc, run_type, host_name, config
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
            dest_host="localhost",
            run_date=arrow.get("2018-05-22"),
        )
        p_glob = patch(
            "nowcast.workers.download_results.Path.glob",
            side_effect=[[Path("namelist_cfg")], [], []]
            if run_type == "hindcast"
            else [[], [Path("namelist_cfg")], [], []],
        )
        with p_glob:
            download_results.download_results(parsed_args, config)
        assert m_fix_perms.call_args_list[1][0] == (Path("namelist_cfg"),)
        assert m_fix_perms.call_args_list[1][1] == {"grp_name": "allen"}

    @pytest.mark.parametrize(
        "run_type, host_name",
        [
            ("nowcast", "arbutus.cloud-nowcast"),
            ("nowcast-green", "arbutus.cloud-nowcast"),
            ("forecast", "arbutus.cloud-nowcast"),
            ("forecast2", "arbutus.cloud-nowcast"),
            ("hindcast", "optimum-hindcast"),
            ("nowcast-agrif", "orcinus-nowcast-agrif"),
        ],
    )
    def test_checklist(
        self, m_fix_perms, m_run_in_subproc, run_type, host_name, config
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            run_type=run_type,
            dest_host="localhost",
            run_date=arrow.get("2018-05-22"),
        )
        p_glob = patch(
            "nowcast.workers.download_results.Path.glob",
            side_effect=[
                [],
                [Path("Salishsea_1h_20180522_20180522_grid_T.nc")],
                [Path("Salishsea_1d_20180522_20180522_grid_T.nc")],
            ]
            if run_type == "hindcast"
            else [
                [],
                [],
                [Path("Salishsea_1h_20180522_20180522_grid_T.nc")],
                [Path("Salishsea_1d_20180522_20180522_grid_T.nc")],
            ],
        )
        with p_glob:
            checklist = download_results.download_results(parsed_args, config)
        assert checklist == {
            run_type: {
                "run date": "2018-05-22",
                "1h": ["Salishsea_1h_20180522_20180522_grid_T.nc"],
                "1d": ["Salishsea_1d_20180522_20180522_grid_T.nc"],
            }
        }

    def test_checklist_agrif(self, m_fix_perms, m_run_in_subproc, config):
        parsed_args = SimpleNamespace(
            host_name="orcinus-nowcast-agrif",
            run_type="nowcast-agrif",
            dest_host="localhost",
            run_date=arrow.get("2018-12-07"),
        )
        p_glob = patch(
            "nowcast.workers.download_results.Path.glob",
            side_effect=[
                [],
                [],
                [Path("1_Salishsea_1h_20180522_20180522_grid_T.nc")],
                [
                    Path("1_Salishsea_1d_20180522_20180522_grid_T.nc"),
                    Path("Salishsea_1d_20180522_20180522_grid_T.nc"),
                ],
            ],
        )
        with p_glob:
            checklist = download_results.download_results(parsed_args, config)
        assert checklist == {
            "nowcast-agrif": {
                "run date": "2018-12-07",
                "1h": ["1_Salishsea_1h_20180522_20180522_grid_T.nc"],
                "1d": [
                    "1_Salishsea_1d_20180522_20180522_grid_T.nc",
                    "Salishsea_1d_20180522_20180522_grid_T.nc",
                ],
            }
        }
