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
"""Unit tests for Salish Sea WaveWatch3 forecast worker make_ww3_current_file
worker.
"""
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, MagicMock, Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_ww3_current_file


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                run types:
                  nowcast:
                    mesh mask: mesh_mask201702.nc

                run:
                  enabled hosts:
                    arbutus.cloud:
                      run types:
                        nowcast:
                          results: /nemoShare/MEOPAR/SalishSea/nowcast/

                wave forecasts:
                  run prep dir: /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs
                  grid dir: grid/
                  current file template: 'SoG_current_{yyyymmdd}.nc'
                  NEMO file template: 'SalishSea_1h_{s_yyyymmdd}_{e_yyyymmdd}_grid_{grid}.nc'
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.make_ww3_current_file.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_ww3_current_file.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_ww3_current_file",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_ww3_current_file.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_ww3_current_file.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_ww3_current_file.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast", "forecast2"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_ww3_current_file.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_ww3_current_file.main()
        args, kwargs = m_worker().run.call_args
        expected = (
            make_ww3_current_file.make_ww3_current_file,
            make_ww3_current_file.success,
            make_ww3_current_file.failure,
        )
        assert args == expected


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_ww3_current_file" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"][
            "make_ww3_current_file"
        ]
        assert msg_registry["checklist key"] == "WW3 currents forcing"

    @pytest.mark.parametrize(
        "msg",
        (
            "success forecast2",
            "failure forecast2",
            "success forecast",
            "failure forecast",
            "success nowcast",
            "failure nowcast",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "make_ww3_current_file"
        ]
        assert msg in msg_registry

    def test_host_config_section(self, prod_config):
        host_config = prod_config["run"]["enabled hosts"]["arbutus.cloud-nowcast"]
        assert (
            host_config["run types"]["nowcast"]["results"]
            == "/nemoShare/MEOPAR/SalishSea/nowcast/"
        )

    def test_wave_forecasts_section(self, prod_config):
        wave_forecasts = prod_config["wave forecasts"]
        assert wave_forecasts["grid dir"] == "/nemoShare/MEOPAR/nowcast-sys/grid/"
        assert (
            wave_forecasts["NEMO file template"]
            == "SalishSea_1h_{s_yyyymmdd}_{e_yyyymmdd}_grid_{grid}.nc"
        )
        assert (
            wave_forecasts["run prep dir"]
            == "/nemoShare/MEOPAR/nowcast-sys/wwatch3-runs"
        )
        assert wave_forecasts["current file template"] == "SoG_current_{yyyymmdd}.nc"

    def test_run_types_section(self, prod_config):
        run_types = prod_config["run types"]
        assert run_types["nowcast"]["mesh mask"] == "mesh_mask201702.nc"


@pytest.mark.parametrize("run_type", ["forecast2", "forecast"])
@patch("nowcast.workers.make_ww3_current_file.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2017-04-07"),
        )
        msg_type = make_ww3_current_file.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["forecast2", "forecast"])
@patch("nowcast.workers.make_ww3_current_file.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2017-04-07"),
        )
        msg_type = make_ww3_current_file.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {run_type}"


