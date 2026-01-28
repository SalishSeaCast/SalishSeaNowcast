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


"""Unit test for SalishSeaCast crop_gribs worker."""

import grp
import logging
import os
import textwrap
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping

import arrow
import attr
import nemo_nowcast
import numpy
import pytest
import xarray

from nowcast.workers import crop_gribs


@pytest.fixture
def config(base_config: nemo_nowcast.Config) -> nemo_nowcast.Config | Mapping:
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(textwrap.dedent("""\
                file group: allen

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
                """))
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

    def test_add_backfill_option(self, mock_worker):
        worker = crop_gribs.main()
        assert worker.cli.parser._actions[5].dest == "backfill"
        assert worker.cli.parser._actions[5].default is False
        assert worker.cli.parser._actions[5].help

    def test_add_forecast_hour_option(self, mock_worker):
        worker = crop_gribs.main()
        assert worker.cli.parser._actions[6].dest == "var_hour"
        assert worker.cli.parser._actions[6].type == int
        assert worker.cli.parser._actions[6].help

    def test_add_variable_option(self, mock_worker):
        worker = crop_gribs.main()
        assert worker.cli.parser._actions[7].dest == "msc_var_name"
        assert worker.cli.parser._actions[7].help


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

    def test_file_group(self, prod_config):
        assert "file group" in prod_config
        assert prod_config["file group"] == "sallen"

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
            ["LHTFL_Sfc", "slhtf", "LHTFL_surface"],
            ["TMP_AGL-2m", "t2m", "tair"],
            ["SPFH_AGL-2m", "sh2", "qair"],
            ["RH_AGL-2m", "r2", "RH_2maboveground"],
            ["APCP_Sfc", "unknown", "precip"],
            ["PRATE_Sfc", "prate", "PRATE_surface"],
            ["PRMSL_MSL", "prmsl", "atmpres"],
        ]
        assert weather_download["lon indices"] == [300, 490]
        assert weather_download["lat indices"] == [230, 460]

    def test_logging_section(self, prod_config):
        loggers = prod_config["logging"]["publisher"]["loggers"]
        assert loggers["watchdog"]["qualname"] == "watchdog"
        assert loggers["watchdog"]["level"] == "WARNING"
        assert loggers["watchdog"]["formatter"] == "simple"


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
    def mock_calc_grib_file_paths(monkeypatch):
        def _mock_calc_grib_file_paths(*args):
            return set()

        monkeypatch.setattr(
            crop_gribs, "_calc_grib_file_paths", _mock_calc_grib_file_paths
        )

    @staticmethod
    @pytest.fixture
    def mock_observer(monkeypatch):
        class MockObserver:
            def schedule(self, event_handler, path, recursive):
                pass

            def join(self, **kwargs):
                pass

            def start(self):
                pass

            def stop(self):
                pass

        monkeypatch.setattr(crop_gribs.watchdog.observers, "Observer", MockObserver)

    @staticmethod
    @pytest.fixture
    def mock_write_ssc_grib_file(monkeypatch):
        def _mock_write_ssc_grib_file(eccc_grib_file, config):
            pass

        monkeypatch.setattr(
            crop_gribs, "_write_ssc_grib_file", _mock_write_ssc_grib_file
        )

    def test_checklist_not_backfill(
        self,
        forecast,
        mock_calc_grib_file_paths,
        mock_observer,
        config,
        caplog,
        monkeypatch,
    ):
        grp_name = grp.getgrgid(os.getgid()).gr_name
        monkeypatch.setitem(config, "file group", grp_name)
        parsed_args = SimpleNamespace(
            forecast=forecast,
            fcst_date=arrow.get("2023-08-11"),
            backfill=False,
            var_hour=None,
            msc_var_name=None,
        )
        caplog.set_level(logging.DEBUG)

        checklist = crop_gribs.crop_gribs(parsed_args, config)

        expected = {forecast: "cropped to SalishSeaCast subdomain"}
        assert checklist == expected

    def test_checklist_backfill(
        self,
        forecast,
        mock_write_ssc_grib_file,
        config,
        caplog,
        monkeypatch,
    ):
        def _mock_calc_grib_file_paths(*args):
            return {
                f"forcing/atmospheric/continental2.5/GRIB/20231115/{forecast}/029/"
                f"20231115T{forecast}Z_MSC_HRDPS_APCP_Sfc_RLatLon0.0225_PT029H.grib2",
            }

        monkeypatch.setattr(
            crop_gribs, "_calc_grib_file_paths", _mock_calc_grib_file_paths
        )

        grp_name = grp.getgrgid(os.getgid()).gr_name
        monkeypatch.setitem(config, "file group", grp_name)
        parsed_args = SimpleNamespace(
            forecast=forecast,
            fcst_date=arrow.get("2023-11-15"),
            backfill=True,
            var_hour=None,
            msc_var_name=None,
        )
        caplog.set_level(logging.DEBUG)

        checklist = crop_gribs.crop_gribs(parsed_args, config)

        assert caplog.records[1].levelname == "INFO"
        expected = (
            f"finished cropping ECCC grib files to SalishSeaCast subdomain in "
            f"forcing/atmospheric/continental2.5/GRIB/20231115/{forecast}/"
        )
        assert caplog.messages[1] == expected

        expected = {forecast: "cropped to SalishSeaCast subdomain"}
        assert checklist == expected

    def test_observer_log_messages(
        self,
        forecast,
        mock_calc_grib_file_paths,
        mock_observer,
        config,
        caplog,
        monkeypatch,
    ):
        grp_name = grp.getgrgid(os.getgid()).gr_name
        monkeypatch.setitem(config, "file group", grp_name)
        parsed_args = SimpleNamespace(
            forecast=forecast,
            fcst_date=arrow.get("2023-08-14"),
            backfill=False,
            var_hour=None,
            msc_var_name=None,
        )
        caplog.set_level(logging.DEBUG)

        crop_gribs.crop_gribs(parsed_args, config)

        assert caplog.records[0].levelname == "INFO"
        expected = (
            f"cropping 2023-08-14 ECCC HRDPS 2.5km continental {forecast}Z GRIB files to "
            f"SalishSeaCast subdomain"
        )
        assert caplog.messages[0] == expected

        assert caplog.records[1].levelname == "INFO"
        expected = (
            f"starting to watch for ECCC grib files to crop in "
            f"forcing/atmospheric/continental2.5/GRIB/20230814/{forecast}/"
        )
        assert caplog.messages[1] == expected

        assert caplog.records[2].levelname == "INFO"
        expected = (
            f"finished cropping ECCC grib files to SalishSeaCast subdomain in "
            f"forcing/atmospheric/continental2.5/GRIB/20230814/{forecast}/"
        )
        assert caplog.messages[2] == expected

    def test_crop_one_file_log_messages(
        self,
        forecast,
        mock_write_ssc_grib_file,
        mock_observer,
        config,
        caplog,
        monkeypatch,
    ):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            fcst_date=arrow.get("2023-08-14"),
            backfill=False,
            var_hour=29,
            msc_var_name="APCP_Sfc",
        )
        caplog.set_level(logging.DEBUG)

        crop_gribs.crop_gribs(parsed_args, config)

        assert caplog.records[0].levelname == "INFO"
        expected = (
            f"cropping 2023-08-14 ECCC HRDPS 2.5km continental {forecast}Z GRIB files to "
            f"SalishSeaCast subdomain"
        )
        assert caplog.messages[0] == expected

        assert caplog.records[1].levelname == "DEBUG"
        expected = (
            f"creating ECCC GRIB file paths list for 20230814 {forecast}Z forecast"
        )
        assert caplog.messages[1] == expected

        assert caplog.records[2].levelname == "INFO"
        expected = (
            f"finished cropping ECCC grib file to SalishSeaCast subdomain: "
            f"forcing/atmospheric/continental2.5/GRIB/20230814/{forecast}/029/"
            f"20230814T{forecast}Z_MSC_HRDPS_APCP_Sfc_RLatLon0.0225_PT029H.grib2"
        )
        assert caplog.messages[2] == expected


