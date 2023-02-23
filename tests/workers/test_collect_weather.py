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


"""Unit tests for SalishSeaCast collect_weather worker.
"""
import grp
import logging
import os
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import attr
import nemo_nowcast
import pytest

from nowcast.workers import collect_weather


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                file group: allen

                weather:
                  download:
                    2.5 km:
                      datamart dir: datamart/hrdps-continental/
                      GRIB dir: forcing/atmospheric/continental2.5/GRIB/
                      forecast duration: 48
                      file template: "{date}T{forecast}Z_MSC_HRDPS_{variable}_RLatLon0.0225_PT{hour}H.grib2"
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
                    1 km:
                      datamart dir: datamart/hrdps-west/1km
                      GRIB dir: forcing/atmospheric/GEM1.0/GRIB/
                      forecast duration: 36
                      file template: 'CMC_hrdps_west_{variable}_rotated_latlon0.009x0.009_{date}T{forecast}Z_P{hour}-00.grib2'
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
    """Unit tests for main() function."""

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

    def test_add_resolution_arg(self, mock_worker):
        worker = collect_weather.main()
        assert worker.cli.parser._actions[4].dest == "resolution"
        assert worker.cli.parser._actions[4].choices == {"1km", "2.5km"}
        assert worker.cli.parser._actions[4].default == "2.5km"
        assert worker.cli.parser._actions[4].help

    def test_add_backfill_option(self, mock_worker):
        worker = collect_weather.main()
        assert worker.cli.parser._actions[5].dest == "backfill"
        assert worker.cli.parser._actions[5].default is False
        assert worker.cli.parser._actions[5].help

    def test_add_backfill_date_option(self, mock_worker):
        worker = collect_weather.main()
        assert worker.cli.parser._actions[6].dest == "backfill_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[6].type == expected
        assert worker.cli.parser._actions[6].default == arrow.now().floor("day").shift(
            days=-1
        )
        assert worker.cli.parser._actions[6].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "collect_weather" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["collect_weather"]
        assert msg_registry["checklist key"] == "weather forecast"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["collect_weather"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success 2.5km 00",
            "failure 2.5km 00",
            "success 2.5km 06",
            "failure 2.5km 06",
            "success 2.5km 12",
            "failure 2.5km 12",
            "success 2.5km 18",
            "failure 2.5km 18",
            "success 1km 00",
            "failure 1km 00",
            "success 1km 12",
            "failure 1km 12",
            "crash",
        ]

    def test_file_group(self, prod_config):
        assert "file group" in prod_config
        assert prod_config["file group"] == "sallen"

    def test_weather_download_2_5_km_section(self, prod_config):
        weather_download = prod_config["weather"]["download"]["2.5 km"]
        assert (
            weather_download["datamart dir"]
            == "/SalishSeaCast/datamart/hrdps-continental/"
        )
        assert (
            weather_download["GRIB dir"]
            == "/results/forcing/atmospheric/continental2.5/GRIB/"
        )
        assert weather_download["forecast duration"] == 48
        assert (
            weather_download["file template"]
            == "{date}T{forecast}Z_MSC_HRDPS_{variable}_RLatLon0.0225_PT{hour}H.grib2"
        )
        assert weather_download["grib variables"] == [
            "UGRD_AGL-10m",
            "VGRD_AGL-10m",
            "DSWRF_Sfc",
            "DLWRF_Sfc",
            "LHTFL_Sfc",
            "TMP_AGL-2m",
            "SPFH_AGL-2m",
            "RH_AGL-2m",
            "APCP_Sfc",
            "PRATE_Sfc",
            "PRMSL_MSL",
            "TCDC_Sfc",
        ]

    def test_weather_download_1_km_section(self, prod_config):
        weather_download = prod_config["weather"]["download"]["1 km"]
        assert (
            weather_download["datamart dir"]
            == "/SalishSeaCast/datamart/hrdps-west/1km/"
        )
        assert (
            weather_download["GRIB dir"] == "/results/forcing/atmospheric/GEM1.0/GRIB/"
        )
        assert weather_download["forecast duration"] == 36
        assert (
            weather_download["file template"]
            == "CMC_hrdps_west_{variable}_rotated_latlon0.009x0.009_{date}T{forecast}Z_P{hour}-00.grib2"
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
        ]

    def test_logging_section(self, prod_config):
        loggers = prod_config["logging"]["publisher"]["loggers"]
        assert loggers["watchdog"]["qualname"] == "watchdog"
        assert loggers["watchdog"]["level"] == "WARNING"
        assert loggers["watchdog"]["formatter"] == "simple"


