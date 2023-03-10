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
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import numpy
import pytest
import xarray

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
                      file template: "{date}T{forecast}Z_MSC_HRDPS_{variable}_RLatLon0.0225_PT{hour}H.grib2"
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
                      accumulation variables:
                        - solar
                        - therm_rad
                        - precip
                      lon indices: [300, 490]
                      lat indices: [230, 460]

                  ops dir: forcing/atmospheric/continental2.5/nemo_forcing/
                  file template: "hrdps_{:y%Ym%md%d}.nc"
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(grib_to_netcdf, "NowcastWorker", mock_nowcast_worker)


class TestGirdIndices:
    """Unit tests for module variables that define indices of sub-region grid that is extracted."""

    def test_SandHeads_indices(self):
        assert grib_to_netcdf.SandI == 118
        assert grib_to_netcdf.SandJ == 108


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

    def test_weather_download_2_5_km_section(self, prod_config):
        weather_download = prod_config["weather"]["download"]["2.5 km"]
        assert (
            weather_download["GRIB dir"]
            == "/results/forcing/atmospheric/continental2.5/GRIB/"
        )
        assert (
            weather_download["file template"]
            == "{date}T{forecast}Z_MSC_HRDPS_{variable}_RLatLon0.0225_PT{hour}H.grib2"
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
        assert weather_download["accumulation variables"] == [
            "solar",
            "therm_rad",
            "precip",
        ]
        assert weather_download["lon indices"] == [300, 490]
        assert weather_download["lat indices"] == [230, 460]

    def test_weather_section(self, prod_config):
        weather = prod_config["weather"]
        assert (
            weather["ops dir"]
            == "/results/forcing/atmospheric/continental2.5/nemo_forcing/"
        )
        assert weather["file template"] == "hrdps_{:y%Ym%md%d}.nc"
        assert (
            weather["monitoring image"]
            == "/results/nowcast-sys/figures/monitoring/wg.png"
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

    @staticmethod
    @pytest.fixture
    def mock_calc_nemo_var_ds(monkeypatch):
        def _mock_calc_nemo_var_ds(grib_var, nemo_var, grib_files, config):
            pass

        monkeypatch.setattr(grib_to_netcdf, "_calc_nemo_var_ds", _mock_calc_nemo_var_ds)

    @staticmethod
    @pytest.fixture
    def mock_combine_by_coords(monkeypatch):
        def _mock_combine_by_coords(data_objects, combine_attrs):
            return xarray.Dataset(
                data_vars={"var": ("x", numpy.array([], dtype=float))},
            )

        monkeypatch.setattr(
            grib_to_netcdf.xarray, "combine_by_coords", _mock_combine_by_coords
        )

    @staticmethod
    @pytest.fixture
    def mock_to_netcdf(monkeypatch):
        def _mock_to_netcdf(nemo_ds, encoding, nc_file_path):
            pass

        monkeypatch.setattr(grib_to_netcdf, "_to_netcdf", _mock_to_netcdf)

    @pytest.mark.parametrize("run_type", ("nowcast+", "forecast2"))
    def test_log_messages(
        self,
        run_type,
        mock_calc_nemo_var_ds,
        mock_combine_by_coords,
        mock_to_netcdf,
        config,
        caplog,
        monkeypatch,
    ):
        parsed_args = SimpleNamespace(
            run_date=arrow.get("2023-03-08"),
            run_type=run_type,
        )
        caplog.set_level(logging.DEBUG)

        grib_to_netcdf.grib_to_netcdf(parsed_args, config)

        assert caplog.records[0].levelname == "INFO"
        expected = f"creating NEMO-atmos forcing files for 2023-03-08 {run_type[:-1]}"
        assert caplog.messages[0].startswith(expected)

    def test_nowcast_checklist(
        self,
        mock_calc_nemo_var_ds,
        mock_combine_by_coords,
        mock_to_netcdf,
        config,
        caplog,
        monkeypatch,
    ):
        parsed_args = SimpleNamespace(
            run_date=arrow.get("2023-03-09"),
            run_type="nowcast+",
        )
        caplog.set_level(logging.DEBUG)

        checklist = grib_to_netcdf.grib_to_netcdf(parsed_args, config)

        expected = {"fcst": ["hrdps_y2023m03d10.nc"]}
        assert checklist == expected


class TestCalcGribFilePaths:
    """Unit test for _calc_grib_file_paths() function."""

    def test_calc_grib_file_paths(self, config):
        fcst_date = arrow.get("2023-03-08")
        fcst_hr = "12"
        fcst_step_range = (1, 2)
        msc_var = "UGRD_TGL_10"

        grib_files = grib_to_netcdf._calc_grib_file_paths(
            fcst_date, fcst_hr, fcst_step_range, msc_var, config
        )

        expected = [
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230308/12/001/20230308T12Z_MSC_HRDPS_UGRD_TGL_10_RLatLon0.0225_PT001H.grib2"
            ),
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230308/12/002/20230308T12Z_MSC_HRDPS_UGRD_TGL_10_RLatLon0.0225_PT002H.grib2"
            ),
        ]
        assert grib_files == expected


class TestTrimGrib:
    """Unit test for _trim_grib() function."""

    def test_trim_grib(self):
        # TODO: test something!
        pass


class TestCalcNemoVarDs:
    """Unit test for _calc_nemo_var_ds() function."""

    def test_calc_nemo_var_ds(self):
        # TODO: test something!
        pass


class TestApportionAccumulationVars:
    """Unit test for _apportion_accumulation_vars() function."""

    def test_apportion_accumulation_vars(self):
        # TODO: test something!
        pass


class TestWriteNetcdf:
    """Unit test for _write_netcdf() function."""

    def test_write_netcdf(self):
        # TODO: test something!
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
