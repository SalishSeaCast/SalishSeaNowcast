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
"""Unit tests for Vancouver Harbour & Fraser River FVCOM
make_fvcom_atmos_forcing worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import numpy
import pytest

from nowcast.workers import make_fvcom_atmos_forcing


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
vhfr fvcom runs:
  fvcom grid:
    utm zone: 10
    x2:
      grid file: vhfr_x2_grd.dat
    r12:
      grid file: vhfr_r12_grd.dat
  atmospheric forcing:
    hrdps grib dir: forcing/atmospheric/GEM2.5/GRIB/
    fvcom atmos dir: forcing/atmospheric/GEM2.5/vhfr-fvcom
    atmos file template: 'atmos_{model_config}_{run_type}_{field_type}_{yyyymmdd}.nc'
    fvcom grid dir: nowcast-sys/FVCOM-VHFR-config/grid/
    field types:
      - hfx
      - precip
      - wnd
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.make_fvcom_atmos_forcing.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_atmos_forcing.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_fvcom_atmos_forcing",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_atmos_forcing.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_model_config_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("model_config",)
        assert kwargs["choices"] == {"r12", "x2"}
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_atmos_forcing.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_fvcom_atmos_forcing.make_fvcom_atmos_forcing,
            make_fvcom_atmos_forcing.success,
            make_fvcom_atmos_forcing.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_fvcom_atmos_forcing" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"][
            "make_fvcom_atmos_forcing"
        ]
        assert msg_registry["checklist key"] == "FVCOM atmospheric forcing"

    @pytest.mark.parametrize(
        "msg",
        (
            "success x2 nowcast",
            "failure x2 nowcast",
            "success r12 nowcast",
            "failure r12 nowcast",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "make_fvcom_atmos_forcing"
        ]
        assert msg in msg_registry

    def test_atmospheric_forcing_section(self, prod_config):
        assert "vhfr fvcom runs" in prod_config
        assert "atmospheric forcing" in prod_config["vhfr fvcom runs"]
        atmos_forcing = prod_config["vhfr fvcom runs"]["atmospheric forcing"]
        assert (
            atmos_forcing["hrdps grib dir"]
            == "/results/forcing/atmospheric/GEM2.5/GRIB/"
        )
        assert (
            atmos_forcing["fvcom atmos dir"]
            == "/results/forcing/atmospheric/GEM2.5/vhfr-fvcom"
        )
        assert (
            atmos_forcing["atmos file template"]
            == "atmos_{model_config}_{run_type}_{field_type}_{yyyymmdd}.nc"
        )
        assert (
            atmos_forcing["fvcom grid dir"] == "/SalishSeaCast/FVCOM-VHFR-config/grid/"
        )
        assert atmos_forcing["field types"] == ["hfx", "precip", "wnd"]

    def test_fvcom_grid_section(self, prod_config):
        assert "vhfr fvcom runs" in prod_config
        assert "fvcom grid" in prod_config["vhfr fvcom runs"]
        fvcom_grid = prod_config["vhfr fvcom runs"]["fvcom grid"]
        assert fvcom_grid["utm zone"] == 10
        x2_fvcom_grid = fvcom_grid["x2"]
        assert x2_fvcom_grid["grid file"] == "vh_x2_grd.dat"
        r12_fvcom_grid = fvcom_grid["r12"]
        assert r12_fvcom_grid["grid file"] == "vh_r12_grd.dat"


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.make_fvcom_atmos_forcing.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success_log_info(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-03-15"),
        )
        msg_type = make_fvcom_atmos_forcing.success(parsed_args)
        assert msg_type == f"success {model_config} {run_type}"
        assert m_logger.info.called


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.make_fvcom_atmos_forcing.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure_log_critical(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-03-15"),
        )
        msg_type = make_fvcom_atmos_forcing.failure(parsed_args)
        assert msg_type == f"failure {model_config} {run_type}"
        assert m_logger.critical.called


@patch("nowcast.workers.make_fvcom_atmos_forcing.logger", autospec=True)
@patch(
    "nowcast.workers.make_fvcom_atmos_forcing.OPPTools.fvcomToolbox.readMesh_V3",
    return_value=(numpy.ones((44157, 2)), numpy.ones((24476, 2))),
    autospec=True,
)
@patch(
    "nowcast.workers.make_fvcom_atmos_forcing.OPPTools.atm.create_atm_hrdps",
    autospec=True,
)
class TestMakeFVCOMAtmosForcing:
    """Unit tests for make_fvcom_atmos_forcing() function."""

    @pytest.mark.parametrize(
        "model_config, run_type, run_date, atmos_file_date",
        (
            ("x2", "nowcast", arrow.get("2018-12-07"), "20181207"),
            ("x2", "forecast", arrow.get("2018-12-07"), "20181208"),
            ("r12", "nowcast", arrow.get("2019-02-20"), "20190220"),
        ),
    )
    def test_checklist(
        self,
        m_create_atm_hrdps,
        m_readMesh,
        m_logger,
        model_config,
        run_type,
        run_date,
        atmos_file_date,
        config,
    ):
        parsed_args = SimpleNamespace(
            model_config=model_config, run_type=run_type, run_date=run_date
        )
        checklist = make_fvcom_atmos_forcing.make_fvcom_atmos_forcing(
            parsed_args, config
        )
        expected = {
            run_type: {
                "run date": run_date.format("YYYY-MM-DD"),
                "model config": model_config,
                "hfx": f"forcing/atmospheric/GEM2.5/vhfr-fvcom/atmos_{model_config}_{run_type}_hfx_{atmos_file_date}.nc",
                "precip": f"forcing/atmospheric/GEM2.5/vhfr-fvcom/atmos_{model_config}_{run_type}_precip_{atmos_file_date}.nc",
                "wnd": f"forcing/atmospheric/GEM2.5/vhfr-fvcom/atmos_{model_config}_{run_type}_wnd_{atmos_file_date}.nc",
            }
        }
        assert checklist == expected

    @pytest.mark.parametrize(
        "model_config, run_type",
        [("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")],
    )
    def test_readMesh_V3(
        self, m_create_atm_hrdps, m_readMesh, m_logger, model_config, run_type, config
    ):
        parsed_args = SimpleNamespace(
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-03-16"),
        )
        make_fvcom_atmos_forcing.make_fvcom_atmos_forcing(parsed_args, config)
        m_readMesh.assert_called_once_with(
            f"nowcast-sys/FVCOM-VHFR-config/grid/vhfr_{model_config}_grd.dat"
        )

    @pytest.mark.parametrize(
        "model_config, run_type, call_num, field_type, file_date, tlims",
        [
            (
                "x2",
                "nowcast",
                0,
                "hfx",
                "20181207",
                ("2018-12-07 00:00:00", "2018-12-08 00:00:00"),
            ),
            (
                "x2",
                "nowcast",
                1,
                "precip",
                "20181207",
                ("2018-12-07 00:00:00", "2018-12-08 00:00:00"),
            ),
            (
                "x2",
                "nowcast",
                2,
                "wnd",
                "20181207",
                ("2018-12-07 00:00:00", "2018-12-08 00:00:00"),
            ),
            (
                "x2",
                "forecast",
                0,
                "hfx",
                "20181208",
                ("2018-12-08 00:00:00", "2018-12-09 12:00:00"),
            ),
            (
                "x2",
                "forecast",
                1,
                "precip",
                "20181208",
                ("2018-12-08 00:00:00", "2018-12-09 12:00:00"),
            ),
            (
                "x2",
                "forecast",
                2,
                "wnd",
                "20181208",
                ("2018-12-08 00:00:00", "2018-12-09 12:00:00"),
            ),
            (
                "r12",
                "nowcast",
                0,
                "hfx",
                "20181207",
                ("2018-12-07 00:00:00", "2018-12-08 00:00:00"),
            ),
            (
                "r12",
                "nowcast",
                1,
                "precip",
                "20181207",
                ("2018-12-07 00:00:00", "2018-12-08 00:00:00"),
            ),
            (
                "r12",
                "nowcast",
                2,
                "wnd",
                "20181207",
                ("2018-12-07 00:00:00", "2018-12-08 00:00:00"),
            ),
        ],
    )
    def test_create_atm_hrdps(
        self,
        m_create_atm_hrdps,
        m_readMesh,
        m_logger,
        model_config,
        run_type,
        call_num,
        field_type,
        file_date,
        tlims,
        config,
    ):
        parsed_args = SimpleNamespace(
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-12-07"),
        )
        make_fvcom_atmos_forcing.make_fvcom_atmos_forcing(parsed_args, config)
        call_args = m_create_atm_hrdps.call_args_list[call_num]
        assert call_args[0][0] == field_type
        numpy.testing.assert_array_equal(call_args[0][2], numpy.ones((24476,)))
        numpy.testing.assert_array_equal(call_args[0][1], numpy.ones((24476,)))
        numpy.testing.assert_array_equal(call_args[0][3], numpy.ones((44157, 2)))
        assert call_args[1]["utmzone"] == 10
        assert call_args[1]["tlim"] == tlims
        expected = (
            f"forcing/atmospheric/GEM2.5/vhfr-fvcom/"
            f"atmos_{model_config}_{run_type}_{field_type}_{file_date}.nc"
        )
        assert call_args[1]["fname"] == expected
        expected = [
            "forcing/atmospheric/GEM2.5/GRIB/20181206/",
            "forcing/atmospheric/GEM2.5/GRIB/20181207/",
        ]
        assert call_args[1]["hrdps_folder"] == expected
