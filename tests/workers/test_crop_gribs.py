#  Copyright 2013 – present by the SalishSeaCast Project contributors
#  and The University of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# SPDX-License-Identifier: Apache-2.0


"""Unit test for SalishSeaCast crop_gribs worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import crop_gribs


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
                      ECCC file template: "{date}T{forecast}Z_MSC_HRDPS_{variable}_RLatLon0.0225_PT{hour}H.grib2"
                      SSC cropped file template: "{date}T{forecast}Z_MSC_HRDPS_{variable}_RLatLon0.0225_PT{hour}H_SSC.grib2"
                      SSC georef: forcing/atmospheric/continental2.5/GRIB/SSC_grid_georef.nc
                      variables:
                        # [MSC name, GRIB std name, NEMO name]
                        - [UGRD_AGL-10m, u10, u_wind]           # u component of wind velocity at 10m elevation
                        - [VGRD_AGL-10m, v10, v_wind]           # v component of wind velocity at 10m elevation
                        - [DSWRF_Sfc, ssrd, solar]              # accumulated downward shortwave (solar) radiation at ground level
                        - [DLWRF_Sfc, strd, therm_rad]          # accumulated downward longwave (thermal) radiation at ground level
                        - [LHTFL_Sfc, lhtfl, LHTFL_surface]     # upward surface latent heat flux (for VHFR FVCOM)
                        - [TMP_AGL-2m, t2m, tair]               # air temperature at 2m elevation
                        - [SPFH_AGL-2m, sh2, qair]              # specific humidity at 2m elevation
                        - [RH_AGL-2m, r2, RH_2maboveground]     # relative humidity at 2m elevation (for VHFR FVCOM)
                        - [APCP_Sfc, unknown, precip]           # accumulated precipitation at ground level
                        - [PRATE_Sfc, prate, PRATE_surface]     # precipitation rate at ground level (for VHFR FVCOM)
                        - [PRMSL_MSL, prmsl, atmpres]           # atmospheric pressure at mean sea level
                      lon indices: [300, 490]
                      lat indices: [230, 460]
                      forecast duration: 48  # hours
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(crop_gribs, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = crop_gribs.main()
        assert worker.name == "crop_gribs"
        assert worker.description.startswith(
            "SalishSeaCast worker that loads ECCC MSC 2.5 km rotated lat-lon continental grid "
        )

    def test_add_forecast_arg(self, mock_worker):
        worker = crop_gribs.main()
        assert worker.cli.parser._actions[3].dest == "forecast"
        assert worker.cli.parser._actions[3].choices == {"00", "06", "12", "18"}
        assert worker.cli.parser._actions[3].help

    def test_add_forecast_date_option(self, mock_worker):
        worker = crop_gribs.main()
        assert worker.cli.parser._actions[4].dest == "fcst_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[4].type == expected
        assert worker.cli.parser._actions[4].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[4].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "crop_gribs" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["crop_gribs"]
        assert msg_registry["checklist key"] == "weather forecast"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["crop_gribs"]
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

    def test_weather_download_2_5_km_section(self, prod_config):
        weather_download = prod_config["weather"]["download"]["2.5 km"]
        assert (
            weather_download["GRIB dir"]
            == "/results/forcing/atmospheric/continental2.5/GRIB/"
        )
        assert (
            weather_download["ECCC file template"]
            == "{date}T{forecast}Z_MSC_HRDPS_{variable}_RLatLon0.0225_PT{hour}H.grib2"
        )
        assert (
            weather_download["SSC cropped file template"]
            == "{date}T{forecast}Z_MSC_HRDPS_{variable}_RLatLon0.0225_PT{hour}H_SSC.grib2"
        )
        assert (
            weather_download["SSC georef"]
            == "/results/forcing/atmospheric/continental2.5/GRIB/SSC_grid_georef.nc"
        )
        assert weather_download["variables"] == [
            ["UGRD_AGL-10m", "u10", "u_wind"],
            ["VGRD_AGL-10m", "v10", "v_wind"],
            ["DSWRF_Sfc", "ssrd", "solar"],
            ["DLWRF_Sfc", "strd", "therm_rad"],
            ["LHTFL_Sfc", "lhtfl", "LHTFL_surface"],
            ["TMP_AGL-2m", "t2m", "tair"],
            ["SPFH_AGL-2m", "sh2", "qair"],
            ["RH_AGL-2m", "r2", "RH_2maboveground"],
            ["APCP_Sfc", "unknown", "precip"],
            ["PRATE_Sfc", "prate", "PRATE_surface"],
            ["PRMSL_MSL", "prmsl", "atmpres"],
        ]
        assert weather_download["lon indices"] == [300, 490]
        assert weather_download["lat indices"] == [230, 460]


@pytest.mark.parametrize(
    "forecast, forecast_date",
    (
        ("00", "2023-04-02"),
        ("06", "2023-04-02"),
        ("12", "2023-04-02"),
        ("18", "2023-04-02"),
    ),
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, forecast, forecast_date, caplog):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            fcst_date=forecast_date,
        )
        caplog.set_level(logging.DEBUG)

        msg_type = crop_gribs.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"{forecast_date} {forecast} GRIBs cropping complete"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {forecast}"


@pytest.mark.parametrize(
    "forecast, forecast_date",
    (
        ("00", "2023-04-02"),
        ("06", "2023-04-02"),
        ("12", "2023-04-02"),
        ("18", "2023-04-02"),
    ),
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, forecast, forecast_date, caplog):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            fcst_date=forecast_date,
        )
        caplog.set_level(logging.DEBUG)

        msg_type = crop_gribs.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"{forecast_date} {forecast} GRIBs cropping failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {forecast}"


@pytest.mark.parametrize("forecast", ("00", "06", "12", "18"))
class TestCropGribs:
    """Unit tests for crop_gribs() function."""

    @staticmethod
    @pytest.fixture
    def mock_write_ssc_grib_files(monkeypatch):
        def _mock_write_ssc_grib_files(
            msc_var, grib_var, eccc_grib_files, ssc_grib_files, config
        ):
            pass

        monkeypatch.setattr(
            crop_gribs, "_write_ssc_grib_files", _mock_write_ssc_grib_files
        )

    def test_checklist(self, forecast, mock_write_ssc_grib_files, config, caplog):
        parsed_args = SimpleNamespace(
            forecast=forecast, fcst_date=arrow.get("2023-04-02")
        )
        caplog.set_level(logging.DEBUG)

        checklist = crop_gribs.crop_gribs(parsed_args, config)

        expected = {forecast: "cropped to SalishSeaCast subdomain"}
        assert checklist == expected

    def test_log_messages(self, forecast, mock_write_ssc_grib_files, config, caplog):
        parsed_args = SimpleNamespace(
            forecast=forecast, fcst_date=arrow.get("2023-04-02")
        )
        caplog.set_level(logging.DEBUG)

        crop_gribs.crop_gribs(parsed_args, config)

        assert caplog.records[0].levelname == "INFO"
        expected = (
            f"cropping 2023-04-02 ECCC HRDPS 2.5km continental {forecast}Z GRIB files to "
            f"SalishSeaCast subdomain"
        )
        assert caplog.messages[0] == expected


class TestCalcGribFilePaths:
    """Unit tests for _calc_grib_file_paths() function."""

    def test_ECCC_grib_file_paths(self, config):
        file_tmpl = config["weather"]["download"]["2.5 km"]["ECCC file template"]
        fcst_date = arrow.get("2023-04-03")
        fcst_hr = "12"
        fcst_dur = 2
        msc_var = "UGRD_AGL-10m"

        grib_files = crop_gribs._calc_grib_file_paths(
            file_tmpl, fcst_date, fcst_hr, fcst_dur, msc_var, config
        )

        expected = [
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230403/12/001/"
                "20230403T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H.grib2"
            ),
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230403/12/002/"
                "20230403T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT002H.grib2"
            ),
        ]
        assert grib_files == expected

    def test_SSC_cropped_grib_file_paths(self, config):
        file_tmpl = config["weather"]["download"]["2.5 km"]["SSC cropped file template"]
        fcst_date = arrow.get("2023-04-03")
        fcst_hr = "12"
        fcst_dur = 2
        msc_var = "UGRD_AGL-10m"

        grib_files = crop_gribs._calc_grib_file_paths(
            file_tmpl, fcst_date, fcst_hr, fcst_dur, msc_var, config
        )

        expected = [
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230403/12/001/"
                "20230403T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H_SSC.grib2"
            ),
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230403/12/002/"
                "20230403T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT002H_SSC.grib2"
            ),
        ]
        assert grib_files == expected

    @pytest.mark.parametrize(
        "grib_domain, file_tmpl_key",
        (
            ("ECCC", "ECCC file template"),
            ("SSC", "SSC cropped file template"),
        ),
    )
    def test_log_messages(self, grib_domain, file_tmpl_key, config, caplog):
        file_tmpl = config["weather"]["download"]["2.5 km"][file_tmpl_key]
        fcst_date = arrow.get("2023-04-03")
        fcst_hr = "12"
        fcst_dur = 2
        msc_var = "UGRD_AGL-10m"
        caplog.set_level(logging.DEBUG)

        crop_gribs._calc_grib_file_paths(
            file_tmpl, fcst_date, fcst_hr, fcst_dur, msc_var, config
        )

        assert caplog.records[0].levelname == "DEBUG"
        expected = f"creating UGRD_AGL-10m {grib_domain} GRIB file paths list for 20230403 12Z forecast"
        assert caplog.messages[0] == expected


# class TestWriteSscGribFiles:
#     """Unit tests for _write_ssc_grib_files() function."""
#
#     def test_log_messages(self, config, caplog, monkeypatch):
#         def mock_open_dataset(path, engine, backend_kwargs):
#             pass
#
#         monkeypatch.setattr(crop_gribs.xarray, "open_dataset", mock_open_dataset)
#
#         msc_var = "UGRD_AGL-10m"
#         grib_var = "u10"
#         eccc_grib_files = [
#             Path(
#                 "forcing/atmospheric/continental2.5/GRIB/20230403/12/001/"
#                 "20230403T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H.grib2"
#             ),
#             Path(
#                 "forcing/atmospheric/continental2.5/GRIB/20230403/12/002/"
#                 "20230403T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT002H.grib2"
#             ),
#         ]
#         ssc_grib_files = [
#             Path(
#                 "forcing/atmospheric/continental2.5/GRIB/20230403/12/001/"
#                 "20230403T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H_SSC.grib2"
#             ),
#             Path(
#                 "forcing/atmospheric/continental2.5/GRIB/20230403/12/002/"
#                 "20230403T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT002H_SSC.grib2"
#             ),
#         ]
#         caplog.set_level(logging.DEBUG)
#
#         crop_gribs._write_ssc_grib_files(msc_var, grib_var, eccc_grib_files, ssc_grib_files, config)
#
#         assert caplog.records[0].levelname == "DEBUG"
#         expected = (
#             f"wrote UGRD_AGL-10m GRIB file cropped to SalishSeaCast subdomain: "
#             f""
#         )
#         assert caplog.messages[0] == expected
