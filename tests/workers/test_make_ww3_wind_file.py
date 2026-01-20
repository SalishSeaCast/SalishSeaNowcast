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


"""Unit tests for Salish Sea WaveWatch3 forecast worker make_ww3_wind_file
worker.
"""

import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_ww3_wind_file


@pytest.fixture
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(textwrap.dedent("""\
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
                """))
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(make_ww3_wind_file, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = make_ww3_wind_file.main()
        assert worker.name == "make_ww3_wind_file"
        assert worker.description.startswith(
            "Salish Sea WaveWatch3 forecast worker that produces the hourly wind forcing"
        )

    def test_add_host_name_arg(self, mock_worker):
        worker = make_ww3_wind_file.main()
        assert worker.cli.parser._actions[3].dest == "host_name"
        assert worker.cli.parser._actions[3].help

    def test_add_run_type_arg(self, mock_worker):
        worker = make_ww3_wind_file.main()
        assert worker.cli.parser._actions[4].dest == "run_type"
        assert worker.cli.parser._actions[4].choices == {
            "nowcast",
            "forecast",
            "forecast2",
        }
        assert worker.cli.parser._actions[4].help

    def test_add_run_date_option(self, mock_worker):
        worker = make_ww3_wind_file.main()
        assert worker.cli.parser._actions[5].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[5].type == expected
        assert worker.cli.parser._actions[5].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[5].help


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
        assert weather["file template"] == "hrdps_{:y%Ym%md%d}.nc"

    def test_wave_forecasts_section(self, prod_config):
        wave_forecasts = prod_config["wave forecasts"]
        assert (
            wave_forecasts["run prep dir"]
            == "/nemoShare/MEOPAR/nowcast-sys/wwatch3-runs"
        )
        assert wave_forecasts["wind file template"] == "SoG_wind_{yyyymmdd}.nc"


@pytest.mark.parametrize("run_type", ["forecast2", "forecast"])
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, run_type, caplog):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2017-04-07"),
        )
        caplog.set_level(logging.DEBUG)

        msg_type = make_ww3_wind_file.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"wwatch3 wind forcing file created on arbutus.cloud for 2017-04-07 {run_type} run"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["forecast2", "forecast"])
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, run_type, caplog):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2017-04-07"),
        )
        caplog.set_level(logging.DEBUG)

        msg_type = make_ww3_wind_file.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"wwatch3 wind forcing file creation failed on arbutus.cloud for 2017-04-07 {run_type} run"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {run_type}"