class TestCalcGribFilePaths:
    """Unit tests for _calc_grib_file_paths() function."""

    def test_ECCC_grib_file_paths(self, config):
        file_tmpl = config["weather"]["download"]["2.5 km"]["ECCC file template"]
        fcst_date = arrow.get("2023-04-03")
        fcst_hr = "12"
        fcst_dur = 2
        msc_var_names = ["UGRD_AGL-10m", "VGRD_AGL-10m"]

        grib_files = crop_gribs._calc_grib_file_paths(
            file_tmpl, fcst_date, fcst_hr, fcst_dur, msc_var_names, config
        )

        expected = {
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230403/12/001/"
                "20230403T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H.grib2"
            ),
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230403/12/001/"
                "20230403T12Z_MSC_HRDPS_VGRD_AGL-10m_RLatLon0.0225_PT001H.grib2"
            ),
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230403/12/002/"
                "20230403T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT002H.grib2"
            ),
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230403/12/002/"
                "20230403T12Z_MSC_HRDPS_VGRD_AGL-10m_RLatLon0.0225_PT002H.grib2"
            ),
        }
        assert grib_files == expected

    def test_ECCC_grib_file_path_for_one_file(self, config):
        file_tmpl = config["weather"]["download"]["2.5 km"]["ECCC file template"]
        fcst_date = arrow.get("2023-08-11")
        fcst_hr = "12"
        fcst_dur = 28
        msc_var_names = ["UGRD_AGL-10m", "VGRD_AGL-10m"]

        grib_files = crop_gribs._calc_grib_file_paths(
            file_tmpl,
            fcst_date,
            fcst_hr,
            fcst_dur,
            msc_var_names,
            config,
            "VGRD_AGL-10m",
        )

        expected = {
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230811/12/028/"
                "20230811T12Z_MSC_HRDPS_VGRD_AGL-10m_RLatLon0.0225_PT028H.grib2"
            ),
        }
        assert grib_files == expected

    def test_log_messages(self, config, caplog):
        file_tmpl = config["weather"]["download"]["2.5 km"]["ECCC file template"]
        fcst_date = arrow.get("2023-07-21")
        fcst_hr = "12"
        fcst_dur = 2
        msc_var_names = ["UGRD_AGL-10m", "UGRD_AGL-10m"]
        caplog.set_level(logging.DEBUG)

        crop_gribs._calc_grib_file_paths(
            file_tmpl, fcst_date, fcst_hr, fcst_dur, msc_var_names, config
        )

        assert caplog.records[0].levelname == "DEBUG"
        expected = f"creating ECCC GRIB file paths list for 20230721 12Z forecast"
        assert caplog.messages[0] == expected


