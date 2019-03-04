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
"""Unit tests for Salish Sea NEMO nowcast download_weather worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

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
            """
file group: allen

weather:
  download:
    url template: 'http://dd.weather.gc.ca/model_hrdps/west/grib2/{forecast}/{hour}/{filename}'
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
    GRIB dir: /tmp/
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def parsed_args():
    return SimpleNamespace(forecast="06", yesterday=False)


@patch("nowcast.workers.download_weather.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_weather.main()
        args, kwargs = m_worker.call_args
        assert args == ("download_weather",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_weather.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_forecast_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_weather.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("forecast",)
        assert kwargs["choices"] == {"00", "06", "12", "18"}
        assert "help" in kwargs

    def test_add_yesterday_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_weather.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("--yesterday",)
        assert kwargs["action"] == "store_true"
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        download_weather.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            download_weather.get_grib,
            download_weather.success,
            download_weather.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "download_weather" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["download_weather"]
        assert msg_registry["checklist key"] == "weather forecast"

    @pytest.mark.parametrize(
        "msg",
        (
            "success 00",
            "failure 00",
            "success 06",
            "failure 06",
            "success 12",
            "failure 12",
            "success 18",
            "failure 18",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["download_weather"]
        assert msg in msg_registry

    def test_file_group(self, prod_config):
        assert "file group" in prod_config
        assert prod_config["file group"] == "sallen"

    def test_weather_download_section(self, prod_config):
        assert "weather" in prod_config
        assert "download" in prod_config["weather"]
        download = prod_config["weather"]["download"]
        assert download["GRIB dir"] == "/results/forcing/atmospheric/GEM2.5/GRIB/"
        assert (
            download["url template"]
            == "https://dd.weather.gc.ca/model_hrdps/west/grib2/{forecast}/{hour}/{filename}"
        )
        assert (
            download["file template"]
            == "CMC_hrdps_west_{variable}_ps2.5km_{date}{forecast}_P{hour}-00.grib2"
        )
        assert download["forecast duration"] == 48
        assert download["grib variables"] == [
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


@pytest.mark.parametrize("forecast", ["00", "06", "12", "18"])
@patch("nowcast.workers.download_weather.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(self, m_logger, forecast, parsed_args):
        parsed_args.forecast = forecast
        msg_type = download_weather.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == f"success {forecast}"


@pytest.mark.parametrize("forecast", ["00", "06", "12", "18"])
@patch("nowcast.workers.download_weather.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(self, m_logger, forecast, parsed_args):
        parsed_args.forecast = forecast
        msg_type = download_weather.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == f"failure {forecast}"


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
        parsed_args,
        config,
    ):
        p_config = patch.dict(config["weather"]["download"], {"forecast duration": 6})
        with p_config:
            download_weather.get_grib(parsed_args, config)
        for hr in range(1, 7):
            args, kwargs = m_mkdir.call_args_list[hr + 1]
            assert args == ("/tmp/20150619/06/00{}".format(hr), m_logger)
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
        parsed_args,
        config,
    ):
        p_config = patch.dict(
            config["weather"]["download"],
            {"grib variables": ["UGRD_TGL_10"], "forecast duration": 1},
        )
        with p_config:
            download_weather.get_grib(parsed_args, config)
        args, kwargs = m_get_file.call_args
        assert args == (
            config["weather"]["download"]["url template"],
            config["weather"]["download"]["file template"],
            "UGRD_TGL_10",
            "/tmp/",
            "20150619",
            "06",
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
        parsed_args,
        config,
    ):
        p_config = patch.dict(
            config["weather"]["download"],
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
        parsed_args,
        config,
    ):
        checklist = download_weather.get_grib(parsed_args, config)
        assert checklist == {"20150619 06 forecast": True}


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


@patch("nowcast.workers.download_weather.logger", autospec=True)
@patch("nowcast.workers.download_weather.get_web_data", autospec=True)
@patch("nowcast.workers.download_weather.os.stat", autospec=True)
class TestGetFile:
    """Unit tests for _get_file() function.
    """

    def test_get_web_data(self, m_stat, m_get_web_data, m_logger, config):
        m_stat().st_size = 123_456
        download_weather._get_file(
            config["weather"]["download"]["url template"],
            config["weather"]["download"]["file template"],
            "UGRD_TGL_10",
            "/tmp/",
            "20150619",
            "06",
            "001",
            None,
        )
        url = (
            "http://dd.weather.gc.ca/model_hrdps/west/grib2/06/001/"
            "CMC_hrdps_west_UGRD_TGL_10_ps2.5km_2015061906_P001-00.grib2"
        )
        filepath = (
            "/tmp/20150619/06/001/"
            "CMC_hrdps_west_UGRD_TGL_10_ps2.5km_2015061906_P001-00.grib2"
        )
        m_get_web_data.assert_called_once_with(
            url,
            "download_weather",
            Path(filepath),
            session=None,
            wait_exponential_max=9000,
        )

    def test_empty_file_exception(self, m_stat, m_get_web_data, m_logger, config):
        m_stat().st_size = 0
        with pytest.raises(download_weather.WorkerError):
            download_weather._get_file(
                config["weather"]["download"]["url template"],
                config["weather"]["download"]["file template"],
                "UGRD_TGL_10",
                "/tmp/",
                "20150619",
                "06",
                "001",
                None,
            )