@patch("nowcast.workers.make_ww3_wind_file.xarray.open_mfdataset", autospec=True)
@patch("nowcast.workers.make_ww3_wind_file.xarray.open_dataset", autospec=True)
@patch("nowcast.workers.make_ww3_wind_file._create_dataset", autospec=True)
class TestMakeWW3WindFile:
    """Unit tests for make_ww3_wind_file() function."""

    @pytest.mark.parametrize("run_type", ["forecast2", "forecast"])
    def test_checklist(
        self,
        m_create_dataset,
        m_open_dataset,
        m_open_mfdataset,
        run_type,
        config,
        caplog,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2017-04-07"),
        )
        caplog.set_level(logging.DEBUG)

        checklist = make_ww3_wind_file.make_ww3_wind_file(parsed_args, config)

        assert checklist == {
            run_type: "/nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/wind/"
            "SoG_wind_20170407.nc"
        }

    def test_nowcast_dataset(
        self, m_create_dataset, m_open_dataset, m_open_mfdataset, config, caplog
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type="nowcast",
            run_date=arrow.get("2019-03-24"),
        )
        caplog.set_level(logging.DEBUG)

        make_ww3_wind_file.make_ww3_wind_file(parsed_args, config)

        drop_vars = {
            "LHTFL_surface",
            "PRATE_surface",
            "RH_2maboveground",
            "atmpres",
            "precip",
            "qair",
            "solar",
            "tair",
            "therm_rad",
            "u_wind",
            "v_wind",
        }
        m_open_dataset.assert_called_once_with(
            Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/ops_y2019m03d24.nc"),
            drop_variables=drop_vars,
            engine="h5netcdf",
        )
        chunks = {
            "time_counter": 24,
            "y": 230,
            "x": 190,
        }
        drop_vars = {
            "LHTFL_surface",
            "PRATE_surface",
            "RH_2maboveground",
            "atmpres",
            "precip",
            "qair",
            "solar",
            "tair",
            "therm_rad",
            "nav_lon",
            "nav_lat",
        }
        m_open_mfdataset.assert_called_once_with(
            [Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/ops_y2019m03d24.nc")],
            chunks=chunks,
            compat="override",
            coords="minimal",
            data_vars="minimal",
            drop_variables=drop_vars,
            engine="h5netcdf",
        )

    def test_forecast_datasets(
        self, m_create_dataset, m_open_dataset, m_open_mfdataset, config, caplog
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type="forecast",
            run_date=arrow.get("2017-04-07"),
        )
        caplog.set_level(logging.DEBUG)

        make_ww3_wind_file.make_ww3_wind_file(parsed_args, config)

        drop_vars = {
            "LHTFL_surface",
            "PRATE_surface",
            "RH_2maboveground",
            "atmpres",
            "precip",
            "qair",
            "solar",
            "tair",
            "therm_rad",
            "u_wind",
            "v_wind",
        }
        m_open_dataset.assert_called_once_with(
            Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/ops_y2017m04d07.nc"),
            drop_variables=drop_vars,
            engine="h5netcdf",
        )
        chunks = {
            "time_counter": 24,
            "y": 230,
            "x": 190,
        }
        drop_vars = {
            "LHTFL_surface",
            "PRATE_surface",
            "RH_2maboveground",
            "atmpres",
            "precip",
            "qair",
            "solar",
            "tair",
            "therm_rad",
            "nav_lon",
            "nav_lat",
        }
        m_open_mfdataset.assert_called_once_with(
            [
                Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/ops_y2017m04d07.nc"),
                Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/fcst/ops_y2017m04d08.nc"),
                Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/fcst/ops_y2017m04d09.nc"),
            ],
            chunks=chunks,
            compat="override",
            coords="minimal",
            data_vars="minimal",
            drop_variables=drop_vars,
            engine="h5netcdf",
        )

    def test_forecast2_datasets(
        self, m_create_dataset, m_open_dataset, m_open_mfdataset, config, caplog
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type="forecast2",
            run_date=arrow.get("2017-04-07"),
        )
        caplog.set_level(logging.DEBUG)

        make_ww3_wind_file.make_ww3_wind_file(parsed_args, config)

        drop_vars = {
            "LHTFL_surface",
            "PRATE_surface",
            "RH_2maboveground",
            "atmpres",
            "precip",
            "qair",
            "solar",
            "tair",
            "therm_rad",
            "u_wind",
            "v_wind",
        }
        m_open_dataset.assert_called_once_with(
            Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/fcst/ops_y2017m04d07.nc"),
            drop_variables=drop_vars,
            engine="h5netcdf",
        )
        chunks = {
            "time_counter": 24,
            "y": 230,
            "x": 190,
        }
        drop_vars = {
            "LHTFL_surface",
            "PRATE_surface",
            "RH_2maboveground",
            "atmpres",
            "precip",
            "qair",
            "solar",
            "tair",
            "therm_rad",
            "nav_lon",
            "nav_lat",
        }
        m_open_mfdataset.assert_called_once_with(
            [
                Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/fcst/ops_y2017m04d07.nc"),
                Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/fcst/ops_y2017m04d08.nc"),
                Path("/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/fcst/ops_y2017m04d09.nc"),
            ],
            chunks=chunks,
            compat="override",
            coords="minimal",
            data_vars="minimal",
            drop_variables=drop_vars,
            engine="h5netcdf",
        )
