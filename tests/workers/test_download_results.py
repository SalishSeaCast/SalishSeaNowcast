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
"""Unit tests for Salish Sea NEMO nowcast download_results worker.
"""
import logging
from pathlib import Path
import shlex
import textwrap
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

import nowcast.lib
from nowcast.workers import download_results


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
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
                  hindcast: SalishSea/hindcast/
                
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
                  hindcast hosts:
                      cedar-hindcast:
                        run types:
                          hindcast:
                            results: SalishSea/hindcast
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.download_results.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_results.main()
        args, kwargs = m_worker.call_args
        assert args == ("download_results",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_results.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_results.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_results.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        expected = {
            "nowcast",
            "nowcast-green",
            "forecast",
            "forecast2",
            "hindcast",
            "nowcast-agrif",
        }
        assert kwargs["choices"] == expected
        assert "help" in kwargs

    def test_add_run_date_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_results.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_results.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            download_results.download_results,
            download_results.success,
            download_results.failure,
        )


@pytest.mark.parametrize(
    "run_type, host_name",
    [
        ("nowcast", "arbutus.cloud-nowcast"),
        ("nowcast-green", "arbutus.cloud-nowcast"),
        ("forecast", "arbutus.cloud-nowcast"),
        ("forecast2", "arbutus.cloud-nowcast"),
        ("hindcast", "cedar-hindcast"),
        ("nowcast-agrif", "orcinus-nowcast-agrif"),
    ],
)
@patch("nowcast.workers.download_results.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(self, m_logger, run_type, host_name):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2017-12-24")
        )
        msg_type = download_results.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == "success {}".format(run_type)


@pytest.mark.parametrize(
    "run_type, host_name",
    [
        ("nowcast", "arbutus.cloud-nowcast"),
        ("nowcast-green", "arbutus.cloud-nowcast"),
        ("forecast", "arbutus.cloud-nowcast"),
        ("forecast2", "arbutus.cloud-nowcast"),
        ("hindcast", "cedar-hindcast"),
        ("nowcast-agrif", "orcinus-nowcast-agrif"),
    ],
)
@patch("nowcast.workers.download_results.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(self, m_logger, run_type, host_name):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2017-12-24")
        )
        msg_type = download_results.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == "failure {}".format(run_type)


