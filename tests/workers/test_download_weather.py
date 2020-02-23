#  Copyright 2013-2020 The Salish Sea MEOPAR contributors
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
"""Unit tests for Salish Sea NEMO nowcast download_weather worker.
"""
import logging
from pathlib import Path
import textwrap
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import download_weather


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
                    2.5 km:
                      GRIB dir: /results/forcing/atmospheric/GEM2.5/GRIB/
                      url template: 'https://dd.weather.gc.ca/model_hrdps/west/grib2/{forecast}/{hour}/{filename}'
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
                      forecast duration: 48  # hours

                    1 km:
                      GRIB dir: /results/forcing/atmospheric/GEM1.0/GRIB/
                      url template: 'https://dd.alpha.meteo.gc.ca/model_hrdps/west/1km/grib2/{forecast}/{hour}/{filename}'
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
                      forecast duration: 36  # hours
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def parsed_args():
    return SimpleNamespace(forecast="06", resolution="2.5km", yesterday=False)


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(download_weather, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, mock_worker):
        worker = download_weather.main()
        assert worker.name == "download_weather"
        assert worker.description.startswith(
            "SalishSeaCast worker that downloads the GRIB2 files from today's 00, 06, 12, or 18"
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

    def test_add_yesterday_option(self, mock_worker):
        worker = download_weather.main()
        assert worker.cli.parser._actions[5].dest == "yesterday"
        assert worker.cli.parser._actions[5].default is False
        assert worker.cli.parser._actions[5].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

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
            weather_download["GRIB dir"] == "/results/forcing/atmospheric/GEM2.5/GRIB/"
        )
        assert (
            weather_download["url template"]
            == "https://dd.weather.gc.ca/model_hrdps/west/grib2/{forecast}/{hour}/{filename}"
        )
        assert (
            weather_download["file template"]
            == "CMC_hrdps_west_{variable}_ps2.5km_{date}{forecast}_P{hour}-00.grib2"
        )
        assert weather_download["forecast duration"] == 48
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
    "forecast, resolution, now, forecast_date",
    (
        ("00", "2.5km", "2020-02-10 03:58:43", "2020-02-10"),
        ("06", "2.5km", "2020-02-10 09:59:43", "2020-02-10"),
        ("12", "2.5km", "2020-02-10 15:56:43", "2020-02-10"),
        ("18", "2.5km", "2020-02-10 21:54:43", "2020-02-10"),
        ("00", "1km", "2020-02-10 03:58:43", "2020-02-10"),
        ("12", "1km", "2020-02-10 15:56:43", "2020-02-10"),
    ),
)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(
        self, forecast, resolution, now, forecast_date, caplog, monkeypatch
    ):
        def mock_now():
            return arrow.get(now)

        monkeypatch.setattr(download_weather.arrow, "now", mock_now)
        parsed_args = SimpleNamespace(
            forecast=forecast, resolution=resolution, yesterday=False
        )
        caplog.set_level(logging.INFO)

        msg_type = download_weather.success(parsed_args)
        assert caplog.records[0].levelname == "INFO"
        expected = f"{forecast_date} {resolution} weather forecast {forecast} downloads complete"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {resolution} {forecast}"

    def test_success_yesterday(
        self, forecast, resolution, now, forecast_date, caplog, monkeypatch
    ):
        def mock_now():
            return arrow.get(now)

        monkeypatch.setattr(download_weather.arrow, "now", mock_now)
        parsed_args = SimpleNamespace(
            forecast=forecast, resolution=resolution, yesterday=True
        )
        caplog.set_level(logging.INFO)

        msg_type = download_weather.success(parsed_args)
        assert caplog.records[0].levelname == "INFO"
        yesterday_date = arrow.get(forecast_date).shift(days=-1).format("YYYY-MM-DD")
        expected = f"{yesterday_date} {resolution} weather forecast {forecast} downloads complete"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {resolution} {forecast}"


@pytest.mark.parametrize(
    "forecast, resolution, now, forecast_date",
    (
        ("00", "1km", "2020-02-10 03:58:43", "2020-02-10"),
        ("12", "1km", "2020-02-10 15:56:43", "2020-02-10"),
        ("00", "2.5km", "2020-02-10 03:58:43", "2020-02-10"),
        ("06", "2.5km", "2020-02-10 09:59:43", "2020-02-10"),
        ("12", "2.5km", "2020-02-10 15:56:43", "2020-02-10"),
        ("18", "2.5km", "2020-02-10 21:54:43", "2020-02-10"),
    ),
)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(
        self, forecast, resolution, now, forecast_date, caplog, monkeypatch
    ):
        def mock_now():
            return arrow.get(now)

        monkeypatch.setattr(download_weather.arrow, "now", mock_now)
        parsed_args = SimpleNamespace(
            forecast=forecast, resolution=resolution, yesterday=False
        )
        caplog.set_level(logging.INFO)

        msg_type = download_weather.failure(parsed_args)
        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"{forecast_date} {resolution} weather forecast {parsed_args.forecast} downloads failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {resolution} {forecast}"

    def test_failure_yesterday(
        self, forecast, resolution, now, forecast_date, caplog, monkeypatch
    ):
        def mock_now():
            return arrow.get(now)

        monkeypatch.setattr(download_weather.arrow, "now", mock_now)
        parsed_args = SimpleNamespace(
            forecast=forecast, resolution=resolution, yesterday=True
        )
        caplog.set_level(logging.INFO)

        msg_type = download_weather.failure(parsed_args)
        assert caplog.records[0].levelname == "CRITICAL"
        yesterday_date = arrow.get(forecast_date).shift(days=-1).format("YYYY-MM-DD")
        expected = f"{yesterday_date} {resolution} weather forecast {parsed_args.forecast} downloads failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {resolution} {forecast}"


