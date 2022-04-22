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
"""Unit tests for Vancouver Harbour & Fraser River FVCOM make_fvcom_boundary
worker.
"""
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_fvcom_boundary


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
vhfr fvcom runs:
  run prep dir: fvcom-runs/

  fvcom grid:
    grid dir: FVCOM-VHFR-config/grid/
    utm zone: 10
    x2:
      grid file: vh_x2_grd.dat
      depths file: vh_x2_dep.dat
      sigma file: vh_x2_sigma.dat
    r12:
      grid file: vh_r12_grd.dat
      depths file: vh_r12_smp3_dep.dat
      sigma file: vh_r12_sigma.dat

  nemo coupling:
    coupling dir: FVCOM-VHFR-config/coupling_nemo_cut/
    x2:
      fvcom nest indices file: vh_x2_nesting_indices.txt
      fvcom nest ref line file: vh_x2_nesting_innerboundary.txt
    r12:
      fvcom nest indices file: vh_r12_nesting_indices.txt
      fvcom nest ref line file: vh_r12_nesting_innerboundary.txt
    nemo cut i range: [225, 369]
    nemo cut j range: [340, 561]
    transition zone width: 8500
    tanh dl: 2
    tanh du: 2
    nemo coordinates: grid/coordinates_seagrid_SalishSea201702.nc
    nemo mesh mask: grid/mesh_mask201702.nc
    nemo bathymetry: grid/bathymetry_201702.nc
    boundary file template: 'bdy_{model_config}_{run_type}_brcl_{yyyymmdd}.nc'

  input dir:
   x2: fvcom-runs/input.x2/
   r12: fvcom-runs/input.r12/

  run types:
    nowcast x2:
      nemo boundary results: SalishSea/nowcast/
    forecast x2:
      nemo boundary results: SalishSea/forecast/
    nowcast r12:
      nemo boundary results: SalishSea/nowcast/
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.make_fvcom_boundary.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_boundary.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_fvcom_boundary",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_boundary.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_model_config_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("model_config",)
        assert kwargs["choices"] == {"r12", "x2"}
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_boundary.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_fvcom_boundary.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_fvcom_boundary.make_fvcom_boundary,
            make_fvcom_boundary.success,
            make_fvcom_boundary.failure,
        )


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_fvcom_boundary" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["make_fvcom_boundary"]
        assert msg_registry["checklist key"] == "FVCOM boundary conditions"

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
        msg_registry = prod_config["message registry"]["workers"]["make_fvcom_boundary"]
        assert msg in msg_registry

    def test_input_dir(self, prod_config):
        input_dir = prod_config["vhfr fvcom runs"]["input dir"]
        assert input_dir["x2"] == "/nemoShare/MEOPAR/nowcast-sys/fvcom-runs/input.x2/"
        assert input_dir["r12"] == "/nemoShare/MEOPAR/nowcast-sys/fvcom-runs/input.r12/"

    def test_nemo_coupling_section(self, prod_config):
        nemo_coupling = prod_config["vhfr fvcom runs"]["nemo coupling"]
        assert (
            nemo_coupling["boundary file template"]
            == "bdy_{model_config}_{run_type}_brcl_{yyyymmdd}.nc"
        )
        assert (
            nemo_coupling["coupling dir"]
            == "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/coupling_nemo_cut/"
        )
        x2_nemo_coupling = nemo_coupling["x2"]
        assert (
            x2_nemo_coupling["fvcom nest indices file"] == "vh_x2_nesting_indices.txt"
        )
        assert (
            x2_nemo_coupling["fvcom nest ref line file"]
            == "vh_x2_nesting_innerboundary.txt"
        )
        r12_nemo_coupling = nemo_coupling["r12"]
        assert (
            r12_nemo_coupling["fvcom nest indices file"] == "vh_r12_nesting_indices.txt"
        )
        assert (
            r12_nemo_coupling["fvcom nest ref line file"]
            == "vh_r12_nesting_innerboundary.txt"
        )
        assert (
            nemo_coupling["nemo coordinates"]
            == "/nemoShare/MEOPAR/nowcast-sys/grid/coordinates_seagrid_SalishSea201702.nc"
        )
        assert (
            nemo_coupling["nemo mesh mask"]
            == "/nemoShare/MEOPAR/nowcast-sys/grid/mesh_mask201702.nc"
        )
        assert (
            nemo_coupling["nemo bathymetry"]
            == "/nemoShare/MEOPAR/nowcast-sys/grid/bathymetry_201702.nc"
        )
        assert nemo_coupling["nemo cut i range"] == [225, 369]
        assert nemo_coupling["nemo cut j range"] == [340, 561]
        assert nemo_coupling["transition zone width"] == 8500
        assert nemo_coupling["tanh dl"] == 2
        assert nemo_coupling["tanh du"] == 2

    def test_fvcom_grid_section(self, prod_config):
        fvcom_grid = prod_config["vhfr fvcom runs"]["fvcom grid"]
        assert (
            fvcom_grid["grid dir"]
            == "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/grid/"
        )
        assert fvcom_grid["utm zone"] == 10
        x2_grid = fvcom_grid["x2"]
        assert x2_grid["grid file"] == "vh_x2_grd.dat"
        assert x2_grid["depths file"] == "vh_x2_dep.dat"
        assert x2_grid["sigma file"] == "vh_x2_sigma.dat"
        r12_grid = fvcom_grid["r12"]
        assert r12_grid["grid file"] == "vh_r12_grd.dat"
        assert r12_grid["depths file"] == "vh_r12_smp3_dep.dat"
        assert r12_grid["sigma file"] == "vh_r12_sigma.dat"

    def test_run_types_section(self, prod_config):
        run_types = prod_config["vhfr fvcom runs"]["run types"]
        assert (
            run_types["nowcast x2"]["nemo boundary results"]
            == "/nemoShare/MEOPAR/SalishSea/nowcast/"
        )
        assert (
            run_types["nowcast r12"]["nemo boundary results"]
            == "/nemoShare/MEOPAR/SalishSea/nowcast/"
        )


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.make_fvcom_boundary.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success_log_info(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2017-11-29"),
        )
        msg_type = make_fvcom_boundary.success(parsed_args)
        assert msg_type == f"success {model_config} {run_type}"
        assert m_logger.info.called


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.make_fvcom_boundary.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure_log_error(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2017-11-29"),
        )
        msg_type = make_fvcom_boundary.failure(parsed_args)
        assert msg_type == f"failure {model_config} {run_type}"
        assert m_logger.critical.called


