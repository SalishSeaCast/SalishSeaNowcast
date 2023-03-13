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
        def _mock_combine_by_coords(data_objects, **kwargs):
            return xarray.Dataset(
                data_vars={"var": ("x", numpy.array([], dtype=float))},
            )

        monkeypatch.setattr(
            grib_to_netcdf.xarray, "combine_by_coords", _mock_combine_by_coords
        )

    @staticmethod
    @pytest.fixture
    def mock_calc_earth_ref_winds(monkeypatch):
        def _mock_calc_earth_ref_winds(nemo_ds):
            pass

        monkeypatch.setattr(
            grib_to_netcdf, "_calc_earth_ref_winds", _mock_calc_earth_ref_winds
        )

    @staticmethod
    @pytest.fixture
    def mock_apportion_accumulation_vars(monkeypatch):
        def _mock_apportion_accumulation_vars(nemo_ds, first_step_is_offset, config):
            return xarray.Dataset(
                data_vars={"var": ("x", numpy.array([], dtype=float))},
            )

        monkeypatch.setattr(
            grib_to_netcdf,
            "_apportion_accumulation_vars",
            _mock_apportion_accumulation_vars,
        )

    @staticmethod
    @pytest.fixture
    def mock_to_netcdf(monkeypatch):
        def _mock_to_netcdf(nemo_ds, encoding, nc_file_path):
            pass

        monkeypatch.setattr(grib_to_netcdf, "_to_netcdf", _mock_to_netcdf)

    @staticmethod
    @pytest.fixture
    def mock_improve_metadata(monkeypatch):
        def _mock_improve_metadata(nemo_ds, config):
            pass

        monkeypatch.setattr(grib_to_netcdf, "_improve_metadata", _mock_improve_metadata)

    @pytest.mark.parametrize("run_type", ("nowcast+", "forecast2"))
    def test_log_messages(
        self,
        run_type,
        mock_calc_nemo_var_ds,
        mock_combine_by_coords,
        mock_calc_earth_ref_winds,
        mock_apportion_accumulation_vars,
        mock_improve_metadata,
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
        mock_calc_earth_ref_winds,
        mock_apportion_accumulation_vars,
        mock_improve_metadata,
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

        expected = {
            "nowcast": "hrdps_y2023m03d09.nc",
            # "fcst": ["hrdps_y2023m03d10.nc"],
        }
        assert checklist == expected


class TestCalcNemoDs:
    """Unit test for _calc_nemo_ds() function."""

    def test_calc_nemo_ds(self):
        # TODO: test something!
        pass


class TestCalcGribFilePaths:
    """Unit tests for _calc_grib_file_paths() function."""

    def test_calc_grib_file_paths(self, config):
        fcst_date = arrow.get("2023-03-08")
        fcst_hr = "12"
        fcst_step_range = (1, 2)
        msc_var = "UGRD_AGL-10m"

        grib_files = grib_to_netcdf._calc_grib_file_paths(
            fcst_date, fcst_hr, fcst_step_range, msc_var, config
        )

        expected = [
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230308/12/001/20230308T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT001H.grib2"
            ),
            Path(
                "forcing/atmospheric/continental2.5/GRIB/20230308/12/002/20230308T12Z_MSC_HRDPS_UGRD_AGL-10m_RLatLon0.0225_PT002H.grib2"
            ),
        ]
        assert grib_files == expected

    def test_log_messages(self, config, caplog):
        fcst_date = arrow.get("2023-03-12")
        fcst_hr = "18"
        fcst_step_range = (5, 6)
        msc_var = "UGRD_AGL-10m"
        caplog.set_level(logging.DEBUG)

        grib_to_netcdf._calc_grib_file_paths(
            fcst_date, fcst_hr, fcst_step_range, msc_var, config
        )

        assert caplog.records[0].levelname == "DEBUG"
        expected = (
            f"creating {msc_var} GRIB file paths list for 20230312 18Z forecast hours "
            f"005 to 006"
        )
        assert caplog.messages[0] == expected


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


class TestCalcEarthRefWinds:
    """Unit test for _calc_earth_ref_winds() function."""

    def test_calc_earth_ref_winds(self):
        # TODO: test something!
        pass


class TestCalcGridAngle:
    """Units test for _calc_grid_angle() function."""

    @pytest.mark.parametrize(
        "direction, expected",
        (
            ("x", -45.00001432394728),
            ("y", -135.00001432394725),
        ),
    )
    def test_calc_grid_angle(self, direction, expected):
        lat1, lat2 = 0, -0.001
        lon1, lon2 = 0, 0.001

        angle = grib_to_netcdf._calc_grid_angle(lat1, lon1, lat2, lon2, direction)

        assert numpy.rad2deg(angle) == pytest.approx(expected)


