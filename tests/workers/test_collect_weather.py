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
"""Unit tests for SalishSeaCast collect_weather worker.
"""
import logging
import os
from pathlib import Path
import textwrap
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import collect_weather


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
                
                weather:
                  download:
                    datamart dir: datamart/hrdps-west/
                    GRIB dir: forcing/atmospheric/GEM2.5/GRIB/
                    forecast duration: 48
                    file template: 'CMC_hrdps_west_{variable}_ps2.5km_{date}{forecast}_P{hour}-00.grib2'
                    grib variables:
                      - UGRD_TGL_10  # u component of wind velocity at 10m elevation
                      - VGRD_TGL_10  # v component of wind velocity at 10m elevation
                      - DSWRF_SFC_0  # accumulated downward shortwave (solar) radiation at ground level
                      - DLWRF_SFC_0  # accumulated downward longwave (thermal) radiation at ground level
                      - LHTFL_SFC_0  # upward surface latent heat flux (for VHFR FVCOM)
                      - TMP_TGL_2    # air temperature at 2m elevation
                      - SPFH_TGL_2   # specific humidity at 2m elevation
                      - RH_TGL_2     # relative humidity at 2m elevation (for VHFR FVCOM)
                      - APCP_SFC_0   # accumulated precipitation at ground level
                      - PRATE_SFC_0  # precipitation rate at ground level (for VHFR FVCOM)
                      - PRMSL_MSL_0  # atmospheric pressure at mean sea level
                      - TCDC_SFC_0   # total cloud in percent (for parametrization of radiation missing from 2007-2014 GRMLAM)
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(collect_weather, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, mock_worker):
        worker = collect_weather.main()
        assert worker.name == "collect_weather"
        assert worker.description.startswith(
            "SalishSeaCast worker that monitors a mirror of HRDPS files from the ECCC MSC datamart"
        )

    def test_add_forecast_arg(self, mock_worker):
        worker = collect_weather.main()
        assert worker.cli.parser._actions[3].dest == "forecast"
        assert worker.cli.parser._actions[3].choices == {"00", "06", "12", "18"}
        assert worker.cli.parser._actions[3].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "collect_weather" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["collect_weather"]
        assert msg_registry["checklist key"] == "weather forecast"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["collect_weather"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success 00",
            "failure 00",
            "success 06",
            "failure 06",
            "success 12",
            "failure 12",
            "success 18",
            "failure 18",
            "crash",
        ]

    def test_file_group(self, prod_config):
        assert "file group" in prod_config
        assert prod_config["file group"] == "sallen"

    def test_weather_section(self, prod_config):
        weather_download = prod_config["weather"]["download"]
        assert weather_download["datamart dir"] == "/SalishSeaCast/datamart/hrdps-west/"
        assert (
            weather_download["GRIB dir"] == "/results/forcing/atmospheric/GEM2.5/GRIB/"
        )
        assert weather_download["forecast duration"] == 48
        assert (
            weather_download["file template"]
            == "CMC_hrdps_west_{variable}_ps2.5km_{date}{forecast}_P{hour}-00.grib2"
        )
        assert weather_download["grib variables"] == [
            "UGRD_TGL_10",
            "VGRD_TGL_10",
            "DSWRF_SFC_0",
            "DLWRF_SFC_0",
            "LHTFL_SFC_0",
            "TMP_TGL_2",
            "SPFH_TGL_2",
            "RH_TGL_2",
            "APCP_SFC_0",
            "PRATE_SFC_0",
            "PRMSL_MSL_0",
            "TCDC_SFC_0",
        ]

    def test_logging_section(self, prod_config):
        loggers = prod_config["logging"]["publisher"]["loggers"]
        assert loggers["watchdog"]["qualname"] == "watchdog"
        assert loggers["watchdog"]["level"] == "WARNING"
        assert loggers["watchdog"]["formatter"] == "simple"