class TestWriteSscGribFile:
    """Unit test for _write_ssc_grib_file() function."""

    @staticmethod
    @pytest.fixture
    def mock_open_dataset(monkeypatch):
        def _mock_open_dataset(path, engine, backend_kwargs):
            class Mock_open_dataset:
                def __int__(self):
                    pass

                def __enter__(self):
                    return xarray.Dataset(
                        data_vars={
                            "u10": (["y", "x"], numpy.array([[], []], dtype=float))
                        },
                    )

                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass

            return Mock_open_dataset()

        monkeypatch.setattr(crop_gribs.xarray, "open_dataset", _mock_open_dataset)

    @staticmethod
    @pytest.fixture
    def mock_xarray_to_grib(monkeypatch):
        def _mock_xarray_to_grib(ssc_ds, ssc_grib_file):
            pass

        monkeypatch.setattr(crop_gribs, "_xarray_to_grib", _mock_xarray_to_grib)

    def test_grib_file_exists_so_no_write(self, config, caplog, tmp_path):
        grib_dir = tmp_path / config["weather"]["download"]["2.5 km"]["GRIB dir"]
        grib_dir.mkdir(parents=True)
        grib_file_dir = grib_dir / "20231115/12/001/"
        grib_file_dir.mkdir(parents=True)
        eccc_grib_file = Path(
            grib_file_dir
            / "20231115T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H.grib2"
        )
        ssc_grib_file = Path(
            grib_file_dir
            / "20231115T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H_SSC.grib2"
        )
        ssc_grib_file.write_bytes(b"")
        caplog.set_level(logging.DEBUG)

        crop_gribs._write_ssc_grib_file(eccc_grib_file, config)

        assert caplog.records[0].levelname == "DEBUG"
        expected = (
            f"cropping skipped because SalishSeaCast subdomain GRIB file exist: "
            f"{grib_file_dir / '20231115T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H_SSC.grib2'}"
        )
        assert caplog.messages[0] == expected

    def test_log_message(
        self,
        mock_open_dataset,
        mock_xarray_to_grib,
        config,
        caplog,
        tmp_path,
        monkeypatch,
    ):
        grib_dir = tmp_path / config["weather"]["download"]["2.5 km"]["GRIB dir"]
        grib_dir.mkdir(parents=True)
        monkeypatch.setitem(
            config["weather"]["download"]["2.5 km"], "GRIB dir", grib_dir
        )
        grib_file_dir = grib_dir / "20230727/12/001/"
        grib_file_dir.mkdir(parents=True)
        eccc_grib_file = Path(
            grib_file_dir
            / "20230727T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H.grib2"
        )
        caplog.set_level(logging.DEBUG)

        crop_gribs._write_ssc_grib_file(eccc_grib_file, config)

        assert caplog.records[0].levelname == "DEBUG"
        expected = (
            f"wrote GRIB file cropped to SalishSeaCast subdomain: "
            f"{grib_file_dir / '20230727T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H_SSC.grib2'}"
        )
        assert caplog.messages[0] == expected


