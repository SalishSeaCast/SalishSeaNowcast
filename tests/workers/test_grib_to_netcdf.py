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


"""Unit tests for SalishSeaCast grib_to_netcdf worker.
"""
import logging
import os
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest
from nemo_nowcast import WorkerError

from nowcast.workers import grib_to_netcdf


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                weather:
                  download:
                    2.5 km:
                      GRIB dir: forcing/atmospheric/continental2.5/GRIB/
                      grib variables:
                        - UGRD_AGL-10m  # u component of wind velocity at 10m elevation
                        - VGRD_AGL-10m  # v component of wind velocity at 10m elevation
                        - DSWRF_Sfc     # accumulated downward shortwave (solar) radiation at ground level
                        - DLWRF_Sfc     # accumulated downward longwave (thermal) radiation at ground level
                        - LHTFL_Sfc     # upward surface latent heat flux (for VHFR FVCOM)
                        - TMP_AGL-2m    # air temperature at 2m elevation
                        - SPFH_AGL-2m   # specific humidity at 2m elevation
                        - RH_AGL-2m     # relative humidity at 2m elevation (for VHFR FVCOM)
                        - APCP_Sfc      # accumulated precipitation at ground level
                        - PRATE_Sfc     # precipitation rate at ground level (for VHFR FVCOM)
                        - PRMSL_MSL     # atmospheric pressure at mean sea level

                  grid desc: rot-ll:245.305142:-36.088520:0.000000 345.178780:2540:0.022500 -12.302501:1290:0.022500
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(grib_to_netcdf, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = grib_to_netcdf.main()
        assert worker.name == "grib_to_netcdf"
        assert worker.description.startswith(
            "SalishSeaCast worker that generates weather forcing file from GRIB2 forecast files."
        )

    def test_add_run_type_arg(self, mock_worker):
        worker = grib_to_netcdf.main()
        assert worker.cli.parser._actions[3].dest == "run_type"
        assert worker.cli.parser._actions[3].choices == {"nowcast+", "forecast2"}
        assert worker.cli.parser._actions[3].help

    def test_add_run_date_option(self, mock_worker):
        worker = grib_to_netcdf.main()
        assert worker.cli.parser._actions[4].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[4].type == expected
        assert worker.cli.parser._actions[4].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[4].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "grib_to_netcdf" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["grib_to_netcdf"]
        assert msg_registry["checklist key"] == "weather forcing"

    @pytest.mark.parametrize(
        "msg",
        (
            "success nowcast+",
            "failure nowcast+",
            "success forecast2",
            "failure forecast2",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["grib_to_netcdf"]
        assert msg in msg_registry

    def test_file_group_item(self, prod_config):
        assert "file group" in prod_config

    def test_weather_section(self, prod_config):
        weather = prod_config["weather"]
        assert (
            weather["grid desc"]
            == "rot-ll:245.305142:-36.088520:0.000000 345.178780:2540:0.022500 -12.302501:1290:0.022500"
        )
        assert weather["ops dir"] == "/results/forcing/atmospheric/GEM2.5/operational/"
        assert weather["file template"] == "ops_{:y%Ym%md%d}.nc"
        assert (
            weather["monitoring image"]
            == "/results/nowcast-sys/figures/monitoring/wg.png"
        )

    def test_weather_download_2_5_km_section(self, prod_config):
        weather_download = prod_config["weather"]["download"]["2.5 km"]
        assert (
            weather_download["GRIB dir"]
            == "/results/forcing/atmospheric/continental2.5/GRIB/"
        )


@pytest.mark.parametrize("run_type", ("nowcast+", "forecast2"))
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, run_type, caplog):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2023-02-26")
        )
        caplog.set_level(logging.DEBUG)

        msg_type = grib_to_netcdf.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"2023-02-26 NEMO-atmos forcing file for {run_type} created"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ("nowcast+", "forecast2"))
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, run_type, caplog):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2023-02-26")
        )
        caplog.set_level(logging.DEBUG)

        msg_type = grib_to_netcdf.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"2023-02-26 NEMO-atmos forcing file creation for {run_type} failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {run_type}"


class TestGribToNetcdf:
    """Unit test for grib_to_netcdf() function."""

    pass