@pytest.mark.parametrize(
    "forecast, utcnow, forecast_date",
    (
        ("00", "2018-12-29 03:58:43", "2018-12-29"),
        ("06", "2018-12-28 09:59:43", "2018-12-28"),
        ("12", "2018-12-28 15:56:43", "2018-12-28"),
        ("18", "2018-12-28 21:54:43", "2018-12-28"),
    ),
)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(self, forecast, utcnow, forecast_date, caplog, monkeypatch):
        def mock_utcnow():
            return arrow.get(utcnow)

        monkeypatch.setattr(collect_weather.arrow, "utcnow", mock_utcnow)
        parsed_args = SimpleNamespace(forecast=forecast)
        caplog.set_level(logging.INFO)

        msg_type = collect_weather.success(parsed_args)
        assert caplog.records[0].levelname == "INFO"
        expected = f"{forecast_date} weather forecast {parsed_args.forecast} collection complete"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {forecast}"


@pytest.mark.parametrize(
    "forecast, utcnow, forecast_date",
    (
        ("00", "2018-12-29 03:58:43", "2018-12-29"),
        ("06", "2018-12-28 09:59:43", "2018-12-28"),
        ("12", "2018-12-28 15:56:43", "2018-12-28"),
        ("18", "2018-12-28 21:54:43", "2018-12-28"),
    ),
)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(self, forecast, utcnow, forecast_date, caplog, monkeypatch):
        def mock_utcnow():
            return arrow.get(utcnow)

        monkeypatch.setattr(collect_weather.arrow, "utcnow", mock_utcnow)
        parsed_args = SimpleNamespace(forecast=forecast)
        caplog.set_level(logging.CRITICAL)

        msg_type = collect_weather.failure(parsed_args)
        assert caplog.records[0].levelname == "CRITICAL"
        expected = (
            f"{forecast_date} weather forecast {parsed_args.forecast} collection failed"
        )
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {forecast}"


@pytest.mark.parametrize(
    "forecast, utcnow, forecast_date",
    (
        ("00", "2018-12-29 03:58:43", "20181229"),
        ("06", "2018-12-28 09:59:43", "20181228"),
        ("12", "2018-12-28 15:56:43", "20181228"),
        ("18", "2018-12-28 21:54:43", "20181228"),
    ),
)
@patch(
    "nowcast.workers.collect_weather._calc_expected_files",
    return_value=set(),
    autospec=True,
)
@patch("nowcast.workers.collect_weather.lib.mkdir", autospec=True)
@patch("nowcast.workers.collect_weather.watchdog.observers.Observer", autospec=True)
class TestCollectWeather:
    """Unit test for collect_weather() function.
    """

    def test_checklist(
        self,
        m_obs,
        m_mkdir,
        m_calc_exp_files,
        forecast,
        utcnow,
        forecast_date,
        config,
        caplog,
        monkeypatch,
    ):
        def mock_utcnow():
            return arrow.get(utcnow)

        monkeypatch.setattr(collect_weather.arrow, "utcnow", mock_utcnow)
        parsed_args = SimpleNamespace(forecast=forecast)
        cheklist = collect_weather.collect_weather(parsed_args, config)
        assert cheklist == {
            forecast: f"forcing/atmospheric/GEM2.5/GRIB/{forecast_date}/{forecast}"
        }