@pytest.mark.parametrize("run_type", ("nowcast+",))
class TestImproveMetadata:
    """Unit test for _improve_metadata() function."""

    @staticmethod
    @pytest.fixture
    def nemo_ds():
        mock_var_da = xarray.DataArray(
            data=numpy.empty(shape=(1, 1, 1)),
            coords={
                "time_counter": ("time_counter", numpy.empty(shape=(1,))),
                "y": ("y", numpy.empty(shape=(1,))),
                "x": ("x", numpy.empty(shape=(1,))),
            },
        )
        return xarray.Dataset(
            data_vars={
                "nav_lon": xarray.DataArray(
                    data=numpy.empty(shape=(1, 1)),
                    coords={
                        "y": ("y", numpy.empty(shape=(1,))),
                        "x": ("x", numpy.empty(shape=(1,))),
                    },
                ),
                "nav_lat": xarray.DataArray(
                    data=numpy.empty(shape=(1, 1)),
                    coords={
                        "y": ("y", numpy.empty(shape=(1,))),
                        "x": ("x", numpy.empty(shape=(1,))),
                    },
                ),
                "LHTFL_surface": mock_var_da,
                "PRATE_surface": mock_var_da,
                "RH_2maboveground": mock_var_da,
                "atmpres": mock_var_da,
                "precip": mock_var_da,
                "qair": mock_var_da,
                "solar": mock_var_da,
                "tair": mock_var_da,
                "therm_rad": mock_var_da,
                "u_wind": mock_var_da,
                "v_wind": mock_var_da,
            },
            coords={
                "time_counter": ("time_counter", numpy.empty(shape=(1,))),
                "y": ("y", numpy.empty(shape=(1,))),
                "x": ("x", numpy.empty(shape=(1,))),
            },
            attrs={},
        )

    def test_time_counter_coord(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "axis": "T",
            "ioos_category": "Time",
            "long_name": "Time Axis",
            "standard_name": "time",
            "time_origin": "01-JAN-1970 00:00",
        }
        for key, value in expected.items():
            assert nemo_ds.time_counter.attrs[key] == value

    def test_y_coord(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "ioos_category": "location",
            "long_name": "Y",
            "standard_name": "y",
            "units": "count",
            "comment": (
                "Y values are grid indices in the model y-direction; "
                "geo-location data for the SalishSeaCast sub-domain of the ECCC MSC "
                "2.5km resolution HRDPS continental model grid is available in the "
                "ubcSSaSurfaceAtmosphereFieldsV22-02 dataset."
            ),
        }
        for key, value in expected.items():
            assert nemo_ds.y.attrs[key] == value

    def test_x_coord(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "ioos_category": "location",
            "long_name": "X",
            "standard_name": "x",
            "units": "count",
            "comment": (
                "X values are grid indices in the model x-direction; "
                "geo-location data for the SalishSeaCast sub-domain of the ECCC MSC "
                "2.5km resolution HRDPS continental model grid is available in the "
                "ubcSSaSurfaceAtmosphereFieldsV22-02 dataset."
            ),
        }
        for key, value in expected.items():
            assert nemo_ds.x.attrs[key] == value

    def test_nav_lon_var(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "ioos_category": "location",
            "long_name": "Longitude",
        }
        for key, value in expected.items():
            assert nemo_ds.nav_lon.attrs[key] == value

    def test_nav_lat_var(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "ioos_category": "location",
            "long_name": "Latitude",
        }
        for key, value in expected.items():
            assert nemo_ds.nav_lat.attrs[key] == value

    def test_all_atmospheric_vars(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "GRIB_numberOfPoints": "43700LL",
            "GRIB_Nx": "230LL",
            "GRIB_Ny": "190LL",
            "ioos_category": "atmospheric",
        }
        nemo_var_names = [
            name[2] for name in config["weather"]["download"]["2.5 km"]["variables"]
        ]
        for nemo_var in nemo_var_names:
            for key, value in expected.items():
                assert nemo_ds[nemo_var].attrs[key] == value

    def test_LHTFL_surface_var(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "standard_name": "surface_downward_latent_heat_flux",
            "units": "W m-2",
            "comment": "For Vancouver Harbour and Lower Fraser River FVCOM model",
        }
        for key, value in expected.items():
            assert nemo_ds.LHTFL_surface.attrs[key] == value

    def test_PRATE_surface_var(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "standard_name": "precipitation_flux",
            "units": "kg m-2 s-1",
            "comment": "For Vancouver Harbour and Lower Fraser River FVCOM model",
        }
        for key, value in expected.items():
            assert nemo_ds.PRATE_surface.attrs[key] == value

    def test_atmpres_var(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "standard_name": "air_pressure_at_mean_sea_level",
            "long_name": "Air Pressure at MSL",
            "units": "Pa",
        }
        for key, value in expected.items():
            assert nemo_ds.atmpres.attrs[key] == value

    def test_precip_var(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "standard_name": "precipitation_flux",
            "long_name": "Precipitation Flux",
            "units": "kg m-2 s-1",
        }
        for key, value in expected.items():
            assert nemo_ds.precip.attrs[key] == value

    def test_qair_var(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "standard_name": "specific_humidity",
            "long_name": "Specific Humidity at 2m",
            "units": "kg kg-1",
        }
        for key, value in expected.items():
            assert nemo_ds.qair.attrs[key] == value

    def test_solar_var(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "standard_name": "surface_downwelling_shortwave_flux_in_air",
            "long_name": "Downward Short-Wave (Solar) Radiation Flux",
            "units": "W m-2",
        }
        for key, value in expected.items():
            assert nemo_ds.solar.attrs[key] == value

    def test_tair_var(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "standard_name": "air_temperature",
            "long_name": "Air Temperature at 2m",
            "units": "K",
        }
        for key, value in expected.items():
            assert nemo_ds.tair.attrs[key] == value

    def test_therm_rad_var(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "standard_name": "surface_downwelling_longwave_flux_in_air",
            "long_name": "Downward Long-Wave (Thermal) Radiation Flux",
            "units": "W m-2",
        }
        for key, value in expected.items():
            assert nemo_ds.therm_rad.attrs[key] == value

    def test_u_wind_var(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "standard_name": "eastward_wind",
            "long_name": "U-Component of Wind at 10m",
            "units": "m s-1",
        }
        for key, value in expected.items():
            assert nemo_ds.u_wind.attrs[key] == value

    def test_v_wind_var(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "standard_name": "northward_wind",
            "long_name": "V-Component of Wind at 10m",
            "units": "m s-1",
        }
        for key, value in expected.items():
            assert nemo_ds.v_wind.attrs[key] == value

    def test_dataset_attrs(self, run_type, nemo_ds, config):
        grib_to_netcdf._improve_metadata(nemo_ds, config)

        expected = {
            "title": "HRDPS, Salish Sea, Atmospheric Forcing Fields, Hourly, v22-02",
            "project": "UBC EOAS SalishSeaCast",
            "institution": "UBC EOAS",
            "institution_fullname": "Earth, Ocean & Atmospheric Sciences, University of British Columbia",
            "creator_name": "SalishSeaCast Project Contributors",
            "creator_email": "sallen at eoas.ubc.ca",
            "creator_url": "https://salishsea.eos.ubc.ca",
            "drawLandMask": "over",
            "coverage_content_type": "modelResult",
        }
        for key, value in expected.items():
            assert nemo_ds.attrs[key] == value


