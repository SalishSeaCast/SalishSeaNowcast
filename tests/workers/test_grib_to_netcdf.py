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
"""Unit tests for Salish Sea NEMO nowcast grib_to_netcdf worker.
"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import pytest

from nowcast.workers import grib_to_netcdf


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    return base_config


@patch("nowcast.workers.grib_to_netcdf.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        grib_to_netcdf.main()
        args, kwargs = m_worker.call_args
        assert args == ("grib_to_netcdf",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        grib_to_netcdf.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        grib_to_netcdf.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast+", "forecast2"}
        assert "help" in kwargs

    def test_add_run_date_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        grib_to_netcdf.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        grib_to_netcdf.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            grib_to_netcdf.grib_to_netcdf,
            grib_to_netcdf.success,
            grib_to_netcdf.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

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
        assert "weather" in prod_config
        weather = prod_config["weather"]
        assert (
            weather["download"]["GRIB dir"]
            == "/results/forcing/atmospheric/GEM2.5/GRIB/"
        )
        assert (
            weather["wgrib2"] == "/data/sallen/MEOPAR/private-tools/grib2/wgrib2/wgrib2"
        )
        assert (
            weather["grid_defn.pl"]
            == "/SalishSeaCast/private-tools/PThupaki/grid_defn.pl"
        )
        assert weather["ops dir"] == "/results/forcing/atmospheric/GEM2.5/operational/"
        assert (
            weather["monitoring image"]
            == "/results/nowcast-sys/figures/monitoring/wg.png"
        )


@pytest.mark.parametrize("run_type", ["nowcast+", "forecast2"])
@patch("nowcast.workers.grib_to_netcdf.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2019-02-11")
        )
        msg_type = grib_to_netcdf.success(parsed_args)
        assert m_logger.info.called
        assert msg_type == "success {}".format(run_type)


@pytest.mark.parametrize("run_type", ["nowcast+", "forecast2"])
@patch("nowcast.workers.grib_to_netcdf.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(self, m_logger, run_type):
        parsed_args = SimpleNamespace(
            run_type=run_type, run_date=arrow.get("2019-02-11")
        )
        msg_type = grib_to_netcdf.failure(parsed_args)
        assert m_logger.critical.called
        assert msg_type == "failure {}".format(run_type)