@patch("nowcast.workers.download_results.logger", autospec=True)
@patch("nowcast.workers.download_results.lib.run_in_subprocess", spec=True)
@patch("nowcast.workers.download_results.lib.fix_perms", autospec=True)
class TestDownloadResults:
    """Unit tests for download_results() function.
    """

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
        self, m_fix_perms, m_run_in_subproc, m_logger, run_type, config
    ):
        parsed_args = SimpleNamespace(
            host_name="foo", run_type=run_type, run_date=arrow.get("2018-05-22")
        )
        config = {}
        with pytest.raises(nemo_nowcast.WorkerError):
            download_results.download_results(parsed_args, config)

    @pytest.mark.parametrize(
        "run_type, host_name",
        [
            ("nowcast", "arbutus.cloud-nowcast"),
            ("nowcast-green", "arbutus.cloud-nowcast"),
            ("forecast", "arbutus.cloud-nowcast"),
            ("forecast2", "arbutus.cloud-nowcast"),
            ("hindcast", "cedar-hindcast"),
            ("nowcast-agrif", "orcinus-nowcast-agrif"),
        ],
    )
    def test_scp_subprocess(
        self, m_fix_perms, m_run_in_subproc, m_logger, run_type, host_name, config
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2018-05-22")
        )
        download_results.download_results(parsed_args, config)
        m_run_in_subproc.assert_called_once_with(
            shlex.split(
                f"scp -pr {host_name}:SalishSea/{run_type}/22may18 SalishSea/{run_type}"
            ),
            m_logger.debug,
            m_logger.error,
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
        self, m_fix_perms, m_run_in_subproc, m_logger, run_type, host_name, config
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2018-05-22")
        )
        m_fvcom_t = Mock(name="FVCOM_T.nc")
        m_fvcom_u = Mock(name="FVCOM_U.nc")
        m_fvcom_v = Mock(name="FVCOM_V.nc")
        m_fvcom_w = Mock(name="FVCOM_W.nc")
        p_glob = patch(
            "nowcast.workers.download_results.Path.glob",
            side_effect=[[m_fvcom_t, m_fvcom_u, m_fvcom_v, m_fvcom_w], [], [], []],
        )
        with p_glob:
            download_results.download_results(parsed_args, config)
        assert m_fvcom_t.unlink.called
        assert m_fvcom_u.unlink.called
        assert m_fvcom_v.unlink.called
        assert m_fvcom_w.unlink.called

    def test_hindcast_not_unlink_fvcom_boundary_files(
        self, m_fix_perms, m_run_in_subproc, m_logger, config
    ):
        parsed_args = SimpleNamespace(
            host_name="cedar-hindcast",
            run_type="hindcast",
            run_date=arrow.get("2018-12-06"),
        )
        m_fvcom_t = Mock(name="FVCOM_T.nc")
        m_fvcom_u = Mock(name="FVCOM_U.nc")
        m_fvcom_v = Mock(name="FVCOM_V.nc")
        m_fvcom_w = Mock(name="FVCOM_W.nc")
        with patch(
            "nowcast.workers.download_results.Path.glob", side_effect=[[], [], []]
        ):
            download_results.download_results(parsed_args, config)
        assert not m_fvcom_t.unlink.called
        assert not m_fvcom_u.unlink.called
        assert not m_fvcom_v.unlink.called
        assert not m_fvcom_w.unlink.called

    @pytest.mark.parametrize(
        "run_type, host_name",
        [
            ("nowcast", "arbutus.cloud-nowcast"),
            ("nowcast-green", "arbutus.cloud-nowcast"),
            ("forecast", "arbutus.cloud-nowcast"),
            ("forecast2", "arbutus.cloud-nowcast"),
            ("hindcast", "cedar-hindcast"),
            ("nowcast-agrif", "orcinus-nowcast-agrif"),
        ],
    )
    @patch("nowcast.workers.download_results.lib.FilePerms", autospec=True)
    def test_results_dir_fix_perms(
        self,
        m_file_perms,
        m_fix_perms,
        m_run_in_subproc,
        m_logger,
        run_type,
        host_name,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2018-05-22")
        )
        download_results.download_results(parsed_args, config)
        assert m_fix_perms.call_args_list[0][0] == (
            Path("SalishSea", run_type, "22may18"),
        )
        assert m_fix_perms.call_args_list[0][1] == {
            "mode": m_file_perms(user="rwx", group="rwx", other="rx"),
            "grp_name": "allen",
        }

    @pytest.mark.parametrize(
        "run_type, host_name",
        [
            ("nowcast", "arbutus.cloud-nowcast"),
            ("nowcast-green", "arbutus.cloud-nowcast"),
            ("forecast", "arbutus.cloud-nowcast"),
            ("forecast2", "arbutus.cloud-nowcast"),
            ("hindcast", "cedar-hindcast"),
            ("nowcast-agrif", "orcinus-nowcast-agrif"),
        ],
    )
    def test_results_files_fix_perms(
        self, m_fix_perms, m_run_in_subproc, m_logger, run_type, host_name, config
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2018-05-22")
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
            ("hindcast", "cedar-hindcast"),
            ("nowcast-agrif", "orcinus-nowcast-agrif"),
        ],
    )
    def test_checklist(
        self, m_fix_perms, m_run_in_subproc, m_logger, run_type, host_name, config
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name, run_type=run_type, run_date=arrow.get("2018-05-22")
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

    def test_checklist_agrif(self, m_fix_perms, m_run_in_subproc, m_logger, config):
        parsed_args = SimpleNamespace(
            host_name="orcinus-nowcast-agrif",
            run_type="nowcast-agrif",
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
