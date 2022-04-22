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
"""Unit tests for SalishSeaCast make_fvcom_rivers_forcing worker.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import numpy
import pytest

from nowcast.workers import make_fvcom_rivers_forcing


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
vhfr fvcom runs:
  fvcom grid:
    grid dir: FVCOM-VHFR-config/grid/
    x2:
      fraser nodes file: vh_x2_river_nodes_fraser.txt
    r12:
      fraser nodes file: vh_r12_river_nodes_fraser.txt

  nemo coupling:
    nemo coordinates: grid/coordinates_seagrid_SalishSea201702.nc

  rivers forcing:
    nemo rivers dir: rivers/
    runoff file template: R201702DFraCElse_{yyyymmdd}.nc
    temperature climatology: rivers-climatology/rivers_ConsTemp_month.nc
    rivers file template: 'rivers_{model_config}_{run_type}_{yyyymmdd}.nc'

  input dir:
   x2: fvcom-runs/input.x2/
   r12: fvcom-runs/input.r12/
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.make_fvcom_rivers_forcing.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_rivers_forcing.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_fvcom_rivers_forcing",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_rivers_forcing.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_rivers_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_model_config_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_rivers_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("model_config",)
        assert kwargs["choices"] == {"r12", "x2"}
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_rivers_forcing.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_rivers_forcing.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_rivers_forcing.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_fvcom_rivers_forcing.make_fvcom_rivers_forcing,
            make_fvcom_rivers_forcing.success,
            make_fvcom_rivers_forcing.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_fvcom_rivers_forcing" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"][
            "make_fvcom_rivers_forcing"
        ]
        assert msg_registry["checklist key"] == "FVCOM rivers forcing"

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
            "make_fvcom_rivers_forcing"
        ]
        assert msg in msg_registry

    def test_fvcom_grid_section(self, prod_config):
        fvcom_grid = prod_config["vhfr fvcom runs"]["fvcom grid"]
        assert (
            fvcom_grid["grid dir"]
            == "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/grid/"
        )
        x2_fvcom_grid = fvcom_grid["x2"]
        assert x2_fvcom_grid["fraser nodes file"] == "vh_x2_river_nodes_fraser.txt"
        r12_fvcom_grid = fvcom_grid["r12"]
        assert r12_fvcom_grid["fraser nodes file"] == "vh_r12_river_nodes_fraser.txt"

    def test_nemo_coupling_section(self, prod_config):
        nemo_coupling = prod_config["vhfr fvcom runs"]["nemo coupling"]
        assert (
            nemo_coupling["nemo coordinates"]
            == "/nemoShare/MEOPAR/nowcast-sys/grid/coordinates_seagrid_SalishSea201702.nc"
        )

    def test_rivers_forcing_section(self, prod_config):
        rivers_forcing = prod_config["vhfr fvcom runs"]["rivers forcing"]
        assert rivers_forcing["nemo rivers dir"] == "/nemoShare/MEOPAR/rivers/"
        assert (
            rivers_forcing["runoff file template"] == "R201702DFraCElse_{yyyymmdd}.nc"
        )
        assert (
            rivers_forcing["temperature climatology"]
            == "/nemoShare/MEOPAR/nowcast-sys/rivers-climatology/rivers_ConsTemp_month.nc"
        )
        assert (
            rivers_forcing["rivers file template"]
            == "rivers_{model_config}_{run_type}_{yyyymmdd}.nc"
        )

    def test_input_dir(self, prod_config):
        input_dir = prod_config["vhfr fvcom runs"]["input dir"]
        assert input_dir["x2"] == "/nemoShare/MEOPAR/nowcast-sys/fvcom-runs/input.x2/"
        assert input_dir["r12"] == "/nemoShare/MEOPAR/nowcast-sys/fvcom-runs/input.r12/"

    @pytest.mark.parametrize("model_config", ("x2", "r12"))
    def test_namelist_rivers(self, model_config, prod_config):
        assert (
            f"namelist.rivers.{model_config}"
            in prod_config["vhfr fvcom runs"]["namelists"][f"vh_{model_config}_run.nml"]
        )


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.make_fvcom_rivers_forcing.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success_log_info(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2019-01-30"),
        )
        msg_type = make_fvcom_rivers_forcing.success(parsed_args)
        assert msg_type == f"success {model_config} {run_type}"
        assert m_logger.info.called


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.make_fvcom_rivers_forcing.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure_log_error(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2019-01-30"),
        )
        msg_type = make_fvcom_rivers_forcing.failure(parsed_args)
        assert msg_type == f"failure {model_config} {run_type}"
        assert m_logger.critical.called


@patch("nowcast.workers.make_fvcom_rivers_forcing.logger", autospec=True)
@patch(
    "nowcast.workers.make_fvcom_rivers_forcing.OPPTools.river.nemo_fraser",
    autospec=True,
)
@patch("nowcast.workers.make_fvcom_rivers_forcing.numpy.genfromtxt", spec=True)
@patch(
    "nowcast.workers.make_fvcom_rivers_forcing.OPPTools.fvcomToolbox.generate_riv",
    autospec=True,
)
@patch(
    "nowcast.workers.make_fvcom_rivers_forcing.OPPTools.river.discharge_split", pec=True
)
@patch("nowcast.workers.make_fvcom_rivers_forcing.numpy.tile", spec=True)
class TestMakeFVCOMRiversForcing:
    """Unit tests for make_fvcom_rivers_forcing() function."""

    @pytest.mark.parametrize(
        "model_config, run_type, run_date, river_file_date",
        (
            ("x2", "nowcast", arrow.get("2019-01-30"), "20190130"),
            ("x2", "forecast", arrow.get("2019-01-30"), "20190131"),
            ("r12", "nowcast", arrow.get("2019-02-20"), "20190220"),
        ),
    )
    def test_checklist(
        self,
        m_tile,
        m_q_split,
        m_gen_riv,
        m_genfromtxt,
        m_nemo_fraser,
        m_logger,
        model_config,
        run_type,
        run_date,
        river_file_date,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=run_date,
        )
        m_nemo_fraser.return_value = (
            numpy.array(
                [run_date.shift(hours=-12).datetime, run_date.shift(days=+1).datetime]
            ),
            "discharge",
            numpy.array([2.5, 2.5]),
        )
        checklist = make_fvcom_rivers_forcing.make_fvcom_rivers_forcing(
            parsed_args, config
        )
        assert checklist == {
            run_type: {
                "run date": run_date.format("YYYY-MM-DD"),
                "model config": model_config,
                "rivers forcing file": f"fvcom-runs/input.{model_config}/rivers_{model_config}_{run_type}_{river_file_date}.nc",
            }
        }

    @pytest.mark.parametrize(
        "model_config, run_type, run_date, time_start, time_end",
        (
            (
                "x2",
                "nowcast",
                arrow.get("2019-01-30"),
                arrow.get("2019-01-30 00:00:00"),
                arrow.get("2019-01-31 00:00:00"),
            ),
            (
                "x2",
                "forecast",
                arrow.get("2019-01-30"),
                arrow.get("2019-01-31 00:00:00"),
                arrow.get("2019-02-01 12:00:00"),
            ),
            (
                "r12",
                "nowcast",
                arrow.get("2019-02-20"),
                arrow.get("2019-02-20 00:00:00"),
                arrow.get("2019-02-21 00:00:00"),
            ),
        ),
    )
    def test_nemo_fraser_call(
        self,
        m_tile,
        m_q_split,
        m_gen_riv,
        m_genfromtxt,
        m_nemo_fraser,
        m_logger,
        model_config,
        run_type,
        run_date,
        time_start,
        time_end,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=run_date,
        )
        m_nemo_fraser.return_value = (
            numpy.array(
                [run_date.shift(hours=-12).datetime, run_date.shift(days=+1).datetime]
            ),
            "discharge",
            numpy.array([2.5, 2.5]),
        )
        make_fvcom_rivers_forcing.make_fvcom_rivers_forcing(parsed_args, config)
        run_date_m1 = run_date.shift(days=-1)
        m_nemo_fraser.assert_called_once_with(
            (
                time_start.format("YYYY-MM-DD HH:mm:ss"),
                time_end.format("YYYY-MM-DD HH:mm:ss"),
            ),
            [
                f"rivers/R201702DFraCElse_y{run_date_m1.year:04d}m{run_date_m1.month:02d}d{run_date_m1.day:02d}.nc"
            ],
            config["vhfr fvcom runs"]["nemo coupling"]["nemo coordinates"],
            config["vhfr fvcom runs"]["rivers forcing"]["temperature climatology"],
        )

    @pytest.mark.parametrize(
        "model_config, run_type, run_date, river_file_date",
        (
            ("x2", "nowcast", arrow.get("2019-01-30"), "20190130"),
            ("x2", "forecast", arrow.get("2019-01-30"), "20190131"),
            ("r12", "nowcast", arrow.get("2019-02-20"), "20190220"),
        ),
    )
    def test_generate_riv_call(
        self,
        m_tile,
        m_q_split,
        m_gen_riv,
        m_genfromtxt,
        m_nemo_fraser,
        m_logger,
        model_config,
        run_type,
        run_date,
        river_file_date,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=run_date,
        )
        m_nemo_fraser.return_value = (
            numpy.array(
                [run_date.shift(hours=-12).datetime, run_date.shift(days=+1).datetime]
            ),
            "discharge",
            numpy.array([2.5, 2.5]),
        )
        make_fvcom_rivers_forcing.make_fvcom_rivers_forcing(parsed_args, config)
        m_gen_riv.assert_called_once_with(
            f"fvcom-runs/input.{model_config}/rivers_{model_config}_{run_type}_{river_file_date}.nc",
            [
                run_date.shift(hours=-12).format("YYYY-MM-DD HH:mm:ss"),
                run_date.shift(days=+1).format("YYYY-MM-DD HH:mm:ss"),
            ],
            m_genfromtxt(),
            m_q_split(),
            m_tile(),
            namelist_file=f"fvcom-runs/namelist.rivers.{model_config}",
            rivName="fraser",
        )
