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
"""Unit tests for Salish Sea WaveWatch3 forecast worker make_ww3_wind_file
worker.
"""
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_ww3_wind_file


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                weather:
                  file template: 'ops_{:y%Ym%md%d}.nc'

                run:
                  enabled hosts:
                    arbutus.cloud:
                      forcing:
                        weather dir: /nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/

                wave forecasts:
                  run prep dir: /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/
                  wind file template: 'SoG_wind_{yyyymmdd}.nc'
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.make_ww3_wind_file.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_ww3_wind_file.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_ww3_wind_file",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_ww3_wind_file.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_ww3_wind_file.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_ww3_wind_file.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast", "forecast2"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_ww3_wind_file.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_ww3_wind_file.main()
        args, kwargs = m_worker().run.call_args
        expected = (
            make_ww3_wind_file.make_ww3_wind_file,
            make_ww3_wind_file.success,
            make_ww3_wind_file.failure,
        )
        assert args == expected


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_ww3_wind_file" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["make_ww3_wind_file"]
        assert msg_registry["checklist key"] == "WW3 wind forcing"

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
        msg_registry = prod_config["message registry"]["workers"]["make_ww3_wind_file"]
        assert msg in msg_registry

    def test_host_config_section(self, prod_config):
        host_config = prod_config["run"]["enabled hosts"]["arbutus.cloud-nowcast"]
        assert (
            host_config["forcing"]["weather dir"]
            == "/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/"
        )

    def test_weather_section(self, prod_config):
        weather = prod_config["weather"]
        assert weather["file template"] == "ops_{:y%Ym%md%d}.nc"

    def test_wave_forecasts_section(self, prod_config):
        wave_forecasts = prod_config["wave forecasts"]
        assert (
            wave_forecasts["run prep dir"]
            == "/nemoShare/MEOPAR/nowcast-sys/wwatch3-runs"
        )
        assert wave_forecasts["wind file template"] == "SoG_wind_{yyyymmdd}.nc"


@pytest.mark.parametrize("run_type", ["forecast2", "forecast"])
@patch("nowcast.workers.make_ww3_wind_file.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2017-04-07"),
        )
        msg_type = make_ww3_wind_file.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["forecast2", "forecast"])
@patch("nowcast.workers.make_ww3_wind_file.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2017-04-07"),
        )
        msg_type = make_ww3_wind_file.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {run_type}"


@patch("nowcast.workers.make_ww3_wind_file.xarray.open_mfdataset", autospec=True)
@patch("nowcast.workers.make_ww3_wind_file.xarray.open_dataset", autospec=True)
@patch("nowcast.workers.make_ww3_wind_file.logger", autospec=True)
@patch("nowcast.workers.make_ww3_wind_file._create_dataset", autospec=True)
class TestMakeWW3WindFile:
    """Unit tests for make_ww3_wind_file() function."""

    @pytest.mark.parametrize("run_type", ["forecast2", "forecast"])
    def test_checklist(
        self,
        m_create_dataset,
        m_logger,
        m_open_dataset,
        m_open_mfdataset,
        run_type,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2017-04-07"),
        )
        checklist = make_ww3_wind_file.make_ww3_wind_file(parsed_args, config)
        assert checklist == {
            run_type: "/nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/wind/"
            "SoG_wind_20170407.nc"
        }

    def test_nowcast_dataset(
        self, m_create_dataset, m_logger, m_open_dataset, m_open_mfdataset, config
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type="nowcast",
            run_date=arrow.get("2019-03-24"),
        )
        make_ww3_wind_file.make_ww3_wind_file(parsed_args, config)
        m_open_dataset.assert_called_once_with(
            Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/ops_y2019m03d24.nc")
        )
        m_open_mfdataset.assert_called_once_with(
            [Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/ops_y2019m03d24.nc")]
        )

    def test_forecast_datasets(
        self, m_create_dataset, m_logger, m_open_dataset, m_open_mfdataset, config
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type="forecast",
            run_date=arrow.get("2017-04-07"),
        )
        make_ww3_wind_file.make_ww3_wind_file(parsed_args, config)
        m_open_dataset.assert_called_once_with(
            Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/ops_y2017m04d07.nc")
        )
        m_open_mfdataset.assert_called_once_with(
            [
                Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/ops_y2017m04d07.nc"),
                Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/fcst/ops_y2017m04d08.nc"),
                Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/fcst/ops_y2017m04d09.nc"),
            ]
        )

    def test_forecast2_datasets(
        self, m_create_dataset, m_logger, m_open_dataset, m_open_mfdataset, config
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type="forecast2",
            run_date=arrow.get("2017-04-07"),
        )
        make_ww3_wind_file.make_ww3_wind_file(parsed_args, config)
        m_open_dataset.assert_called_once_with(
            Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/fcst/ops_y2017m04d07.nc")
        )
        m_open_mfdataset.assert_called_once_with(
            [
                Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/fcst/ops_y2017m04d07.nc"),
                Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/fcst/ops_y2017m04d08.nc"),
                Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/fcst/ops_y2017m04d09.nc"),
            ]
        )