class TestApportionAccumulationVars:
    """Unit test for _apportion_accumulation_vars() function."""

    def test_apportion_accumulation_vars(self):
        # TODO: test something!
        pass


class TestWriteNetcdf:
    """Unit tests for _write_netcdf() function."""

    @staticmethod
    @pytest.fixture
    def mock_to_netcdf(monkeypatch):
        def _mock_to_netcdf(nemo_ds, encoding, nc_file_path):
            pass

        monkeypatch.setattr(grib_to_netcdf, "_to_netcdf", _mock_to_netcdf)

    @pytest.mark.parametrize(
        "run_type, fcst",
        (
            ("nowcast+", False),
            ("forecast2", True),
        ),
    )
    def test_history_attr(self, run_type, fcst, config, mock_to_netcdf, monkeypatch):
        def mock_now(tz):
            return arrow.get("2023-03-12 16:02:43-07:00")

        monkeypatch.setattr(grib_to_netcdf.arrow, "now", mock_now)

        nemo_ds = xarray.Dataset()
        file_date = arrow.get("2023-03-12")
        run_date = arrow.get("2023-03-12")

        grib_to_netcdf._write_netcdf(
            nemo_ds, file_date, run_date, run_type, config, fcst
        )

        expected = (
            f"[Sun 2023-03-12 16:02:43 -07:00] "
            f"python3 -m nowcast.workers.grib_to_netcdf $NOWCAST_YAML "
            f"{run_type} --run-date 2023-03-12"
        )
        assert nemo_ds.attrs["history"] == expected


class TestUpdateChecklist:
    """Unit tests for _update_checklist() function."""

    def test_add_first_forecast(self):
        nc_file = Path("fcst/", "hrdps_y2023m03d09.nc")
        fcst = True
        checklist = {}

        grib_to_netcdf._update_checklist(nc_file, fcst, checklist)

        expected = {"fcst": ["hrdps_y2023m03d09.nc"]}
        assert checklist == expected

    def test_add_second_forecast(self):
        nc_file = Path("fcst/", "hrdps_y2023m03d10.nc")
        fcst = True
        checklist = {"fcst": ["hrdps_y2023m03d09.nc"]}

        grib_to_netcdf._update_checklist(nc_file, fcst, checklist)

        expected = {"fcst": ["hrdps_y2023m03d09.nc", "hrdps_y2023m03d10.nc"]}
        assert checklist == expected

    def test_add_nowcast(self):
        nc_file = Path("hrdps_y2023m03d08.nc")
        fcst = False
        checklist = {}

        grib_to_netcdf._update_checklist(nc_file, fcst, checklist)

        expected = {"nowcast": "hrdps_y2023m03d08.nc"}
        assert checklist == expected


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