@pytest.mark.parametrize(
    "forecast, utcnow",
    (
        ("00", arrow.get("2018-12-29 03:58:43")),
        ("06", arrow.get("2018-12-28 09:59:43")),
        ("12", arrow.get("2018-12-28 15:56:43")),
        ("18", arrow.get("2018-12-28 21:54:43")),
    ),
)
class TestCalcExpectedFiles:
    """Unit tests for _calc_expected_files() function.
    """

    def test_expected_files(
        self, forecast, utcnow, config, prod_config, caplog, monkeypatch
    ):
        def mock_utcnow():
            return arrow.get(utcnow)

        monkeypatch.setattr(collect_weather.arrow, "utcnow", mock_utcnow)
        datamart_dir = Path(config["weather"]["download"]["datamart dir"])
        forecast_date = utcnow.shift(hours=-int(forecast)).format("YYYYMMDD")
        expected_files = collect_weather._calc_expected_files(
            datamart_dir, forecast, forecast_date, config
        )
        forecast_duration = prod_config["weather"]["download"]["forecast duration"]
        grib_vars = prod_config["weather"]["download"]["grib variables"]
        file_template = config["weather"]["download"]["file template"]
        expected = set()
        for hour in range(forecast_duration):
            forecast_hour = f"{hour + 1:03d}"
            var_files = {
                file_template.format(
                    variable=var,
                    date=forecast_date,
                    forecast=forecast,
                    hour=forecast_hour,
                )
                for var in grib_vars
            }
            expected.update(
                {
                    datamart_dir / forecast / f"{forecast_hour}" / var_file
                    for var_file in var_files
                }
            )
        assert expected_files == expected
        assert len(expected_files) == forecast_duration * len(grib_vars)


class TestGribFileEventHandler:
    """Unit tests for _GribFileEventHandler class.
    """

    def test_constructor(self, config):
        handler = collect_weather._GribFileEventHandler(
            expected_files=set(),
            grib_forecast_dir=Path(),
            grp_name=config["file group"],
        )
        assert handler.expected_files == set()
        assert handler.grib_forecast_dir == Path()
        assert handler.grp_name == config["file group"]

    @patch("nowcast.workers.collect_weather.lib.mkdir", autospec=True)
    @patch("nowcast.workers.collect_weather.shutil.move", autospec=True)
    def test_move_expected_file(self, m_move, m_mkdir, config, caplog):
        expected_file = Path(
            config["weather"]["download"]["datamart dir"],
            "18/043/CMC_hrdps_west_TCDC_SFC_0_ps2.5km_2018123018_P043-00.grib2",
        )
        expected_files = {expected_file}
        grib_forecast_dir = Path(
            config["weather"]["download"]["GRIB dir"], "20181230", "18"
        )
        grib_hour_dir = grib_forecast_dir / "043"
        caplog.set_level(logging.DEBUG)

        handler = collect_weather._GribFileEventHandler(
            expected_files, grib_forecast_dir, grp_name=config["file group"]
        )
        handler.on_moved(Mock(name="event", dest_path=expected_file))
        m_mkdir.assert_called_once_with(
            grib_hour_dir, collect_weather.logger, grp_name=config["file group"]
        )
        m_move.assert_called_once_with(
            os.fspath(expected_file), os.fspath(grib_hour_dir)
        )
        assert caplog.records[0].levelname == "DEBUG"
        assert caplog.messages[0] == f"moved {expected_file} to {grib_hour_dir}/"
        assert expected_file not in expected_files

    @patch("nowcast.workers.collect_weather.lib.mkdir", autospec=True)
    @patch("nowcast.workers.collect_weather.shutil.move", autospec=True)
    def test_ignore_unexpected_file(self, m_move, m_mkdir, config, caplog):
        expected_file = Path(
            config["weather"]["download"]["datamart dir"],
            "18/043/CMC_hrdps_west_TCDC_SFC_0_ps2.5km_2018123018_P043-00.grib2",
        )
        expected_files = {expected_file}
        grib_forecast_dir = Path(
            config["weather"]["download"]["GRIB dir"], "20181230", "18"
        )
        caplog.set_level(logging.DEBUG)

        handler = collect_weather._GribFileEventHandler(
            expected_files, grib_forecast_dir, grp_name=config["file group"]
        )
        handler.on_moved(Mock(name="event", dest_path="foo"))
        assert not m_mkdir.called
        assert not m_move.called
        assert not caplog.records
        assert expected_file in expected_files