class TestDefineForecastSegmentsNowcast:
    """Unit tests for _define_forecast_segments_nowcast() function."""

    def test_log_messages(self, caplog):
        run_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        grib_to_netcdf._define_forecast_segments_nowcast(run_date)

        assert caplog.records[0].levelname == "DEBUG"
        expected = (
            f"forecast sections: "
            f"{run_date.shift(days=-1).format('YYYYMMDD')}/18 "
            f"{run_date.format('YYYYMMDD')}/00 "
            f"{run_date.format('YYYYMMDD')}/12"
        )
        assert caplog.messages[0] == expected
        assert caplog.records[1].levelname == "DEBUG"
        expected = f"tomorrow forecast section: {run_date.format('YYYYMMDD')}/12"
        assert caplog.messages[1] == expected
        assert caplog.records[2].levelname == "DEBUG"
        expected = f"next day forecast section: {run_date.format('YYYYMMDD')}/12"
        assert caplog.messages[2] == expected

    def test_fcst_section_hrs_list(self, caplog):
        run_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        segments = grib_to_netcdf._define_forecast_segments_nowcast(run_date)
        fcst_section_hrs_list, _, _, _, _ = segments

        expected = [
            {
                "section 1": ("20230225/18", -1, 5, 6),
                "section 2": ("20230226/00", 1, 1, 12),
                "section 3": ("20230226/12", 13, 1, 11),
            },
            {
                "section 1": ("20230226/12", -1, 11, 35),
            },
            {
                "section 1": ("20230226/12", -1, 35, 48),
            },
        ]
        assert fcst_section_hrs_list == expected

    def test_zero_starts(self, caplog):
        run_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        segments = grib_to_netcdf._define_forecast_segments_nowcast(run_date)
        _, zero_starts, _, _, _ = segments

        assert zero_starts == [[1, 13], [], []]

    def test_lengths(self, caplog):
        run_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        segments = grib_to_netcdf._define_forecast_segments_nowcast(run_date)
        _, _, lengths, _, _ = segments

        assert lengths == [24, 24, 13]

    def test_subdirectories(self, caplog):
        run_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        segments = grib_to_netcdf._define_forecast_segments_nowcast(run_date)
        _, _, _, subdirectories, _ = segments

        assert subdirectories == ["", "fcst", "fcst"]

    def test_yearmonthdays(self, caplog):
        run_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        segments = grib_to_netcdf._define_forecast_segments_nowcast(run_date)
        _, _, _, _, yearmonthdays = segments

        nemo_yyyymmdd = "[y]YYYY[m]MM[d]DD"
        expected = [
            run_date.format(nemo_yyyymmdd),
            run_date.shift(days=+1).format(nemo_yyyymmdd),
            run_date.shift(days=+2).format(nemo_yyyymmdd),
        ]
        assert yearmonthdays == expected


class TestDefineForecastSegmentsForecast2:
    """Unit tests for _define_forecast_segments_forecast2() function."""

    def test_log_messages(self, caplog):
        run_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        grib_to_netcdf._define_forecast_segments_forecast2(run_date)

        assert caplog.records[0].levelname == "DEBUG"
        expected = f"forecast section: {run_date.format('YYYYMMDD')}/06"
        assert caplog.messages[0] == expected
        assert caplog.records[1].levelname == "DEBUG"
        expected = f"next day forecast section: {run_date.format('YYYYMMDD')}/06"
        assert caplog.messages[1] == expected

    def test_fcst_section_hrs_list(self, caplog):
        run_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        segments = grib_to_netcdf._define_forecast_segments_forecast2(run_date)
        fcst_section_hrs_list, _, _, _, _ = segments

        expected = [
            {"section 1": ("20230226/06", -1, 17, 41)},
            {"section 1": ("20230226/06", -1, 41, 48)},
        ]
        assert fcst_section_hrs_list == expected

    def test_zero_starts(self, caplog):
        run_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        segments = grib_to_netcdf._define_forecast_segments_forecast2(run_date)
        _, zero_starts, _, _, _ = segments

        assert zero_starts == [[], []]

    def test_lengths(self, caplog):
        run_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        segments = grib_to_netcdf._define_forecast_segments_forecast2(run_date)
        _, _, lengths, _, _ = segments

        assert lengths == [24, 7]

    def test_subdirectories(self, caplog):
        run_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        segments = grib_to_netcdf._define_forecast_segments_forecast2(run_date)
        _, _, _, subdirectories, _ = segments

        assert subdirectories == ["fcst", "fcst"]

    def test_yearmonthdays(self, caplog):
        run_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        segments = grib_to_netcdf._define_forecast_segments_forecast2(run_date)
        _, _, _, _, yearmonthdays = segments

        nemo_yyyymmdd = "[y]YYYY[m]MM[d]DD"
        expected = [
            run_date.shift(days=+1).format(nemo_yyyymmdd),
            run_date.shift(days=+2).format(nemo_yyyymmdd),
        ]
        assert yearmonthdays == expected