@patch("nowcast.workers.make_fvcom_boundary.logger", autospec=True)
@patch(
    "nowcast.workers.make_fvcom_boundary.OPPTools.nesting.read_metrics",
    return_value=tuple(
        "x y z tri nsiglev siglev nsiglay siglay nemo_lon nemo_lat "
        "e1t e2t e3u_0 e3v_0 gdept_0 gdepw_0 gdepu gdepv "
        "tmask umask vmask gdept_1d nemo_h".split()
    ),
    autospec=True,
)
@patch(
    "nowcast.workers.make_fvcom_boundary.OPPTools.nesting.read_nesting",
    return_value=tuple("inest xb yb".split()),
    autospec=True,
)
@patch(
    "nowcast.workers.make_fvcom_boundary.OPPTools.nesting.make_type3_nesting_file2",
    autospec=True,
)
class TestMakeFVCOMBoundary:
    """Unit tests for make_fvcom_boundary() function."""

    @pytest.mark.parametrize(
        "model_config, run_type, file_date",
        (
            ("x2", "nowcast", "20180108"),
            ("x2", "forecast", "20180109"),
            ("r12", "nowcast", "20180108"),
        ),
    )
    def test_checklist(
        self,
        m_mk_nest_file2,
        m_read_nesting,
        m_read_metrics,
        m_logger,
        model_config,
        run_type,
        file_date,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-01-08"),
        )
        with patch("nowcast.workers.make_fvcom_boundary.Path.mkdir"):
            checklist = make_fvcom_boundary.make_fvcom_boundary(parsed_args, config)
        input_dir = Path(config["vhfr fvcom runs"]["input dir"][model_config])
        expected = {
            run_type: {
                "run date": "2018-01-08",
                "model config": model_config,
                "open boundary file": os.fspath(
                    input_dir / f"bdy_{model_config}_{run_type}_brcl_{file_date}.nc"
                ),
            }
        }
        assert checklist == expected

    @pytest.mark.parametrize(
        "model_config, run_type, depths_file",
        (
            ("x2", "nowcast", "vh_x2_dep.dat"),
            ("x2", "forecast", "vh_x2_dep.dat"),
            ("r12", "nowcast", "vh_r12_smp3_dep.dat"),
        ),
    )
    def test_nesting_read_metrics(
        self,
        m_mk_nest_file2,
        m_read_nesting,
        m_read_metrics,
        m_logger,
        model_config,
        run_type,
        depths_file,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-01-08"),
        )
        with patch("nowcast.workers.make_fvcom_boundary.Path.mkdir"):
            make_fvcom_boundary.make_fvcom_boundary(parsed_args, config)
        grid_dir = Path(config["vhfr fvcom runs"]["fvcom grid"]["grid dir"])
        m_read_metrics.assert_called_once_with(
            fgrd=os.fspath(grid_dir / f"vh_{model_config}_grd.dat"),
            fbathy=os.fspath(grid_dir / depths_file),
            fsigma=os.fspath(grid_dir / f"vh_{model_config}_sigma.dat"),
            fnemocoord="grid/coordinates_seagrid_SalishSea201702.nc",
            fnemomask="grid/mesh_mask201702.nc",
            fnemobathy="grid/bathymetry_201702.nc",
            nemo_cut_i=[225, 369],
            nemo_cut_j=[340, 561],
        )

    @pytest.mark.parametrize(
        "model_config, run_type",
        (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
    )
    def test_nesting_read_nesting(
        self,
        m_mk_nest_file2,
        m_read_nesting,
        m_read_metrics,
        m_logger,
        model_config,
        run_type,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2018-04-25"),
        )
        with patch("nowcast.workers.make_fvcom_boundary.Path.mkdir"):
            make_fvcom_boundary.make_fvcom_boundary(parsed_args, config)
        coupling_dir = Path(config["vhfr fvcom runs"]["nemo coupling"]["coupling dir"])
        m_read_nesting.assert_called_once_with(
            fnest=os.fspath(coupling_dir / f"vh_{model_config}_nesting_indices.txt"),
            frefline=os.fspath(
                coupling_dir / f"vh_{model_config}_nesting_innerboundary.txt"
            ),
        )

    @pytest.mark.parametrize(
        "model_config, run_type, run_date, time_start, time_end, nemo_file_list",
        [
            (
                "x2",
                "nowcast",
                "2018-01-08",
                "2018-01-08 00:00:00",
                "2018-01-09 00:00:00",
                [
                    "SalishSea/nowcast/07jan18/FVCOM_T.nc",
                    "SalishSea/nowcast/08jan18/FVCOM_T.nc",
                ],
            ),
            (
                "x2",
                "forecast",
                "2018-01-08",
                "2018-01-09 00:00:00",
                "2018-01-10 12:00:00",
                [
                    "SalishSea/nowcast/07jan18/FVCOM_T.nc",
                    "SalishSea/nowcast/08jan18/FVCOM_T.nc",
                    "SalishSea/forecast/08jan18/FVCOM_T.nc",
                ],
            ),
            (
                "r12",
                "nowcast",
                "2019-02-14",
                "2019-02-14 00:00:00",
                "2019-02-15 00:00:00",
                [
                    "SalishSea/nowcast/13feb19/FVCOM_T.nc",
                    "SalishSea/nowcast/14feb19/FVCOM_T.nc",
                ],
            ),
        ],
    )
    def test_nesting_make_type3_nesting_file2(
        self,
        m_mk_nest_file2,
        m_read_nesting,
        m_read_metrics,
        m_logger,
        model_config,
        run_type,
        run_date,
        time_start,
        time_end,
        nemo_file_list,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get(run_date),
        )
        with patch("nowcast.workers.make_fvcom_boundary.Path.mkdir"):
            make_fvcom_boundary.make_fvcom_boundary(parsed_args, config)
        input_dir = Path(config["vhfr fvcom runs"]["input dir"][model_config])
        m_mk_nest_file2.assert_called_once_with(
            fout=os.fspath(
                input_dir
                / f'bdy_{model_config}_{run_type}_brcl_{arrow.get(time_start).format("YYYYMMDD")}.nc'
            ),
            x="x",
            y="y",
            z="z",
            tri="tri",
            nsiglev="nsiglev",
            siglev="siglev",
            nsiglay="nsiglay",
            siglay="siglay",
            utmzone=10,
            inest="inest",
            xb="xb",
            yb="yb",
            rwidth=8500,
            dl=2,
            du=2,
            nemo_lon="nemo_lon",
            nemo_lat="nemo_lat",
            e1t="e1t",
            e2t="e2t",
            e3u_0="e3u_0",
            e3v_0="e3v_0",
            nemo_file_list=nemo_file_list,
            time_start=time_start,
            time_end=time_end,
            opt="BRCL",
            gdept_0="gdept_0",
            gdepw_0="gdepw_0",
            gdepu="gdepu",
            gdepv="gdepv",
            tmask="tmask",
            umask="umask",
            vmask="vmask",
            u_name="uvelocity",
            v_name="vvelocity",
            w_name="wvelocity",
            t_name="cons_temp",
            s_name="ref_salinity",
        )
