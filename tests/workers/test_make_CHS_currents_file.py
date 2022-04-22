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

# SPDX-License-Identifier: Apache-2.0


"""Unit tests for SalishSeaCast make_CHS_currents_file worker.
"""
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_CHS_currents_file


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                file group: allen

                run types:
                  nowcast:
                    mesh mask: mesh_mask201702.nc
                  forecast:
                    mesh mask: mesh_mask201702.nc
                  forecast2:
                    mesh mask: mesh_mask201702.nc

                results archive:
                  nowcast: nowcast-blue/
                  forecast: forecast/
                  forecast2: forecast2/

                figures:
                  grid dir:
                    nowcast-sys/grid/
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.make_CHS_currents_file.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_CHS_currents_file.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_CHS_currents_file",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_CHS_currents_file.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_CHS_currents_file.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast", "forecast2"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_CHS_currents_file.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_CHS_currents_file.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_CHS_currents_file.make_CHS_currents_file,
            make_CHS_currents_file.success,
            make_CHS_currents_file.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_CHS_currents_file" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"][
            "make_CHS_currents_file"
        ]
        assert msg_registry["checklist key"] == "CHS currents file"

    @pytest.mark.parametrize(
        "msg",
        (
            "success nowcast",
            "failure nowcast",
            "success forecast",
            "failure forecast",
            "success forecast2",
            "failure forecast2",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "make_CHS_currents_file"
        ]
        assert msg in msg_registry

    def test_figures_section(self, prod_config):
        figures = prod_config["figures"]
        assert figures["grid dir"] == "/SalishSeaCast/grid/"

    def test_run_types_section(self, prod_config):
        run_types = prod_config["run types"]
        assert run_types["nowcast"]["mesh mask"] == "mesh_mask201702.nc"
        assert run_types["forecast"]["mesh mask"] == "mesh_mask201702.nc"
        assert run_types["forecast2"]["mesh mask"] == "mesh_mask201702.nc"

    def test_results_archive_section(self, prod_config):
        results_archive = prod_config["results archive"]
        assert results_archive["nowcast"] == "/results/SalishSea/nowcast-blue.201905/"
        assert results_archive["forecast"] == "/results/SalishSea/forecast.201905/"
        assert results_archive["forecast2"] == "/results/SalishSea/forecast2.201905/"

    def test_file_group(self, prod_config):
        assert prod_config["file group"] == "sallen"


@pytest.mark.parametrize("run_type", ["nowcast", "forecast", "forecast2"])
@patch("nowcast.workers.make_CHS_currents_file.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2018-09-01")
        )
        msg_type = make_CHS_currents_file.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["nowcast", "forecast", "forecast2"])
@patch("nowcast.workers.make_CHS_currents_file.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2018-09-01")
        )
        msg_type = make_CHS_currents_file.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {run_type}"


@patch(
    "nowcast.workers.make_CHS_currents_file._read_avg_unstagger_rotate",
    return_value=("urot5", "vrot5", "urot10", "vrot10"),
    autospec=True,
)
@patch(
    "nowcast.workers.make_CHS_currents_file._write_netcdf",
    spec=make_CHS_currents_file._write_netcdf,
)
@patch("nowcast.workers.make_CHS_currents_file.lib.fix_perms", autospec=True)
class TestMakeCHSCurrentsFile:
    """Unit tests for make_CHS_currents_function."""

    @pytest.mark.parametrize("run_type", ["nowcast", "forecast", "forecast2"])
    def test_checklist(self, m_fix_perms, m_write_ncdf, m_read_aur, run_type, config):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2018-09-01")
        )
        checklist = make_CHS_currents_file.make_CHS_currents_file(parsed_args, config)
        expected = {run_type: {"filename": m_write_ncdf(), "run date": "2018-09-01"}}
        assert checklist == expected

    @pytest.mark.parametrize(
        "run_type, results_archive, ufile, vfile",
        [
            (
                "nowcast",
                "nowcast-blue",
                "SalishSea_1h_20180901_20180901_grid_U.nc",
                "SalishSea_1h_20180901_20180901_grid_V.nc",
            ),
            (
                "forecast",
                "forecast",
                "SalishSea_1h_20180902_20180903_grid_U.nc",
                "SalishSea_1h_20180902_20180903_grid_V.nc",
            ),
            (
                "forecast2",
                "forecast2",
                "SalishSea_1h_20180903_20180904_grid_U.nc",
                "SalishSea_1h_20180903_20180904_grid_V.nc",
            ),
        ],
    )
    def test_read_avg_unstagger_rotatehecklist(
        self,
        m_fix_perms,
        m_write_ncdf,
        m_read_aur,
        run_type,
        results_archive,
        ufile,
        vfile,
        config,
    ):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2018-09-01")
        )
        make_CHS_currents_file.make_CHS_currents_file(parsed_args, config)
        m_read_aur.assert_called_once_with(
            Path("nowcast-sys/grid/mesh_mask201702.nc"),
            Path(results_archive) / "01sep18",
            ufile,
            vfile,
            run_type,
        )