@pytest.mark.skipif(
    "GITHUB_ACTIONS" in os.environ,
    reason="ligwgrib2 is not yet in GHA test env",
)
class TestRotateGribWind:
    """Unit tests for __rotate_grib_wind() function."""

    def test_missing_wind_var_file_raises_WorkerError(
        self, config, caplog, tmp_path, monkeypatch
    ):
        grib_dir = tmp_path / Path(config["weather"]["download"]["2.5 km"]["GRIB dir"])
        monkeypatch.setitem(
            config["weather"]["download"]["2.5 km"], "GRIB dir", grib_dir
        )
        hour_dir = grib_dir.joinpath("20230226", "18", "005")
        hour_dir.mkdir(parents=True)
        hour_dir = grib_dir.joinpath("20230226", "18", "006")
        hour_dir.mkdir(parents=True)

        fcst_section_hrs = {"section 1": ("20230226/18", -1, 5, 6)}
        caplog.set_level(logging.DEBUG)

        with pytest.raises(WorkerError):
            grib_to_netcdf._rotate_grib_wind(fcst_section_hrs, config)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"No GRIB file found; a previous download may have failed for 20230226/18/005 UGRD_AGL-10m"
        assert caplog.messages[0] == expected

    def test_empty_wind_var_file_raises_WorkerError(
        self, config, caplog, tmp_path, monkeypatch
    ):
        grib_dir = tmp_path / Path(config["weather"]["download"]["2.5 km"]["GRIB dir"])
        monkeypatch.setitem(
            config["weather"]["download"]["2.5 km"], "GRIB dir", grib_dir
        )
        for hour in ("005", "006"):
            hour_dir = grib_dir.joinpath("20230226", "18", hour)
            hour_dir.mkdir(parents=True)
            for wind_var in ("UGRD_AGL-10m", "VGRD_AGL-10m"):
                wind_file = (
                    hour_dir
                    / f"20230226T18Z_MSC_HRDPS_{wind_var}_RLatLon0.0225_PT{hour}H.grib2"
                )
                wind_file.write_bytes(b"")

        fcst_section_hrs = {"section 1": ("20230226/18", -1, 5, 6)}
        caplog.set_level(logging.DEBUG)

        with pytest.raises(WorkerError):
            grib_to_netcdf._rotate_grib_wind(fcst_section_hrs, config)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"Empty GRIB file found; a previous download may have failed for 20230226/18/005 UGRD_AGL-10m"
        assert caplog.messages[0] == expected

    def test_remove_outuv_file(self, config, caplog, tmp_path, monkeypatch):
        grib_dir = tmp_path / Path(config["weather"]["download"]["2.5 km"]["GRIB dir"])
        monkeypatch.setitem(
            config["weather"]["download"]["2.5 km"], "GRIB dir", grib_dir
        )
        hour_dir = grib_dir.joinpath("20230226", "18", "005")
        hour_dir.mkdir(parents=True)
        for wind_var in ("UGRD_AGL-10m", "VGRD_AGL-10m"):
            wind_file = (
                hour_dir
                / f"20230226T18Z_MSC_HRDPS_{wind_var}_RLatLon0.0225_PT005H.grib2"
            )
            wind_file.write_bytes(b"not empty")
        outuv = hour_dir / "UV.grib"
        outuv.write_bytes(b"")
        hour_dir = grib_dir.joinpath("20230226", "18", "006")
        hour_dir.mkdir(parents=True)
        for wind_var in ("UGRD_AGL-10m", "VGRD_AGL-10m"):
            wind_file = (
                hour_dir
                / f"20230226T18Z_MSC_HRDPS_{wind_var}_RLatLon0.0225_PT006H.grib2"
            )
            wind_file.write_bytes(b"not empty")

        fcst_section_hrs = {"section 1": ("20230226/18", -1, 5, 6)}
        caplog.set_level(logging.DEBUG)

        grib_to_netcdf._rotate_grib_wind(fcst_section_hrs, config)

        assert not outuv.exists()