class TestHandleStalledObserver:
    """Unit tests for _handle_stalled_observer() function."""

    def test_gt_10_files_unprocessed(self, config, caplog):
        grib_dir = Path("forcing/atmospheric/continental2.5/GRIB/20230920/12/043/")
        eccc_grib_files = {
            grib_dir / "20230920T12Z_MSC_HRDPS_APCP_Sfc_RLatLon0.0225_PT043H.grib2",
            grib_dir / "20230920T12Z_MSC_HRDPS_DLWRF_Sfc_RLatLon0.0225_PT043H.grib2",
            grib_dir / "20230920T12Z_MSC_HRDPS_DSWRF_Sfc_RLatLon0.0225_PT043H.grib2",
            grib_dir / "20230920T12Z_MSC_HRDPS_LHTFL_Sfc_RLatLon0.0225_PT043H.grib2",
            grib_dir / "20230920T12Z_MSC_HRDPS_PRATE_Sfc_RLatLon0.0225_PT043H.grib2",
            grib_dir / "20230920T12Z_MSC_HRDPS_PRMSL_MSL_RLatLon0.0225_PT043H.grib2",
            grib_dir / "20230920T12Z_MSC_HRDPS_RH_AGL-2m_RLatLon0.0225_PT043H.grib2",
            grib_dir / "20230920T12Z_MSC_HRDPS_SPFH_AGL-2m_RLatLon0.0225_PT043H.grib2",
            grib_dir / "20230920T12Z_MSC_HRDPS_TMP_AGL-2m_RLatLon0.0225_PT043H.grib2",
            grib_dir / "20230920T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT043H.grib2",
            grib_dir / "20230920T12Z_MSC_HRDPS_VGRD_AGL-10m_RLatLon0.0225_PT043H.grib2",
        }
        fcst_hr = "12"
        caplog.set_level(logging.DEBUG)

        crop_gribs._handle_stalled_observer(eccc_grib_files, fcst_hr, config)

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "CRITICAL"
        expected = (
            f"crop_gribs 12 has watched for 8h and 11 files remain unprocessed: "
            f"{' '.join(os.fspath(eccc_grib_file) for eccc_grib_file in eccc_grib_files)}"
        )
        assert caplog.messages[0] == expected

    def test_retry_success(self, config, caplog, tmp_path, monkeypatch):
        def _mock_write_ssc_grib_file(eccc_grib_file, config):
            pass

        monkeypatch.setattr(
            crop_gribs, "_write_ssc_grib_file", _mock_write_ssc_grib_file
        )
        grib_dir = tmp_path / config["weather"]["download"]["2.5 km"]["GRIB dir"]
        grib_dir.mkdir(parents=True)
        monkeypatch.setitem(
            config["weather"]["download"]["2.5 km"], "GRIB dir", grib_dir
        )
        grib_file_dir = grib_dir / "20230920/12/043/"
        grib_file_dir.mkdir(parents=True)
        eccc_grib_files = {
            grib_dir / "20230920T12Z_MSC_HRDPS_APCP_Sfc_RLatLon0.0225_PT043H.grib2",
        }
        fcst_hr = "12"
        caplog.set_level(logging.DEBUG)

        crop_gribs._handle_stalled_observer(eccc_grib_files, fcst_hr, config)

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
        expected = f"crop_gribs 12 has watched for 8h; retrying remaining 1 file(s)"
        assert caplog.messages[0] == expected

    def test_file_not_found(self, config, caplog, tmp_path, monkeypatch):
        grib_dir = tmp_path / config["weather"]["download"]["2.5 km"]["GRIB dir"]
        grib_dir.mkdir(parents=True)
        monkeypatch.setitem(
            config["weather"]["download"]["2.5 km"], "GRIB dir", grib_dir
        )
        grib_file_dir = grib_dir / "20230920/12/043/"
        grib_file_dir.mkdir(parents=True)
        eccc_grib_files = {
            grib_dir / "20230920T12Z_MSC_HRDPS_APCP_Sfc_RLatLon0.0225_PT043H.grib2",
        }
        fcst_hr = "12"
        caplog.set_level(logging.DEBUG)

        crop_gribs._handle_stalled_observer(eccc_grib_files, fcst_hr, config)

        assert len(caplog.records) == 2
        assert caplog.records[1].levelname == "CRITICAL"
        expected = (
            f"crop_gribs 12 has watched for 8h and at least 1 file has not "
            f"yet been downloaded: {' '.join(os.fspath(eccc_grib_file) for eccc_grib_file in eccc_grib_files)}"
        )
        assert caplog.messages[1] == expected