@pytest.mark.parametrize(
    "forecast, resolution, utcnow, forecast_date",
    (
        ("00", "2.5km", "2018-12-29 03:58:43", "2018-12-29"),
        ("06", "2.5km", "2018-12-28 09:59:43", "2018-12-28"),
        ("12", "2.5km", "2018-12-28 15:56:43", "2018-12-28"),
        ("18", "2.5km", "2018-12-28 21:54:43", "2018-12-28"),
        ("00", "1km", "2020-02-20 03:58:43", "2020-02-20"),
        ("12", "1km", "2020-02-20 15:56:43", "2020-02-20"),
    ),
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(
        self, forecast, resolution, utcnow, forecast_date, caplog, monkeypatch
    ):
        def mock_utcnow():
            return arrow.get(utcnow)

        monkeypatch.setattr(collect_weather.arrow, "utcnow", mock_utcnow)
        parsed_args = SimpleNamespace(forecast=forecast, resolution=resolution)
        caplog.set_level(logging.DEBUG)

        msg_type = collect_weather.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"{forecast_date} {resolution} weather forecast {forecast} collection complete"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {resolution} {forecast}"


@pytest.mark.parametrize(
    "forecast, resolution, utcnow, forecast_date",
    (
        ("00", "2.5km", "2018-12-29 03:58:43", "2018-12-29"),
        ("06", "2.5km", "2018-12-28 09:59:43", "2018-12-28"),
        ("12", "2.5km", "2018-12-28 15:56:43", "2018-12-28"),
        ("18", "2.5km", "2018-12-28 21:54:43", "2018-12-28"),
        ("00", "1km", "2020-02-10 03:58:43", "2020-02-10"),
        ("12", "1km", "2020-02-10 15:56:43", "2020-02-10"),
    ),
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(
        self, forecast, resolution, utcnow, forecast_date, caplog, monkeypatch
    ):
        def mock_utcnow():
            return arrow.get(utcnow)

        monkeypatch.setattr(collect_weather.arrow, "utcnow", mock_utcnow)
        parsed_args = SimpleNamespace(forecast=forecast, resolution=resolution)
        caplog.set_level(logging.DEBUG)

        msg_type = collect_weather.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"{forecast_date} {resolution} weather forecast {forecast} collection failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {resolution} {forecast}"


class TestCollectWeather:
    """Unit tests for collect_weather() function."""

    @staticmethod
    @pytest.fixture
    def mock_calc_expected_files(monkeypatch):
        def mock_calc_expected_files(*args):
            return set()

        monkeypatch.setattr(
            collect_weather, "_calc_expected_files", mock_calc_expected_files
        )

    @pytest.mark.parametrize(
        "forecast, resolution",
        (
            ("00", "2.5km"),
            ("06", "2.5km"),
            ("12", "2.5km"),
            ("18", "2.5km"),
            ("00", "1km"),
            ("12", "1km"),
        ),
    )
    def test_checklist_backfill(
        self,
        forecast,
        resolution,
        mock_calc_expected_files,
        config,
        caplog,
        tmp_path,
        monkeypatch,
    ):
        resolution_key = resolution.replace("km", " km")
        grib_dir = tmp_path / config["weather"]["download"][resolution_key]["GRIB dir"]
        grib_dir.mkdir(parents=True)
        monkeypatch.setitem(
            config["weather"]["download"][resolution_key], "GRIB dir", grib_dir
        )
        grp_name = grp.getgrgid(os.getgid()).gr_name
        monkeypatch.setitem(config, "file group", grp_name)
        parsed_args = SimpleNamespace(
            forecast=forecast,
            resolution=resolution,
            backfill=True,
            backfill_date=arrow.get("2020-05-04"),
        )
        caplog.set_level(logging.DEBUG)

        checklist = collect_weather.collect_weather(parsed_args, config)

        assert caplog.records[0].levelname == "DEBUG"
        assert caplog.messages[0] == f"created {grib_dir/'20200504'}/"
        assert caplog.records[1].levelname == "DEBUG"
        assert caplog.messages[1] == f"created {grib_dir/'20200504'}/{forecast}/"
        assert caplog.records[2].levelname == "INFO"
        datamart_dir = Path(
            config["weather"]["download"][resolution_key]["datamart dir"]
        )
        expected = f"starting to move 2020-05-04 files from {datamart_dir/forecast}/"
        assert caplog.messages[2] == expected
        assert caplog.records[3].levelname == "INFO"
        expected = f"finished collecting files from {datamart_dir/forecast}/ to {grib_dir}/20200504/{forecast}/"
        assert caplog.messages[3] == expected
        expected = {f"{forecast} {resolution}": f"{grib_dir}/20200504/{forecast}"}
        assert checklist == expected

    @pytest.mark.parametrize(
        "forecast, resolution, utcnow, forecast_date",
        (
            ("00", "2.5km", "2018-12-29 03:58:43", "20181229"),
            ("06", "2.5km", "2018-12-28 09:59:43", "20181228"),
            ("12", "2.5km", "2018-12-28 15:56:43", "20181228"),
            ("18", "2.5km", "2018-12-28 21:54:43", "20181228"),
            ("00", "1km", "2020-02-10 03:58:43", "20200210"),
            ("12", "1km", "2020-02-10 15:56:43", "20200210"),
        ),
    )
    def test_checklist_observer(
        self,
        forecast,
        resolution,
        utcnow,
        forecast_date,
        mock_calc_expected_files,
        config,
        caplog,
        tmp_path,
        monkeypatch,
    ):
        def mock_utcnow():
            return arrow.get(utcnow)

        monkeypatch.setattr(collect_weather.arrow, "utcnow", mock_utcnow)

        class MockObserver:
            def schedule(self, event_handler, path, recursive):
                pass

            def start(self):
                pass

        monkeypatch.setattr(
            collect_weather.watchdog.observers, "Observer", MockObserver
        )

        resolution_key = resolution.replace("km", " km")
        grib_dir = tmp_path / config["weather"]["download"][resolution_key]["GRIB dir"]
        grib_dir.mkdir(parents=True)
        monkeypatch.setitem(
            config["weather"]["download"][resolution_key], "GRIB dir", grib_dir
        )
        grp_name = grp.getgrgid(os.getgid()).gr_name
        monkeypatch.setitem(config, "file group", grp_name)
        parsed_args = SimpleNamespace(
            forecast=forecast, resolution=resolution, backfill=False
        )
        caplog.set_level(logging.DEBUG)

        checklist = collect_weather.collect_weather(parsed_args, config)

        assert caplog.records[2].levelname == "INFO"
        datamart_dir = Path(
            config["weather"]["download"][resolution_key]["datamart dir"]
        )
        expected = f"starting to watch for files in {datamart_dir/forecast}/"
        assert caplog.messages[2] == expected
        expected = {
            f"{forecast} {resolution}": f"{grib_dir}/{forecast_date}/{forecast}"
        }
        assert checklist == expected


@pytest.mark.parametrize(
    "forecast, resolution, utcnow",
    (
        ("00", "2.5 km", arrow.get("2018-12-29 03:58:43")),
        ("06", "2.5 km", arrow.get("2018-12-28 09:59:43")),
        ("12", "2.5 km", arrow.get("2018-12-28 15:56:43")),
        ("18", "2.5 km", arrow.get("2018-12-28 21:54:43")),
        ("00", "1 km", arrow.get("2020-02-10 03:58:43")),
        ("12", "1 km", arrow.get("2020-02-10 15:56:43")),
    ),
)
class TestCalcExpectedFiles:
    """Unit tests for _calc_expected_files() function."""

    def test_expected_files(
        self, forecast, resolution, utcnow, config, prod_config, caplog, monkeypatch
    ):
        def mock_utcnow():
            return arrow.get(utcnow)

        monkeypatch.setattr(collect_weather.arrow, "utcnow", mock_utcnow)
        datamart_dir = Path(config["weather"]["download"][resolution]["datamart dir"])
        forecast_date = utcnow.shift(hours=-int(forecast)).format("YYYYMMDD")
        caplog.set_level(logging.DEBUG)

        expected_files = collect_weather._calc_expected_files(
            datamart_dir, forecast, forecast_date, resolution, config
        )

        assert caplog.records[0].levelname == "DEBUG"
        expected = f"calculated set of expected file paths for {resolution} {forecast_date}/{forecast}"
        assert caplog.messages[0] == expected
        forecast_duration = config["weather"]["download"][resolution][
            "forecast duration"
        ]
        grib_vars = config["weather"]["download"][resolution]["grib variables"]
        file_template = config["weather"]["download"][resolution]["file template"]
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


@pytest.mark.parametrize(
    "forecast, resolution",
    (
        ("00", "2.5 km"),
        ("06", "2.5 km"),
        ("12", "2.5 km"),
        ("18", "2.5 km"),
        ("00", "1 km"),
        ("12", "1 km"),
    ),
)
class TestMoveFile:
    """Unit test for _move_file() function."""

    def test_move_file(
        self, forecast, resolution, config, caplog, tmp_path, monkeypatch
    ):
        grib_dir = tmp_path / config["weather"]["download"][resolution]["GRIB dir"]
        grib_dir.mkdir(parents=True)
        monkeypatch.setitem(
            config["weather"]["download"][resolution], "GRIB dir", grib_dir
        )
        grp_name = grp.getgrgid(os.getgid()).gr_name
        monkeypatch.setitem(config, "file group", grp_name)
        datamart_dir = (
            tmp_path / config["weather"]["download"][resolution]["datamart dir"]
        )
        caplog.set_level(logging.DEBUG)

        file_template = config["weather"]["download"][resolution]["file template"]
        var_file = file_template.format(
            variable="UGRD_TGL_10", date="20200505", forecast=forecast, hour="043"
        )
        (datamart_dir / forecast / "043").mkdir(parents=True)
        expected_file = datamart_dir / forecast / "043" / var_file
        expected_file.write_bytes(b"")
        grib_forecast_dir = grib_dir / "20200505" / forecast
        grib_forecast_dir.mkdir(parents=True)
        collect_weather._move_file(expected_file, grib_forecast_dir, grp_name)

        assert (grib_forecast_dir / "043" / var_file).exists()
        assert not expected_file.exists()
        assert caplog.records[0].levelname == "DEBUG"
        assert (
            caplog.messages[0] == f"moved {expected_file} to {grib_forecast_dir/'043'}/"
        )


@pytest.mark.parametrize("resolution", ("2.5 km", "1 km"))
class TestGribFileEventHandler:
    """Unit tests for _GribFileEventHandler class."""

    def test_constructor(self, resolution, config):
        handler = collect_weather._GribFileEventHandler(
            expected_files=set(),
            grib_forecast_dir=Path(),
            grp_name=config["file group"],
        )
        assert handler.expected_files == set()
        assert handler.grib_forecast_dir == Path()
        assert handler.grp_name == config["file group"]

    def test_move_expected_file(
        self, resolution, config, caplog, tmp_path, monkeypatch
    ):
        @attr.s
        class MockEvent:
            dest_path = attr.ib()

        grib_dir = tmp_path / config["weather"]["download"][resolution]["GRIB dir"]
        grib_dir.mkdir(parents=True)
        monkeypatch.setitem(
            config["weather"]["download"][resolution], "GRIB dir", grib_dir
        )
        grp_name = grp.getgrgid(os.getgid()).gr_name
        monkeypatch.setitem(config, "file group", grp_name)
        datamart_dir = (
            tmp_path / config["weather"]["download"][resolution]["datamart dir"]
        )
        (datamart_dir / "18" / "043").mkdir(parents=True)
        expected_file = (
            datamart_dir
            / "18"
            / "043"
            / "CMC_hrdps_west_TCDC_SFC_0_ps2.5km_2018123018_P043-00.grib2"
        )
        expected_file.write_bytes(b"")
        expected_files = {expected_file}
        grib_forecast_dir = grib_dir / "20181230" / "18"
        grib_forecast_dir.mkdir(parents=True)
        grib_hour_dir = grib_forecast_dir / "043"
        caplog.set_level(logging.DEBUG)

        handler = collect_weather._GribFileEventHandler(
            expected_files, grib_forecast_dir, grp_name=config["file group"]
        )
        handler.on_moved(MockEvent(dest_path=expected_file))

        assert (
            grib_forecast_dir
            / "043"
            / "CMC_hrdps_west_TCDC_SFC_0_ps2.5km_2018123018_P043-00.grib2"
        ).exists()
        assert not expected_file.exists()
        assert caplog.records[0].levelname == "DEBUG"
        assert caplog.messages[0] == f"moved {expected_file} to {grib_hour_dir}/"
        assert expected_file not in expected_files

    def test_ignore_unexpected_file(
        self, resolution, config, caplog, tmp_path, monkeypatch
    ):
        @attr.s
        class MockEvent:
            dest_path = attr.ib()

        grib_dir = tmp_path / config["weather"]["download"][resolution]["GRIB dir"]
        grib_dir.mkdir(parents=True)
        monkeypatch.setitem(
            config["weather"]["download"][resolution], "GRIB dir", grib_dir
        )
        grp_name = grp.getgrgid(os.getgid()).gr_name
        monkeypatch.setitem(config, "file group", grp_name)
        datamart_dir = (
            tmp_path / config["weather"]["download"][resolution]["datamart dir"]
        )
        (datamart_dir / "18" / "043").mkdir(parents=True)
        expected_file = (
            datamart_dir
            / "18"
            / "043"
            / "CMC_hrdps_west_TCDC_SFC_0_ps2.5km_2018123018_P043-00.grib2"
        )
        expected_file.write_bytes(b"")
        expected_files = {expected_file}
        grib_forecast_dir = grib_dir / "20181230" / "18"
        grib_forecast_dir.mkdir(parents=True)
        grib_hour_dir = grib_forecast_dir / "043"
        caplog.set_level(logging.DEBUG)

        handler = collect_weather._GribFileEventHandler(
            expected_files, grib_forecast_dir, grp_name=config["file group"]
        )
        handler.on_moved(MockEvent(dest_path="foo"))

        assert not caplog.records
        assert expected_file in expected_files
