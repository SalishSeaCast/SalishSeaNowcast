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


"""Unit tests for SalishSeaCast download_weather worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import download_weather


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
                      datamart dir: /SalishSeaCast/datamart/hrdps-continental/
                      GRIB dir: /results/forcing/atmospheric/continental2.5/GRIB/
                      url template: "https://hpfx.collab.science.gc.ca/{date}/WXO-DD/model_hrdps/continental/2.5km/{forecast}/{hour}/{filename}"
                      file template: "{date}T{forecast}Z_MSC_HRDPS_{variable}_RLatLon0.0225_PT{hour}H.grib2"
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
                        - TCDC_Sfc      # total cloud in percent (for parametrization of radiation missing from 2007-2014 GEMLAM)
                      forecast duration: 48  # hours

                    1 km:
                      GRIB dir: /results/forcing/atmospheric/GEM1.0/GRIB/
                      url template: "https://dd.alpha.meteo.gc.ca/model_hrdps/west/1km/grib2/{forecast}/{hour}/{filename}"
                      file template: "CMC_hrdps_west_{variable}_rotated_latlon0.009x0.009_{date}T{forecast}Z_P{hour}-00.grib2"
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
                      forecast duration: 36  # hours
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(download_weather, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = download_weather.main()
        assert worker.name == "download_weather"
        assert worker.description.startswith(
            "SalishSeaCast worker that downloads the GRIB2 files from the 00, 06, 12, or 18"
        )

    def test_add_forecast_arg(self, mock_worker):
        worker = download_weather.main()
        assert worker.cli.parser._actions[3].dest == "forecast"
        assert worker.cli.parser._actions[3].choices == {"00", "06", "12", "18"}
        assert worker.cli.parser._actions[3].help

    def test_add_resolution_arg(self, mock_worker):
        worker = download_weather.main()
        assert worker.cli.parser._actions[4].dest == "resolution"
        assert worker.cli.parser._actions[4].choices == {"1km", "2.5km"}
        assert worker.cli.parser._actions[4].default == "2.5km"
        assert worker.cli.parser._actions[4].help

    def test_add_data_date_option(self, mock_worker):
        worker = download_weather.main()
        assert worker.cli.parser._actions[5].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[5].type == expected
        assert worker.cli.parser._actions[5].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[5].help

    def test_add_verify_certs_option(self, mock_worker):
        worker = download_weather.main()
        assert worker.cli.parser._actions[6].dest == "no_verify_certs"
        assert worker.cli.parser._actions[6].default is False
        assert worker.cli.parser._actions[6].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "download_weather" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["download_weather"]
        assert msg_registry["checklist key"] == "weather forecast"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["download_weather"]
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
            weather_download["GRIB dir"]
            == "/results/forcing/atmospheric/continental2.5/GRIB/"
        )
        assert (
            weather_download["url template"]
            == "https://hpfx.collab.science.gc.ca/{date}/WXO-DD/model_hrdps/continental/2.5km/{forecast}/{hour}/{filename}"
        )
        assert (
            weather_download["file template"]
            == "{date}T{forecast}Z_MSC_HRDPS_{variable}_RLatLon0.0225_PT{hour}H.grib2"
        )
        assert weather_download["forecast duration"] == 48
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
            weather_download["GRIB dir"] == "/results/forcing/atmospheric/GEM1.0/GRIB/"
        )
        assert (
            weather_download["url template"]
            == "https://dd.alpha.meteo.gc.ca/model_hrdps/west/1km/grib2/{forecast}/{hour}/{filename}"
        )
        assert (
            weather_download["file template"]
            == "CMC_hrdps_west_{variable}_rotated_latlon0.009x0.009_{date}T{forecast}Z_P{hour}-00.grib2"
        )
        assert weather_download["forecast duration"] == 36
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


@pytest.mark.parametrize(
    "forecast, resolution, forecast_date",
    (
        ("00", "2.5km", "2020-02-10"),
        ("06", "2.5km", "2020-02-10"),
        ("12", "2.5km", "2020-02-10"),
        ("18", "2.5km", "2020-02-10"),
        ("00", "1km", "2020-02-10"),
        ("12", "1km", "2020-02-10"),
    ),
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, forecast, resolution, forecast_date, caplog, monkeypatch):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            resolution=resolution,
            run_date=forecast_date,
            no_verify_certs=False,
        )

        caplog.set_level(logging.DEBUG)

        msg_type = download_weather.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"{forecast_date} {resolution} weather forecast {forecast} downloads complete"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {resolution} {forecast}"


@pytest.mark.parametrize(
    "forecast, resolution, forecast_date",
    (
        ("00", "1km", "2020-02-10"),
        ("12", "1km", "2020-02-10"),
        ("00", "2.5km", "2020-02-10"),
        ("06", "2.5km", "2020-02-10"),
        ("12", "2.5km", "2020-02-10"),
        ("18", "2.5km", "2020-02-10"),
    ),
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, forecast, resolution, forecast_date, caplog, monkeypatch):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            resolution=resolution,
            run_date=forecast_date,
            no_verify_certs=False,
        )
        caplog.set_level(logging.DEBUG)

        msg_type = download_weather.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"{forecast_date} {resolution} weather forecast {parsed_args.forecast} downloads failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {resolution} {forecast}"


@patch("nowcast.workers.download_weather.logger", autospec=True)
@patch("nowcast.workers.download_weather.lib.mkdir", autospec=True)
@patch("nowcast.workers.download_weather.lib.fix_perms", autospec=True)
@patch("nowcast.workers.download_weather._get_file", autospec=True)
class TestGetGrib:
    """Unit tests for get_grib() function."""

    @pytest.mark.parametrize(
        "forecast, resolution",
        (
            ("00", "2.5km"),
            ("06", "2.5km"),
            ("12", "2.5km"),
            ("18", "2.5km"),
        ),
    )
    def test_make_hour_dirs_2_5km(
        self,
        m_get_file,
        m_fix_perms,
        m_mkdir,
        m_logger,
        forecast,
        resolution,
        config,
    ):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            resolution=resolution,
            run_date=arrow.get("2023-02-24"),
            no_verify_certs=False,
        )
        p_config = patch.dict(
            config["weather"]["download"][resolution.replace("km", " km")],
            {"forecast duration": 6},
        )
        with p_config:
            download_weather.get_grib(parsed_args, config)
        for hr in range(1, 7):
            args, kwargs = m_mkdir.call_args_list[hr + 1]
            assert args == (
                f"/results/forcing/atmospheric/continental{float(resolution[:-2]):.1f}/GRIB/20230224/{forecast}/00{hr}",
                m_logger,
            )
            assert kwargs == {"grp_name": "allen", "exist_ok": False}

    @pytest.mark.parametrize(
        "forecast, resolution",
        (
            ("00", "1km"),
            ("12", "1km"),
        ),
    )
    def test_make_hour_dirs_1km(
        self,
        m_get_file,
        m_fix_perms,
        m_mkdir,
        m_logger,
        forecast,
        resolution,
        config,
    ):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            resolution=resolution,
            run_date=arrow.get("2023-02-24"),
            no_verify_certs=False,
        )
        p_config = patch.dict(
            config["weather"]["download"][resolution.replace("km", " km")],
            {"forecast duration": 6},
        )
        with p_config:
            download_weather.get_grib(parsed_args, config)
        for hr in range(1, 7):
            args, kwargs = m_mkdir.call_args_list[hr + 1]
            assert args == (
                f"/results/forcing/atmospheric/GEM{float(resolution[:-2]):.1f}/GRIB/20230224/{forecast}/00{hr}",
                m_logger,
            )
            assert kwargs == {"grp_name": "allen", "exist_ok": False}

    @pytest.mark.parametrize(
        "forecast, resolution, variable",
        (
            ("00", "1km", "UGRD_TGL_10"),
            ("12", "1km", "UGRD_TGL_10"),
            ("00", "2.5km", "UGRD_AGL-10m"),
            ("06", "2.5km", "UGRD_AGL-10m"),
            ("12", "2.5km", "UGRD_AGL-10m"),
            ("18", "2.5km", "UGRD_AGL-10m"),
        ),
    )
    @patch("nowcast.workers.download_weather.requests.Session", autospec=True)
    def test_get_grib_variable_file(
        self,
        m_session,
        m_get_file,
        m_fix_perms,
        m_mkdir,
        m_logger,
        forecast,
        resolution,
        variable,
        config,
    ):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            resolution=resolution,
            run_date=arrow.get("2023-02-24"),
            no_verify_certs=False,
        )
        p_config = patch.dict(
            config["weather"]["download"][resolution.replace("km", " km")],
            {"grib variables": [variable], "forecast duration": 1},
        )
        with p_config:
            download_weather.get_grib(parsed_args, config)
        args, kwargs = m_get_file.call_args
        assert args == (
            config["weather"]["download"][resolution.replace("km", " km")][
                "url template"
            ],
            config["weather"]["download"][resolution.replace("km", " km")][
                "file template"
            ],
            variable,
            config["weather"]["download"][resolution.replace("km", " km")]["GRIB dir"],
            "20230224",
            forecast,
            "001",
            m_session().__enter__(),
        )
        assert kwargs == {}

    @pytest.mark.parametrize(
        "forecast, resolution, variable",
        (
            ("00", "1km", "UGRD_TGL_10"),
            ("12", "1km", "UGRD_TGL_10"),
            ("00", "2.5km", "UGRD_AGL-10m"),
            ("06", "2.5km", "UGRD_AGL-10m"),
            ("12", "2.5km", "UGRD_AGL-10m"),
            ("18", "2.5km", "UGRD_AGL-10m"),
        ),
    )
    def test_fix_perms(
        self,
        m_get_file,
        m_fix_perms,
        m_mkdir,
        m_logger,
        forecast,
        resolution,
        variable,
        config,
    ):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            resolution=resolution,
            run_date=arrow.get("2023-02-24"),
            no_verify_certs=False,
        )
        p_config = patch.dict(
            config["weather"]["download"][resolution.replace("km", " km")],
            {"grib variables": [variable], "forecast duration": 1},
        )
        m_get_file.return_value = "filepath"
        p_fix_perms = patch("nowcast.workers.download_weather.lib.fix_perms")
        with p_config, p_fix_perms as m_fix_perms:
            download_weather.get_grib(parsed_args, config)
        m_fix_perms.assert_called_once_with("filepath")

    @pytest.mark.parametrize(
        "forecast, resolution",
        (
            ("00", "2.5km"),
            ("06", "2.5km"),
            ("12", "2.5km"),
            ("18", "2.5km"),
        ),
    )
    def test_checklist_2_5km(
        self,
        m_get_file,
        m_fix_perms,
        m_mkdir,
        m_logger,
        forecast,
        resolution,
        config,
    ):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            resolution=resolution,
            run_date=arrow.get("2023-02-24"),
            no_verify_certs=False,
        )
        checklist = download_weather.get_grib(parsed_args, config)

        expected = {
            f"{forecast} {resolution}": f"/results/forcing/atmospheric/continental{float(resolution[:-2]):.1f}/GRIB/20230224/{forecast}"
        }
        assert checklist == expected

    @pytest.mark.parametrize(
        "forecast, resolution",
        (
            ("00", "1km"),
            ("12", "1km"),
        ),
    )
    def test_checklist_1km(
        self,
        m_get_file,
        m_fix_perms,
        m_mkdir,
        m_logger,
        forecast,
        resolution,
        config,
    ):
        parsed_args = SimpleNamespace(
            forecast=forecast,
            resolution=resolution,
            run_date=arrow.get("2023-02-24"),
            no_verify_certs=False,
        )
        checklist = download_weather.get_grib(parsed_args, config)

        expected = {
            f"{forecast} {resolution}": f"/results/forcing/atmospheric/GEM{float(resolution[:-2]):.1f}/GRIB/20230224/{forecast}"
        }
        assert checklist == expected


@patch("nowcast.workers.download_weather.logger", autospec=True)
@patch("nowcast.workers.download_weather.lib.mkdir", autospec=True)
class TestMkdirs:
    """Unit tests for _mkdirs() function."""

    def test_make_date_dir(self, m_mkdir, m_logger):
        download_weather._mkdirs("/tmp", "20150618", "06", "foo")
        args, kwargs = m_mkdir.call_args_list[0]
        assert args == ("/tmp/20150618", m_logger)
        assert kwargs == {"grp_name": "foo"}

    def test_make_forecast_dir(self, m_mkdir, m_logger):
        download_weather._mkdirs("/tmp", "20150618", "06", "foo")
        args, kwargs = m_mkdir.call_args_list[1]
        assert args == ("/tmp/20150618/06", m_logger)
        assert kwargs == {"grp_name": "foo", "exist_ok": False}


@patch("nowcast.workers.download_weather.get_web_data", autospec=True)
@patch("nowcast.workers.download_weather.os.stat", autospec=True)
class TestGetFile:
    """Unit tests for _get_file() function."""

    @pytest.mark.parametrize(
        "resolution, variable",
        (
            ("1 km", "UGRD_TGL_10"),
            ("2.5 km", "UGRD_AGL-10m"),
        ),
    )
    def test_get_web_data(
        self, m_stat, m_get_web_data, resolution, variable, config, caplog
    ):
        m_stat().st_size = 123_456
        caplog.set_level(logging.DEBUG)

        download_weather._get_file(
            config["weather"]["download"][resolution]["url template"],
            config["weather"]["download"][resolution]["file template"],
            variable,
            config["weather"]["download"][resolution]["GRIB dir"],
            "20150619",
            "06",
            "001",
            None,
        )
        filename = config["weather"]["download"][resolution]["file template"].format(
            variable=variable, date="20150619", forecast="06", hour="001"
        )
        url = config["weather"]["download"][resolution]["url template"].format(
            date="20150619", forecast="06", hour="001", filename=filename
        )
        filepath = Path(
            config["weather"]["download"][resolution]["GRIB dir"],
            "20150619",
            "06",
            "001",
            filename,
        )
        m_get_web_data.assert_called_once_with(
            url,
            "download_weather",
            Path(filepath),
            session=None,
            wait_exponential_max=9000,
        )
        assert caplog.records[0].levelname == "DEBUG"
        assert caplog.messages[0] == f"downloaded 123456 bytes from {url}"

    @pytest.mark.parametrize("resolution", ("1 km", "2.5 km"))
    def test_empty_file_exception(
        self, m_stat, m_get_web_data, resolution, config, caplog
    ):
        m_stat().st_size = 0
        caplog.set_level(logging.DEBUG)

        with pytest.raises(download_weather.WorkerError):
            download_weather._get_file(
                config["weather"]["download"][resolution]["url template"],
                config["weather"]["download"][resolution]["file template"],
                "UGRD_TGL_10",
                config["weather"]["download"][resolution]["GRIB dir"],
                "20150619",
                "06",
                "001",
                None,
            )
        assert caplog.records[0].levelname == "DEBUG"
        assert caplog.messages[0].startswith("downloaded 0 bytes from")
        assert caplog.records[1].levelname == "CRITICAL"
        assert caplog.messages[1].startswith("Problem! 0 size file:")