@pytest.mark.parametrize(
    "forecast, resolution",
    (
        ("00", "1km"),
        ("12", "1km"),
        ("00", "2.5km"),
        ("06", "2.5km"),
        ("12", "2.5km"),
        ("18", "2.5km"),
    ),
)
@patch("nowcast.workers.download_weather.logger", autospec=True)
@patch(
    "nowcast.workers.download_weather._calc_date",
    return_value="20150619",
    autospec=True,
)
@patch("nowcast.workers.download_weather.lib.mkdir", autospec=True)
@patch("nowcast.workers.download_weather.lib.fix_perms", autospec=True)
@patch("nowcast.workers.download_weather._get_file", autospec=True)
class TestGetGrib:
    """Unit tests for get_grib() function.
    """

    def test_make_hour_dirs(
        self,
        m_get_file,
        m_fix_perms,
        m_mkdir,
        m_calc_date,
        m_logger,
        forecast,
        resolution,
        config,
    ):
        parsed_args = SimpleNamespace(
            forecast=forecast, resolution=resolution, yesterday=False
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
                f"/results/forcing/atmospheric/GEM{float(resolution[:-2]):.1f}/GRIB/20150619/{forecast}/00{hr}",
                m_logger,
            )
            assert kwargs == {"grp_name": "allen", "exist_ok": False}

    @patch("nowcast.workers.download_weather.requests.Session", autospec=True)
    def test_get_grib_variable_file(
        self,
        m_session,
        m_get_file,
        m_fix_perms,
        m_mkdir,
        m_calc_date,
        m_logger,
        forecast,
        resolution,
        config,
    ):
        parsed_args = SimpleNamespace(
            forecast=forecast, resolution=resolution, yesterday=False
        )
        p_config = patch.dict(
            config["weather"]["download"][resolution.replace("km", " km")],
            {"grib variables": ["UGRD_TGL_10"], "forecast duration": 1},
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
            "UGRD_TGL_10",
            config["weather"]["download"][resolution.replace("km", " km")]["GRIB dir"],
            "20150619",
            forecast,
            "001",
            m_session().__enter__(),
        )
        assert kwargs == {}

    def test_fix_perms(
        self,
        m_get_file,
        m_fix_perms,
        m_mkdir,
        m_calc_date,
        m_logger,
        forecast,
        resolution,
        config,
    ):
        parsed_args = SimpleNamespace(
            forecast=forecast, resolution=resolution, yesterday=False
        )
        p_config = patch.dict(
            config["weather"]["download"][resolution.replace("km", " km")],
            {"grib variables": ["UGRD_TGL_10"], "forecast duration": 1},
        )
        m_get_file.return_value = "filepath"
        p_fix_perms = patch("nowcast.workers.download_weather.lib.fix_perms")
        with p_config, p_fix_perms as m_fix_perms:
            download_weather.get_grib(parsed_args, config)
        m_fix_perms.assert_called_once_with("filepath")

    def test_checklist(
        self,
        m_get_file,
        m_fix_perms,
        m_mkdir,
        m_calc_date,
        m_logger,
        forecast,
        resolution,
        config,
    ):
        parsed_args = SimpleNamespace(
            forecast=forecast, resolution=resolution, yesterday=False
        )
        checklist = download_weather.get_grib(parsed_args, config)

        expected = {
            f"{forecast} {resolution}": f"/results/forcing/atmospheric/GEM{float(resolution[:-2]):.1f}/GRIB/20150619/{forecast}"
        }
        assert checklist == expected


@patch(
    "nowcast.workers.download_weather.arrow.utcnow",
    return_value=arrow.get(2015, 6, 18, 19, 3, 42),
    autospec=True,
)
class TestCalcDate:
    """Unit tests for _calc_date() function.
    """

    def test_calc_date_06_forecast(self, m_utcnow, parsed_args):
        date = download_weather._calc_date(parsed_args, "06")
        assert date == "20150618"

    def test_calc_date_yesterday(self, m_utcnow, parsed_args):
        parsed_args.yesterday = True
        date = download_weather._calc_date(parsed_args, "06")
        assert date == "20150617"


@patch("nowcast.workers.download_weather.logger", autospec=True)
@patch("nowcast.workers.download_weather.lib.mkdir", autospec=True)
class TestMkdirs:
    """Unit tests for _mkdirs() function.
    """

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
    """Unit tests for _get_file() function.
    """

    @pytest.mark.parametrize("resolution", ("1 km", "2.5 km"))
    def test_get_web_data(self, m_stat, m_get_web_data, resolution, config, caplog):
        m_stat().st_size = 123_456
        caplog.set_level(logging.DEBUG)

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
        filename = config["weather"]["download"][resolution]["file template"].format(
            variable="UGRD_TGL_10", date="20150619", forecast="06", hour="001"
        )
        url = config["weather"]["download"][resolution]["url template"].format(
            forecast="06", hour="001", filename=filename
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