class TestGribFileEventHandler:
    """Unit tests for _GribFileEventHandler class."""

    def test_constructor(self, config):
        handler = crop_gribs._GribFileEventHandler(eccc_grib_files=set(), config=config)
        assert handler.eccc_grib_files == set()
        assert handler.config == config

    def test_crop_expected_file(self, config, caplog, tmp_path, monkeypatch):
        @attr.s
        class MockWatchdogEvent:
            src_path = attr.ib()

        def mock_write_ssc_grib_file(eccc_grib_file, config):
            pass

        monkeypatch.setattr(
            crop_gribs, "_write_ssc_grib_file", mock_write_ssc_grib_file
        )

        grib_dir = tmp_path / config["weather"]["download"]["2.5 km"]["GRIB dir"]
        grib_dir.mkdir(parents=True)
        monkeypatch.setitem(
            config["weather"]["download"]["2.5 km"], "GRIB dir", grib_dir
        )
        grib_forecast_dir = grib_dir / "20230808" / "18" / "043"
        grib_forecast_dir.mkdir(parents=True)
        eccc_grib_file = (
            grib_forecast_dir
            / "20230808T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT043H.grib2"
        )
        eccc_grib_file.write_bytes(b"")
        eccc_grib_files = {eccc_grib_file}

        caplog.set_level(logging.DEBUG)

        handler = crop_gribs._GribFileEventHandler(eccc_grib_files, config)
        handler.on_closed(MockWatchdogEvent(src_path=os.fspath(eccc_grib_file)))

        assert caplog.records[0].levelname == "DEBUG"
        expected = f"observer thread files remaining to process: 0"
        assert caplog.messages[0] == expected
        assert eccc_grib_file not in eccc_grib_files
        assert not eccc_grib_file.exists()

    def test_ignore_unexpected_file(self, config, caplog, tmp_path, monkeypatch):
        @attr.s
        class MockWatchdogEvent:
            src_path = attr.ib()

        grib_dir = tmp_path / config["weather"]["download"]["2.5 km"]["GRIB dir"]
        grib_dir.mkdir(parents=True)
        monkeypatch.setitem(
            config["weather"]["download"]["2.5 km"], "GRIB dir", grib_dir
        )
        grib_forecast_dir = grib_dir / "20230808" / "18" / "043"
        grib_forecast_dir.mkdir(parents=True)
        eccc_grib_file = (
            grib_forecast_dir
            / "20230808T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT043H.grib2"
        )
        eccc_grib_file.write_bytes(b"")
        eccc_grib_files = {eccc_grib_file}

        caplog.set_level(logging.DEBUG)

        handler = crop_gribs._GribFileEventHandler(eccc_grib_files, config)
        handler.on_closed(MockWatchdogEvent(src_path="foo"))

        assert not caplog.records
        assert eccc_grib_file in eccc_grib_files
        assert eccc_grib_file.exists()
