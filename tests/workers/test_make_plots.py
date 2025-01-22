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


"""Unit tests for SalishSeaCast make_plots worker.
"""
import logging
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_plots


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    return base_config


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(make_plots, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = make_plots.main()

        assert worker.name == "make_plots"
        assert worker.description.startswith(
            "SalishSeaCast worker that produces visualization images for"
        )

    def test_add_model_arg(self, mock_worker):
        worker = make_plots.main()

        assert worker.cli.parser._actions[3].dest == "model"
        assert worker.cli.parser._actions[3].choices == {"nemo", "fvcom", "wwatch3"}
        assert worker.cli.parser._actions[3].help

    def test_add_run_type_arg(self, mock_worker):
        worker = make_plots.main()

        assert worker.cli.parser._actions[4].dest == "run_type"
        assert worker.cli.parser._actions[4].choices == {
            "nowcast",
            "nowcast-green",
            "nowcast-agrif",
            "nowcast-x2",
            "nowcast-r12",
            "forecast",
            "forecast2",
            "forecast-x2",
        }
        assert worker.cli.parser._actions[4].help

    def test_add_plot_type_arg(self, mock_worker):
        worker = make_plots.main()

        assert worker.cli.parser._actions[5].dest == "plot_type"
        assert worker.cli.parser._actions[5].choices == {
            "publish",
            "research",
            "comparison",
        }
        assert worker.cli.parser._actions[5].help

    def test_add_run_date_option(self, mock_worker):
        worker = make_plots.main()
        assert worker.cli.parser._actions[6].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[6].type == expected
        assert worker.cli.parser._actions[6].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[6].help

    def test_add_test_figure_arg(self, mock_worker):
        worker = make_plots.main()

        assert worker.cli.parser._actions[7].dest == "test_figure"
        assert worker.cli.parser._actions[7].default is None
        assert worker.cli.parser._actions[7].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_plots" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["make_plots"]
        assert msg_registry["checklist key"] == "plots"

    @pytest.mark.parametrize(
        "msg",
        (
            "success nemo nowcast publish",
            "success nemo nowcast research",
            "success nemo nowcast comparison",
            "failure nemo nowcast publish",
            "failure nemo nowcast research",
            "failure nemo nowcast comparison",
            "success nemo nowcast-green research",
            "failure nemo nowcast-green research",
            "success nemo nowcast-agrif research",
            "failure nemo nowcast-agrif research",
            "success nemo forecast publish",
            "failure nemo forecast publish",
            "success nemo forecast2 publish",
            "failure nemo forecast2 publish",
            "success fvcom nowcast-x2 publish",
            "failure fvcom nowcast-x2 publish",
            "success fvcom nowcast-r12 publish",
            "failure fvcom nowcast-r12 publish",
            "success fvcom nowcast-x2 research",
            "failure fvcom nowcast-x2 research",
            "success fvcom nowcast-r12 research",
            "failure fvcom nowcast-r12 research",
            "success wwatch3 forecast publish",
            "failure wwatch3 forecast publish",
            "success wwatch3 forecast2 publish",
            "failure wwatch3 forecast2 publish",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["make_plots"]
        assert msg in msg_registry

    def test_timezone(self, prod_config):
        timezone = prod_config["figures"]["timezone"]

        assert timezone == "Canada/Pacific"

    def test_dev_results_archive(self, prod_config):
        dev_results_archive = prod_config["results archive"]["nowcast-dev"]

        assert dev_results_archive == "None"

    def test_weather_path(self, prod_config):
        weather_path = prod_config["weather"]["ops dir"]

        assert (
            weather_path == "/results/forcing/atmospheric/continental2.5/nemo_forcing/"
        )

    @pytest.mark.parametrize(
        "run_type, results_archive",
        (
            ("nowcast", "/results/SalishSea/nowcast-blue.202111/"),
            ("nowcast-green", "/results2/SalishSea/nowcast-green.202111/"),
            ("nowcast-agrif", "/results/SalishSea/nowcast-agrif.201702/"),
            ("forecast", "/results/SalishSea/forecast.202111/"),
            ("forecast2", "/results/SalishSea/forecast2.202111/"),
        ),
    )
    def test_results_archives(self, run_type, results_archive, prod_config):
        run_type_results_archive = prod_config["results archive"][run_type]

        assert run_type_results_archive == results_archive

    def test_grid_dir(self, prod_config):
        grid_dir = prod_config["figures"]["grid dir"]

        assert grid_dir == "/SalishSeaCast/grid/"

    @pytest.mark.parametrize(
        "run_type, bathymetry",
        (
            ("nowcast", "bathymetry_202108.nc"),
            ("nowcast-green", "bathymetry_202108.nc"),
            ("nowcast-agrif", "bathymetry_201702.nc"),
            ("forecast", "bathymetry_202108.nc"),
            ("forecast2", "bathymetry_202108.nc"),
        ),
    )
    def test_bathymetry(self, run_type, bathymetry, prod_config):
        run_type_bathy = prod_config["run types"][run_type]["bathymetry"]

        assert run_type_bathy == bathymetry

    @pytest.mark.parametrize(
        "run_type, mesh_mask",
        (
            ("nowcast", "mesh_mask202108.nc"),
            ("nowcast-green", "mesh_mask202108.nc"),
            ("nowcast-agrif", "mesh_mask201702.nc"),
            ("forecast", "mesh_mask202108.nc"),
            ("forecast2", "mesh_mask202108.nc"),
        ),
    )
    def test_mesh_mask(self, run_type, mesh_mask, prod_config):
        run_type_mesh_mask = prod_config["run types"][run_type]["mesh mask"]

        assert run_type_mesh_mask == mesh_mask

    def test_dev_mesh_mask(self, prod_config):
        dev_mesh_mask = prod_config["run types"]["nowcast-dev"]["mesh mask"]

        assert dev_mesh_mask == "mesh_mask201702.nc"

    def test_coastline(self, prod_config):
        coastline = prod_config["figures"]["coastline"]

        assert coastline == "/ocean/rich/more/mmapbase/bcgeo/PNW.mat"

    @pytest.mark.parametrize(
        "dataset, dataset_url",
        (
            (
                "tide stn ssh time series",
                "https://salishsea.eos.ubc.ca/erddap/griddap/ubcSSf{place}SSH10m",
            ),
            (
                "2nd narrows hadcp time series",
                "https://salishsea.eos.ubc.ca/erddap/tabledap/ubcVFPA2ndNarrowsCurrent2sV1",
            ),
            (
                "wwatch3 fields",
                "https://salishsea.eos.ubc.ca/erddap/griddap/ubcSSf2DWaveFields30mV17-02",
            ),
            (
                "3d physics fields",
                "https://salishsea.eos.ubc.ca/erddap/griddap/ubcSSg3DPhysicsFields1hV21-11",
            ),
            (
                "3d biology fields",
                "https://salishsea.eos.ubc.ca/erddap/griddap/ubcSSg3DBiologyFields1hV21-11",
            ),
            (
                "HRDPS fields",
                "https://salishsea.eos.ubc.ca/erddap/griddap/ubcSSaSurfaceAtmosphereFieldsV23-02",
            ),
        ),
    )
    def test_dataset_urls(self, dataset, dataset_url, prod_config):
        url = prod_config["figures"]["dataset URLs"][dataset]

        assert url == dataset_url

    def test_agrif_bathymetryy(self, prod_config):
        grid_dir = Path(prod_config["figures"]["grid dir"])
        ss_grid_path = (
            grid_dir / prod_config["run types"]["nowcast-agrif"]["bathymetry"]
        )
        bs_grid_path = Path(
            prod_config["run types"]["nowcast-agrif"]["sub-grid bathymetry"]
        )

        assert ss_grid_path == Path("/SalishSeaCast/grid/bathymetry_201702.nc")
        assert bs_grid_path == Path(
            "/SalishSeaCast/grid/subgrids/BaynesSound/bathymetry_201702_BS.nc"
        )

    def test_tidal_predictions(self, prod_config):
        tidal_predictions = prod_config["ssh"]["tidal predictions"]

        assert tidal_predictions == "/SalishSeaCast/tidal-predictions/"

    @pytest.mark.parametrize(
        "run_type, duration",
        (
            ("nowcast", 1),
            ("nowcast-green", 1),
            ("nowcast-agrif", 1),
            ("forecast", 1.5),
            ("forecast2", 1.25),
        ),
    )
    def test_durations(self, run_type, duration, prod_config):
        run_type_duration = prod_config["run types"][run_type]["duration"]

        assert run_type_duration == duration

    def test_test_path(self, prod_config):
        test_path = prod_config["figures"]["test path"]

        assert test_path == "/results/nowcast-sys/figures/test/"

    def test_storage_path(self, prod_config):
        storage_path = prod_config["figures"]["storage path"]

        assert storage_path == "/results/nowcast-sys/figures/"

    def test_file_group(self, prod_config):
        file_group = prod_config["file group"]

        assert file_group == "sallen"

    @pytest.mark.parametrize(
        "key, expected_path",
        (
            ("storm surge alerts thumbnail", "Website_thumbnail"),
            ("storm surge info portal path", "storm-surge/"),
        ),
    )
    def test_storm_surge_paths(self, key, expected_path, prod_config):
        path = prod_config["figures"][key]

        assert path == expected_path


@pytest.mark.parametrize(
    "model, run_type, plot_type",
    [
        ("nemo", "nowcast", "publish"),
        ("nemo", "nowcast", "research"),
        ("nemo", "nowcast", "comparison"),
        ("nemo", "nowcast-green", "research"),
        ("nemo", "nowcast-agrif", "research"),
        ("nemo", "forecast", "publish"),
        ("nemo", "forecast2", "publish"),
        ("fvcom", "nowcast-x2", "publish"),
        ("fvcom", "forecast-x2", "publish"),
        ("fvcom", "nowcast-r12", "publish"),
        ("wwatch3", "forecast", "publish"),
        ("wwatch3", "forecast2", "publish"),
    ],
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, model, run_type, plot_type, caplog):
        parsed_args = SimpleNamespace(
            model=model,
            run_type=run_type,
            plot_type=plot_type,
            run_date=arrow.get("2017-01-02"),
        )
        caplog.set_level(logging.DEBUG)

        msg_type = make_plots.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = (
            f"{parsed_args.model} {parsed_args.plot_type} plots for "
            f'{parsed_args.run_date.format("YYYY-MM-DD")} '
            f"{parsed_args.run_type} completed"
        )
        assert caplog.messages[0] == expected
        assert msg_type == f"success {model} {run_type} {plot_type}"


@pytest.mark.parametrize(
    "model, run_type, plot_type",
    [
        ("nemo", "nowcast", "publish"),
        ("nemo", "nowcast", "research"),
        ("nemo", "nowcast", "comparison"),
        ("nemo", "nowcast-green", "research"),
        ("nemo", "nowcast-agrif", "research"),
        ("nemo", "forecast", "publish"),
        ("nemo", "forecast2", "publish"),
        ("fvcom", "nowcast-x2", "publish"),
        ("fvcom", "forecast-x2", "publish"),
        ("fvcom", "nowcast-r12", "publish"),
        ("wwatch3", "forecast", "publish"),
        ("wwatch3", "forecast2", "publish"),
    ],
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, model, run_type, plot_type, caplog):
        parsed_args = SimpleNamespace(
            model=model,
            run_type=run_type,
            plot_type=plot_type,
            run_date=arrow.get("2017-01-02"),
        )
        caplog.set_level(logging.DEBUG)

        msg_type = make_plots.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = (
            f"{parsed_args.model} {parsed_args.plot_type} plots failed for "
            f'{parsed_args.run_date.format("YYYY-MM-DD")} {parsed_args.run_type}'
        )
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {model} {run_type} {plot_type}"
