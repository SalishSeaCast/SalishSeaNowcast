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
"""Unit tests for SalishSeaCast make_surface_current_tiles worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_surface_current_tiles


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
file group: allen
            
figures:
  grid dir: nowcast-sys/grid/
  surface current tiles:
    storage path: nowcast-sys/figures/surface_currents/

results archive:
  nowcast: results/nowcast-blue.201806/
  forecast: results/forecast.201806/
  forecast2: results/forecast2.201806/
  
run types:
  forecast:
    coordinates: coordinates_seagrid_SalishSea201702.nc
    bathymetry: bathymetry_201702.nc
    mesh mask: mesh_mask201702.nc
  forecast2:
    coordinates: coordinates_seagrid_SalishSea201702.nc
    bathymetry: bathymetry_201702.nc
    mesh mask: mesh_mask201702.nc
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.make_surface_current_tiles.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_surface_current_tiles.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_surface_current_tiles",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_surface_current_tiles.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_surface_current_tiles.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"forecast", "forecast2"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_surface_current_tiles.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    @patch(
        "nowcast.workers.make_surface_current_tiles.multiprocessing.cpu_count",
        return_value=12,
        autospec=True,
    )
    def test_add_nprocs_arg(self, m_cpu_count, m_worker):
        m_worker().cli = Mock(name="cli")
        make_surface_current_tiles.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("--nprocs",)
        assert kwargs["type"] == int
        assert kwargs["default"] == 6
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_surface_current_tiles.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_surface_current_tiles.make_surface_current_tiles,
            make_surface_current_tiles.success,
            make_surface_current_tiles.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert (
            "make_surface_current_tiles" in prod_config["message registry"]["workers"]
        )
        msg_registry = prod_config["message registry"]["workers"][
            "make_surface_current_tiles"
        ]
        assert msg_registry["checklist key"] == "surface current tiles"

    @pytest.mark.parametrize(
        "msg",
        (
            "success forecast",
            "failure forecast",
            "success forecast2",
            "failure forecast2",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "make_surface_current_tiles"
        ]
        assert msg in msg_registry

    def test_file_group(self, prod_config):
        assert "file group" in prod_config
        assert prod_config["file group"] == "sallen"

    def test_figures_section(self, prod_config):
        assert "figures" in prod_config
        figures = prod_config["figures"]
        assert figures["grid dir"] == "/results/nowcast-sys/grid/"
        assert "surface current tiles" in figures
        tiles = figures["surface current tiles"]
        assert tiles["storage path"] == "/results/nowcast-sys/figures/surface_currents/"

    def test_results_archive_section(self, prod_config):
        assert "results archive" in prod_config
        results_archive = prod_config["results archive"]
        assert results_archive["nowcast"] == "/results/SalishSea/nowcast-blue.201806/"
        assert results_archive["forecast"] == "/results/SalishSea/forecast.201806/"
        assert results_archive["forecast2"] == "/results/SalishSea/forecast2.201806/"

    @pytest.mark.parametrize("run_type", ["forecast", "forecast2"])
    def test_run_types_section(self, run_type, prod_config):
        assert "run types" in prod_config
        run_types = prod_config["run types"]
        assert (
            run_types[run_type]["coordinates"]
            == "coordinates_seagrid_SalishSea201702.nc"
        )
        assert run_types[run_type]["bathymetry"] == "bathymetry_201702.nc"
        assert run_types[run_type]["mesh mask"] == "mesh_mask201702.nc"


@pytest.mark.parametrize("run_type", ["forecast", "forecast2"])
@patch("nowcast.workers.make_surface_current_tiles.logger", autospec=True)
class TestSuccess:
    """Unit test for success() function.
    """

    def test_success(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=(arrow.get("2018-11-29"))
        )
        msg_type = make_surface_current_tiles.success(parsed_args)
        m_logger.info.assert_called_once_with(
            f"surface current tile figures for 2018-11-29 {run_type} completed"
        )
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["forecast", "forecast2"])
@patch("nowcast.workers.make_surface_current_tiles.logger", autospec=True)
class TestFailure:
    """Unit test for failure() function.
    """

    def test_failure_log_critical(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=(arrow.get("2018-11-29"))
        )
        msg_type = make_surface_current_tiles.failure(parsed_args)
        m_logger.critical.assert_called_once_with(
            f"surface current tile figures production for 2018-11-29 {run_type} failed"
        )
        assert msg_type == f"failure {run_type}"


@pytest.mark.parametrize("run_type", ["forecast", "forecast2"])
@patch("nowcast.workers.make_surface_current_tiles.logger", autospec=True)
class TestMakeSurfaceCurrentTiles:
    """Unit tests for make_surface_current_tiles() function.
    """

    def test_checklist(self, m_logger, run_type, config):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=(arrow.get("2018-11-29")), nprocs=6
        )
        # checklist = make_surface_current_tiles.make_surface_current_tiles(
        #     parsed_args, config
        # )
        expected = {}
        # assert checklist == expected