@patch("nowcast.workers.make_ww3_current_file._create_dataset", autospec=True)
@patch("nowcast.workers.make_ww3_current_file.viz_tools.unstagger", autospec=True)
@patch("nowcast.workers.make_ww3_current_file.viz_tools.rotate_vel", autospec=True)
@patch("nowcast.workers.make_ww3_current_file.xarray.open_mfdataset", autospec=True)
@patch("nowcast.workers.make_ww3_current_file.xarray.open_dataset", autospec=True)
@patch("nowcast.workers.make_ww3_current_file.logger", autospec=True)
class TestMakeWW3CurrentFile:
    """Unit tests for make_ww3_current_file() function."""

    @pytest.mark.parametrize("run_type", ("forecast2", "forecast", "nowcast"))
    @patch(
        "nowcast.workers.make_ww3_current_file._calc_nowcast_datasets", autospec=True
    )
    @patch(
        "nowcast.workers.make_ww3_current_file._calc_forecast_datasets", autospec=True
    )
    @patch(
        "nowcast.workers.make_ww3_current_file._calc_forecast2_datasets", autospec=True
    )
    def test_checklist(
        self,
        m_calc_fcst2_datasets,
        m_calc_fcst_datasets,
        m_calc_ncst_datasets,
        m_logger,
        m_open_dataset,
        m_open_mfdataset,
        m_rotate_vel,
        m_unstagger,
        m_create_dataset,
        run_type,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2019-08-05"),
        )
        m_unstagger.return_value = (MagicMock(), MagicMock())
        m_rotate_vel.return_value = (MagicMock(), MagicMock())
        checklist = make_ww3_current_file.make_ww3_current_file(parsed_args, config)
        assert checklist == {
            run_type: "/nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/current/SoG_current_20190805.nc",
            "run date": "2019-08-05",
        }

    @pytest.mark.parametrize(
        "run_type, expected_call",
        [
            (
                "forecast2",
                call(
                    arrow.get("2017-04-12"),
                    Path("/nemoShare/MEOPAR/SalishSea/"),
                    "SalishSea_1h_{s_yyyymmdd}_{e_yyyymmdd}_grid_{grid}.nc",
                    Path("/nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/current"),
                ),
            ),
            (
                "forecast",
                call(
                    arrow.get("2017-04-12"),
                    Path("/nemoShare/MEOPAR/SalishSea/"),
                    "SalishSea_1h_{s_yyyymmdd}_{e_yyyymmdd}_grid_{grid}.nc",
                ),
            ),
            (
                "nowcast",
                call(
                    arrow.get("2017-04-12"),
                    Path("/nemoShare/MEOPAR/SalishSea/"),
                    "SalishSea_1h_{s_yyyymmdd}_{e_yyyymmdd}_grid_{grid}.nc",
                ),
            ),
        ],
    )
    @patch(
        "nowcast.workers.make_ww3_current_file._calc_nowcast_datasets", autospec=True
    )
    @patch(
        "nowcast.workers.make_ww3_current_file._calc_forecast_datasets", autospec=True
    )
    @patch(
        "nowcast.workers.make_ww3_current_file._calc_forecast2_datasets", autospec=True
    )
    def test_calc_datasets_call(
        self,
        m_calc_fcst2_datasets,
        m_calc_fcst_datasets,
        m_calc_ncst_datasets,
        m_logger,
        m_open_dataset,
        m_open_mfdataset,
        m_rotate_vel,
        m_unstagger,
        m_create_dataset,
        run_type,
        expected_call,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2017-04-12"),
        )
        m_unstagger.return_value = (MagicMock(), MagicMock())
        m_rotate_vel.return_value = (MagicMock(), MagicMock())
        checklist = make_ww3_current_file.make_ww3_current_file(parsed_args, config)
        func_mocks = {
            "forecast2": m_calc_fcst2_datasets,
            "forecast": m_calc_fcst_datasets,
            "nowcast": m_calc_ncst_datasets,
        }
        assert func_mocks[run_type].call_count == 1
        assert func_mocks[run_type].call_args_list[0] == expected_call

    @pytest.mark.parametrize("run_type", ["forecast2", "forecast", "nowcast"])
    @patch("nowcast.workers.make_ww3_current_file._calc_forecast_datasets")
    @patch("nowcast.workers.make_ww3_current_file._calc_forecast2_datasets")
    def test_mesh_mask_dataset(
        self,
        m_calc_fcst2_datasets,
        m_calc_fcst_datasets,
        m_logger,
        m_open_dataset,
        m_open_mfdataset,
        m_rotate_vel,
        m_unstagger,
        m_create_dataset,
        run_type,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2017-04-18"),
        )
        m_unstagger.return_value = (MagicMock(), MagicMock())
        m_rotate_vel.return_value = (MagicMock(), MagicMock())
        make_ww3_current_file.make_ww3_current_file(parsed_args, config)
        m_open_dataset.assert_called_once_with("grid/mesh_mask201702.nc")


