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


"""Unit tests for SalishSeaCast make_surface_current_tiles worker.
"""
import logging
from pathlib import Path
import textwrap
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_surface_current_tiles


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                file group: allen

                figures:
                  grid dir: nowcast-sys/grid/
                  surface current tiles:
                    storage path: nowcast-sys/figures/surface_currents/

                results archive:
                  nowcast: results/nowcast-blue.201806/
                  nowcast-green: results/nowcast-green.201806/
                  forecast: results/forecast.201806/
                  forecast2: results/forecast2.201806/

                run types:
                  nowcast-green:
                    coordinates: coordinates_seagrid_SalishSea201702.nc
                    bathymetry: bathymetry_201702.nc
                    mesh mask: mesh_mask201702.nc
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
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(
        make_surface_current_tiles, "NowcastWorker", mock_nowcast_worker
    )


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = make_surface_current_tiles.main()

        assert worker.name == "make_surface_current_tiles"
        assert worker.description.startswith(
            "SalishSeaCast worker that produces tiles of surface current visualization"
        )

    def test_add_run_type_arg(self, mock_worker):
        worker = make_surface_current_tiles.main()

        assert worker.cli.parser._actions[3].dest == "run_type"
        assert worker.cli.parser._actions[3].choices == {
            "nowcast-green",
            "forecast",
            "forecast2",
        }
        assert worker.cli.parser._actions[3].help

    def test_add_run_date_option(self, mock_worker):
        worker = make_surface_current_tiles.main()

        assert worker.cli.parser._actions[4].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[4].type == expected
        assert worker.cli.parser._actions[4].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[4].help

    def test_add_nprocs_option(self, mock_worker, monkeypatch):
        def mock_cpu_count():
            return 12

        monkeypatch.setattr(
            make_surface_current_tiles.multiprocessing, "cpu_count", mock_cpu_count
        )

        worker = make_surface_current_tiles.main()

        assert worker.cli.parser._actions[5].dest == "nprocs"
        assert worker.cli.parser._actions[5].type == int
        assert worker.cli.parser._actions[5].default == 6
        assert worker.cli.parser._actions[5].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

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
            "success nowcast-green",
            "failure nowcast-green",
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
        assert figures["grid dir"] == "/SalishSeaCast/grid/"
        assert "surface current tiles" in figures
        tiles = figures["surface current tiles"]
        assert tiles["storage path"] == "/results/nowcast-sys/figures/surface_currents/"

    def test_results_archive_section(self, prod_config):
        assert "results archive" in prod_config
        results_archive = prod_config["results archive"]
        assert results_archive["nowcast"] == "/results/SalishSea/nowcast-blue.202111/"
        assert (
            results_archive["nowcast-green"]
            == "/results2/SalishSea/nowcast-green.202111/"
        )
        assert results_archive["forecast"] == "/results/SalishSea/forecast.202111/"
        assert results_archive["forecast2"] == "/results/SalishSea/forecast2.202111/"

    @pytest.mark.parametrize("run_type", ["nowcast-green", "forecast", "forecast2"])
    def test_run_types_section(self, run_type, prod_config):
        assert "run types" in prod_config
        run_types = prod_config["run types"]
        assert (
            run_types[run_type]["coordinates"]
            == "coordinates_seagrid_SalishSea201702.nc"
        )
        assert run_types[run_type]["bathymetry"] == "bathymetry_202108.nc"
        assert run_types[run_type]["mesh mask"] == "mesh_mask202108.nc"


@pytest.mark.parametrize("run_type", ("nowcast-green", "forecast", "forecast2"))
class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, run_type, caplog):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=(arrow.get("2018-11-29"))
        )
        caplog.set_level(logging.DEBUG)

        msg_type = make_surface_current_tiles.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected_msg = (
            f"surface current tile figures for 2018-11-29 {run_type} completed"
        )
        assert caplog.messages[0] == expected_msg
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ("nowcast-green", "forecast", "forecast2"))
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, run_type, caplog):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=(arrow.get("2018-11-29"))
        )
        caplog.set_level(logging.DEBUG)

        msg_type = make_surface_current_tiles.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected_msg = (
            f"surface current tile figures production for 2018-11-29 {run_type} failed"
        )
        assert caplog.messages[0] == expected_msg
        assert msg_type == f"failure {run_type}"


@pytest.mark.parametrize("run_type", ("nowcast-green", "forecast", "forecast2"))
class TestMakeSurfaceCurrentTiles:
    """Unit tests for make_surface_current_tiles() function."""

    def test_checklist(self, run_type, config, caplog):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=(arrow.get("2018-11-29")), nprocs=6
        )
        caplog.set_level(logging.DEBUG)

        # checklist = make_surface_current_tiles.make_surface_current_tiles(
        #     parsed_args, config
        # )
        #
        # assert caplog.records[0].levelname == "INFO"
        # expected_msg = (
        #     f"finished rendering of tiles for 2018-11-29 {run_type} "
        #     f"into nowcast-sys/figures/surface_currents/"
        # )
        # assert caplog.messages[0] == expected_msg
        #
        # expected = {
        #     "run date": "2018-11-29",
        #     "png": [],
        #     "pdf": [],
        # }
        # assert checklist == expected