@patch("nowcast.workers.make_ww3_current_file.logger", autospec=True)
class TestCalcNowcastDatasets:
    """Unit tests for _calc_nowcast_datasets() function."""

    def test_nowcast_datasets(self, m_logger):
        datasets = make_ww3_current_file._calc_nowcast_datasets(
            arrow.get("2019-03-25"),
            Path("/nemoShare/MEOPAR/SalishSea/"),
            "SalishSea_1h_{s_yyyymmdd}_{e_yyyymmdd}_grid_{grid}.nc",
        )
        assert datasets == {
            "u": [
                Path(
                    "/nemoShare/MEOPAR/SalishSea/nowcast/25mar19/SalishSea_1h_20190325_20190325_grid_U.nc"
                )
            ],
            "v": [
                Path(
                    "/nemoShare/MEOPAR/SalishSea/nowcast/25mar19/SalishSea_1h_20190325_20190325_grid_V.nc"
                )
            ],
        }


@patch("nowcast.workers.make_ww3_current_file.logger", autospec=True)
class TestCalcForecastDatasets:
    """Unit tests for _calc_forecast_datasets() function."""

    def test_forecast_datasets(self, m_logger):
        datasets = make_ww3_current_file._calc_forecast_datasets(
            arrow.get("2017-04-12"),
            Path("/nemoShare/MEOPAR/SalishSea/"),
            "SalishSea_1h_{s_yyyymmdd}_{e_yyyymmdd}_grid_{grid}.nc",
        )
        assert datasets == {
            "u": [
                Path(
                    "/nemoShare/MEOPAR/SalishSea/nowcast/12apr17/SalishSea_1h_20170412_20170412_grid_U.nc"
                ),
                Path(
                    "/nemoShare/MEOPAR/SalishSea/forecast/12apr17/SalishSea_1h_20170413_20170414_grid_U.nc"
                ),
            ],
            "v": [
                Path(
                    "/nemoShare/MEOPAR/SalishSea/nowcast/12apr17/SalishSea_1h_20170412_20170412_grid_V.nc"
                ),
                Path(
                    "/nemoShare/MEOPAR/SalishSea/forecast/12apr17/SalishSea_1h_20170413_20170414_grid_V.nc"
                ),
            ],
        }


@patch("nowcast.workers.make_ww3_current_file.logger", autospec=True)
@patch("nowcast.workers.make_ww3_current_file.subprocess.run", autospec=True)
class TestCalcForecast2Datasets:
    """Unit tests for _calc_forecast2_datasets() function."""

    def test_forecast2_datasets(self, m_run, m_logger):
        datasets = make_ww3_current_file._calc_forecast2_datasets(
            arrow.get("2017-04-13"),
            Path("/nemoShare/MEOPAR/SalishSea/"),
            "SalishSea_1h_{s_yyyymmdd}_{e_yyyymmdd}_grid_{grid}.nc",
            Path("/nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/current"),
        )
        assert datasets == {
            "u": [
                Path(
                    "/nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/current/SalishSea_1h_20170413_20170413_grid_U.nc"
                ),
                Path(
                    "/nemoShare/MEOPAR/SalishSea/forecast2/12apr17/SalishSea_1h_20170414_20170415_grid_U.nc"
                ),
            ],
            "v": [
                Path(
                    "/nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/current/SalishSea_1h_20170413_20170413_grid_V.nc"
                ),
                Path(
                    "/nemoShare/MEOPAR/SalishSea/forecast2/12apr17/SalishSea_1h_20170414_20170415_grid_V.nc"
                ),
            ],
        }
