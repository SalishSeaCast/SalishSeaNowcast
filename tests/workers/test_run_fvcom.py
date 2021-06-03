#  Copyright 2013-2021 The Salish Sea MEOPAR contributors
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
"""Unit tests for Vancouver Harbour & Fraser River FVCOM run_fvcom worker.
"""
import os
import subprocess
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import run_fvcom


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            """
vhfr fvcom runs:
  case name:
    x2: vh_x2
    r12: vh_r12
  run prep dir: fvcom-runs/

  fvcom grid:
    grid dir: FVCOM-VHFR-config/grid/
    x2:
      grid file: vh_x2_grd.dat
      depths file: vh_x2_dep.dat
      sigma file: vh_x2_sigma.dat
      coriolis file: vh_x2_cor.dat
      sponge file: vh_x2_nospg_spg.dat
      obc nodes file: vh_x2_obc.dat
    r12:
      grid file: vh_r12_grd.dat
      depths file: vh_r12_smp3_dep.dat
      sigma file: vh_r12_sigma.dat
      coriolis file: vh_r12_cor.dat
      sponge file: vh_r12_nospg_spg.dat
      obc nodes file: vh_r12_obc.dat

  nemo coupling:
    boundary file template: 'bdy_{model_config}_{run_type}_brcl_{yyyymmdd}.nc'

  atmospheric forcing:
    atmos file template: 'atmos_{model_config}_{run_type}_{field_type}_{yyyymmdd}.nc'
    field types:
      - hfx
      - precip
      - wnd

  rivers forcing:
    rivers file template: 'rivers_{model_config}_{run_type}_{yyyymmdd}.nc'

  input dir:
   x2: fvcom-runs/input.x2/
   r12: fvcom-runs/input.r12/

  output station timeseries:
    x2:
      FVCOM-VHFR-config/output/vh_x2_station.txt
    r12:
      FVCOM-VHFR-config/output/vh_r12_station.txt

  namelists:
    'vh_x2_run.nml':
      - namelist.case
      - namelist.startup.hotstart
      - namelist.numerics
      - namelist.restart
      - namelist.netcdf
      - namelist.physics
      - namelist.surface
      - namelist.rivers.x2
      - namelist.obc
      - namelist.grid
      - namelist.nesting
      - namelist.station_timeseries
    'vh_r12_run.nml':
      - namelist.case
      - namelist.startup.hotstart
      - namelist.numerics
      - namelist.restart
      - namelist.netcdf
      - namelist.physics
      - namelist.surface
      - namelist.rivers.r12
      - namelist.obc
      - namelist.grid
      - namelist.nesting
      - namelist.station_timeseries

  number of processors:
   x2: 28
   r12: 84

  mpi hosts file:
   x2: ${HOME}/mpi_hosts.fvcom.x2
   r12: ${HOME}/mpi_hosts.fvcom.r12

  fvc_cmd: bin/fvc

  run types:
    nowcast x2:
      time step: 0.5
      results: SalishSea/fvcom-nowcast-x2/
    forecast x2:
      time step: 0.5
      results: SalishSea/fvcom-forecast-x2/
    nowcast r12:
      time step: 0.2
      results: SalishSea/fvcom-nowcast-r12/
"""
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@patch("nowcast.workers.run_fvcom.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        args, kwargs = m_worker.call_args
        assert args == ("run_fvcom",)
        assert list(kwargs.keys()) == ["description"]

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_host_name_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[0]
        assert args == ("host_name",)
        assert "help" in kwargs

    def test_add_model_config_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[1]
        assert args == ("model_config",)
        assert kwargs["choices"] == {"r12", "x2"}
        assert "help" in kwargs

    def test_add_run_type_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        args, kwargs = m_worker().cli.add_argument.call_args_list[2]
        assert args == ("run_type",)
        assert kwargs["choices"] == {"nowcast", "forecast"}
        assert "help" in kwargs

    def test_add_run_date_option(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        run_fvcom.main()
        args, kwargs = m_worker().run.call_args
        assert args == (run_fvcom.run_fvcom, run_fvcom.success, run_fvcom.failure)


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "run_fvcom" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["run_fvcom"]
        assert msg_registry["checklist key"] == "FVCOM run"

    @pytest.mark.parametrize(
        "msg",
        (
            "success x2 nowcast",
            "failure x2 nowcast",
            "success x2 forecast",
            "failure x2 forecast",
            "success r12 nowcast",
            "failure r12 nowcast",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["run_fvcom"]
        assert msg in msg_registry

    def test_vhfr_fvcom_runs_section(self, prod_config):
        assert "vhfr fvcom runs" in prod_config
        vhfr_fvcom_runs = prod_config["vhfr fvcom runs"]
        assert vhfr_fvcom_runs["host"] == "arbutus.cloud-nowcast"
        assert vhfr_fvcom_runs["ssh key"] == "SalishSeaNEMO-nowcast_id_rsa"
        assert vhfr_fvcom_runs["case name"]["x2"] == "vh_x2"
        assert vhfr_fvcom_runs["case name"]["r12"] == "vh_r12"
        assert (
            vhfr_fvcom_runs["run prep dir"]
            == "/nemoShare/MEOPAR/nowcast-sys/fvcom-runs/"
        )
        assert "fvcom grid" in vhfr_fvcom_runs
        assert "nemo coupling" in vhfr_fvcom_runs
        assert "atmospheric forcing" in vhfr_fvcom_runs
        input_dir = prod_config["vhfr fvcom runs"]["input dir"]
        assert input_dir["x2"] == "/nemoShare/MEOPAR/nowcast-sys/fvcom-runs/input.x2/"
        assert input_dir["r12"] == "/nemoShare/MEOPAR/nowcast-sys/fvcom-runs/input.r12/"
        assert (
            vhfr_fvcom_runs["output station timeseries"]["x2"]
            == "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/output/vh_x2_station.txt"
        )
        assert (
            vhfr_fvcom_runs["output station timeseries"]["r12"]
            == "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/output/vh_r12_station.txt"
        )
        assert "namelists" in vhfr_fvcom_runs
        assert (
            vhfr_fvcom_runs["FVCOM exe path"]
            == "/nemoShare/MEOPAR/nowcast-sys/FVCOM41/"
        )
        assert vhfr_fvcom_runs["number of processors"]["x2"] == 30
        assert vhfr_fvcom_runs["number of processors"]["r12"] == 90
        assert vhfr_fvcom_runs["mpi hosts file"]["x2"] == "${HOME}/mpi_hosts.fvcom.x2"
        assert vhfr_fvcom_runs["mpi hosts file"]["r12"] == "${HOME}/mpi_hosts.fvcom.r12"
        assert (
            vhfr_fvcom_runs["fvc_cmd"]
            == "/nemoShare/MEOPAR/nowcast-sys/nowcast-env/bin/fvc"
        )
        assert "run types" in vhfr_fvcom_runs
        assert "results archive" in vhfr_fvcom_runs
        assert (
            vhfr_fvcom_runs["stations dataset filename"]["x2"]
            == "vh_x2_station_timeseries.nc"
        )
        assert (
            vhfr_fvcom_runs["stations dataset filename"]["r12"]
            == "vh_r12_station_timeseries.nc"
        )

    def test_fvcom_grid_section(self, prod_config):
        fvcom_grid = prod_config["vhfr fvcom runs"]["fvcom grid"]
        assert (
            fvcom_grid["grid dir"]
            == "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/grid/"
        )
        x2_grid = fvcom_grid["x2"]
        assert x2_grid["grid file"] == "vh_x2_grd.dat"
        assert x2_grid["depths file"] == "vh_x2_dep.dat"
        assert x2_grid["sigma file"] == "vh_x2_sigma.dat"
        assert x2_grid["coriolis file"] == "vh_x2_cor.dat"
        assert x2_grid["sponge file"] == "vh_x2_nospg_spg.dat"
        assert x2_grid["obc nodes file"] == "vh_x2_obc.dat"
        r12_grid = fvcom_grid["r12"]
        assert r12_grid["grid file"] == "vh_r12_grd.dat"
        assert r12_grid["depths file"] == "vh_r12_smp3_dep.dat"
        assert r12_grid["sigma file"] == "vh_r12_sigma.dat"
        assert r12_grid["coriolis file"] == "vh_r12_cor.dat"
        assert r12_grid["sponge file"] == "vh_r12_nospg_spg.dat"
        assert r12_grid["obc nodes file"] == "vh_r12_obc.dat"

    def test_nemo_coupling_section(self, prod_config):
        nemo_coupling = prod_config["vhfr fvcom runs"]["nemo coupling"]
        assert (
            nemo_coupling["boundary file template"]
            == "bdy_{model_config}_{run_type}_brcl_{yyyymmdd}.nc"
        )

    def test_atmospheric_forcing_section(self, prod_config):
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

    def test_rivers_forcing_section(self, prod_config):
        rivers_forcing = prod_config["vhfr fvcom runs"]["rivers forcing"]
        assert (
            rivers_forcing["rivers file template"]
            == "rivers_{model_config}_{run_type}_{yyyymmdd}.nc"
        )

    def test_namelists_section(self, prod_config):
        namelists = prod_config["vhfr fvcom runs"]["namelists"]["vh_x2_run.nml"]
        assert namelists == [
            "namelist.case",
            "namelist.startup.hotstart",
            "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.io",
            "namelist.numerics",
            "namelist.restart",
            "namelist.netcdf",
            "namelist.physics",
            "namelist.surface",
            "namelist.rivers.x2",
            "namelist.obc",
            "namelist.grid",
            "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.groundwater",
            "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.lagrangian",
            "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.probes",
            "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.bounds_check",
            "namelist.nesting",
            "namelist.station_timeseries",
            "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.additional_models",
        ]
        namelists = prod_config["vhfr fvcom runs"]["namelists"]["vh_r12_run.nml"]
        assert namelists == [
            "namelist.case",
            "namelist.startup.hotstart",
            "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.io",
            "namelist.numerics",
            "namelist.restart",
            "namelist.netcdf",
            "namelist.physics",
            "namelist.surface",
            "namelist.rivers.r12",
            "namelist.obc",
            "namelist.grid",
            "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.groundwater",
            "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.lagrangian",
            "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.probes",
            "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.bounds_check",
            "namelist.nesting",
            "namelist.station_timeseries",
            "/nemoShare/MEOPAR/nowcast-sys/FVCOM-VHFR-config/namelists/namelist.additional_models",
        ]

    def test_run_types_section(self, prod_config):
        run_types = prod_config["vhfr fvcom runs"]["run types"]
        assert run_types["nowcast x2"] == {
            "nemo boundary results": "/nemoShare/MEOPAR/SalishSea/nowcast/",
            "time step": 0.5,
            "results": "/nemoShare/MEOPAR/SalishSea/fvcom-nowcast-x2/",
        }
        assert run_types["forecast x2"] == {
            "nemo boundary results": "/nemoShare/MEOPAR/SalishSea/forecast/",
            "time step": 0.5,
            "results": "/nemoShare/MEOPAR/SalishSea/fvcom-forecast-x2/",
        }
        assert run_types["nowcast r12"] == {
            "nemo boundary results": "/nemoShare/MEOPAR/SalishSea/nowcast/",
            "time step": 0.2,
            "results": "/nemoShare/MEOPAR/SalishSea/fvcom-nowcast-r12/",
        }

    def test_results_archive_section(self, prod_config):
        results_archive = prod_config["vhfr fvcom runs"]["results archive"]
        assert results_archive["nowcast x2"] == "/opp/fvcom/nowcast-x2/"
        assert results_archive["forecast x2"] == "/opp/fvcom/forecast-x2/"
        assert results_archive["nowcast r12"] == "/opp/fvcom/nowcast-r12/"


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2017-11-29"),
        )
        msg_type = run_fvcom.success(parsed_args)
        assert msg_type == f"success {model_config} {run_type}"
        assert m_logger.info.called


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, m_logger, model_config, run_type):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=arrow.get("2017-11-29"),
        )
        msg_type = run_fvcom.failure(parsed_args)
        assert msg_type == f"failure {model_config} {run_type}"
        assert m_logger.critical.called


@pytest.mark.parametrize(
    "model_config, run_type, run_date",
    (
        ("x2", "nowcast", arrow.get("2017-11-29")),
        ("x2", "forecast", arrow.get("2017-11-29")),
        ("r12", "nowcast", arrow.get("2019-02-21")),
    ),
)
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
@patch("nowcast.workers.run_fvcom._create_run_desc_file")
@patch("nowcast.workers.run_fvcom.fvcom_cmd.api.prepare")
@patch("nowcast.workers.run_fvcom._prep_fvcom_input_dir")
@patch("nowcast.workers.run_fvcom.shutil.copy2", autospec=True)
@patch("nowcast.workers.run_fvcom._create_run_script")
@patch("nowcast.workers.run_fvcom._launch_run_script")
class TestRunFVCOM:
    """Unit tests for run_fvcom() function."""

    def test_checklist(
        self,
        m_launch,
        m_crs,
        m_copy2,
        m_pfid,
        m_prep,
        m_crdf,
        m_logger,
        model_config,
        run_type,
        run_date,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            model_config=model_config,
            run_type=run_type,
            run_date=run_date,
        )
        tmp_run_dir = f"fvcom-runs/{run_date.format('DDMMMYY').lower()}vhfr-{run_type}_{run_date.format('YYYY-MM-DD')}T183043.555919-0700"
        m_prep.return_value = tmp_run_dir
        checklist = run_fvcom.run_fvcom(parsed_args, config)
        expected = {
            f"{model_config} {run_type}": {
                "host": "arbutus.cloud",
                "run dir": tmp_run_dir,
                "run exec cmd": m_launch(),
                "model config": model_config,
                "run date": run_date.format("YYYY-MM-DD"),
            }
        }
        assert checklist == expected


@pytest.mark.parametrize(
    "model_config, run_type, run_date",
    (
        ("x2", "nowcast", arrow.get("2017-12-11")),
        ("x2", "forecast", arrow.get("2017-12-11")),
        ("r12", "nowcast", arrow.get("2019-02-21")),
    ),
)
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
@patch("nowcast.workers.run_fvcom.yaml.safe_dump", autospec=True)
@patch("nowcast.workers.run_fvcom._run_description")
class TestCreateRunDescFile:
    """Unit tests for _create_fun_desc_file() function."""

    def test_run_desc_file_path(
        self,
        m_run_desc,
        m_yaml_dump,
        m_logger,
        model_config,
        run_type,
        run_date,
        config,
    ):
        with patch("nowcast.workers.run_fvcom.Path.open") as m_open:
            run_desc_file_path = run_fvcom._create_run_desc_file(
                run_date, model_config, run_type, config
            )
        expected = Path(
            f"fvcom-runs/{run_date.format('DDMMMYY').lower()}fvcom-{model_config}-{run_type}.yaml"
        )
        assert run_desc_file_path == expected

    def test_run_desc_yaml_dump(
        self,
        m_run_desc,
        m_yaml_dump,
        m_logger,
        model_config,
        run_type,
        run_date,
        config,
        tmpdir,
    ):
        run_prep_dir = Path(str(tmpdir.ensure_dir("nowcast-sys/fvcom-runs")))
        with patch("nowcast.workers.run_fvcom.Path.open") as m_open:
            run_desc_file_path = run_fvcom._create_run_desc_file(
                run_date, model_config, run_type, config
            )
            m_yaml_dump.assert_called_once_with(
                m_run_desc(), m_open().__enter__(), default_flow_style=False
            )


@pytest.mark.parametrize(
    "model_config, run_type, run_date",
    (
        ("x2", "nowcast", arrow.get("2017-12-11")),
        ("x2", "forecast", arrow.get("2017-12-11")),
        ("r12", "nowcast", arrow.get("2019-02-21")),
    ),
)
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
@patch("nowcast.workers.run_fvcom._edit_namelists")
@patch("nowcast.workers.run_fvcom._assemble_namelist")
class TestRunDescription:
    """Unit test for _run_description() function."""

    def test_run_desc(
        self,
        m_mk_nml,
        m_edit_nml,
        m_logger,
        model_config,
        run_type,
        run_date,
        config,
        tmpdir,
    ):
        run_id = f"{run_date.format('DDMMMYY').lower()}fvcom-{run_type}"
        fvcom_repo_dir = Path(str(tmpdir.ensure_dir("FVCOM41")))
        run_prep_dir = Path(str(tmpdir.ensure_dir("fvcom-runs")))
        m_mk_nml.return_value = Path(str(run_prep_dir), f"vh_{model_config}_run.nml")
        p_config = patch.dict(
            config["vhfr fvcom runs"],
            {"run prep dir": run_prep_dir, "FVCOM exe path": fvcom_repo_dir},
        )
        with p_config:
            run_desc = run_fvcom._run_description(
                run_id, run_date, model_config, run_type, run_prep_dir, config
            )
        expected = {
            "run_id": run_id,
            "casename": config["vhfr fvcom runs"]["case name"][model_config],
            "nproc": config["vhfr fvcom runs"]["number of processors"][model_config],
            "paths": {
                "FVCOM": os.fspath(fvcom_repo_dir),
                "runs directory": os.fspath(run_prep_dir),
                "input": os.fspath(run_prep_dir / f"input.{model_config}"),
            },
            "namelist": os.fspath(run_prep_dir / f"vh_{model_config}_run.nml"),
        }
        assert run_desc == expected


@patch("nowcast.workers.run_fvcom.logger", autospec=True)
@patch("nowcast.workers.run_fvcom._patch_namelist")
class TestEditNamelists:
    """Unit test for _edit_namelists() function."""

    @pytest.mark.parametrize(
        "model_config, run_type, run_date, time_step",
        (
            ("x2", "nowcast", arrow.get("2018-01-15"), 0.5),
            ("r12", "nowcast", arrow.get("2019-02-21"), 0.2),
        ),
    )
    def test_edit_namelists_nowcast(
        self, m_patch_nml, m_logger, model_config, run_type, run_date, time_step, config
    ):
        run_fvcom._edit_namelists(
            config["vhfr fvcom runs"]["case name"][model_config],
            run_date,
            model_config,
            run_type,
            Path("run_prep_dir"),
            config,
        )
        assert m_patch_nml.call_args_list == [
            call(
                Path("run_prep_dir/namelist.case"),
                {
                    "nml_case": {
                        "case_title": config["vhfr fvcom runs"]["case name"][
                            model_config
                        ],
                        "start_date": f"{run_date.format('YYYY-MM-DD')} 00:00:00.00",
                        "end_date": f"{run_date.shift(days=+1).format('YYYY-MM-DD')} 00:00:00.00",
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.startup.hotstart"),
                {"nml_startup": {"startup_file": f"vh_{model_config}_restart_0001.nc"}},
            ),
            call(
                Path("run_prep_dir/namelist.numerics"),
                {"nml_integration": {"extstep_seconds": time_step}},
            ),
            call(
                Path("run_prep_dir/namelist.restart"),
                {
                    "nml_restart": {
                        "rst_first_out": f"{run_date.shift(days=+1).format('YYYY-MM-DD')} 00:00:00.00"
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.netcdf"),
                {
                    "nml_netcdf": {
                        "nc_first_out": f"{run_date.format('YYYY-MM-DD')} 01:00:00.00",
                        "nc_output_stack": 24,
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.physics"),
                {
                    "nml_heating_calculated": {
                        "heating_calculate_file": f"atmos_{model_config}_{run_type}_hfx_{run_date.format('YYYYMMDD')}.nc"
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.surface"),
                {
                    "nml_surface_forcing": {
                        "wind_file": f"atmos_{model_config}_{run_type}_wnd_{run_date.format('YYYYMMDD')}.nc",
                        "precipitation_file": f"atmos_{model_config}_{run_type}_precip_{run_date.format('YYYYMMDD')}.nc",
                        "airpressure_file": f"atmos_{model_config}_{run_type}_hfx_{run_date.format('YYYYMMDD')}.nc",
                    }
                },
            ),
            call(
                Path(f"run_prep_dir/namelist.rivers.{model_config}"),
                {
                    "nml_river_type": {
                        "river_info_file": f"rivers_{model_config}_{run_type}_{run_date.format('YYYYMMDD')}.nc_riv.nml"
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.obc"),
                {
                    "nml_open_boundary_control": {
                        "obc_node_list_file": config["vhfr fvcom runs"]["fvcom grid"][
                            model_config
                        ]["obc nodes file"]
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.grid"),
                {
                    "nml_grid_coordinates": {
                        "grid_file": config["vhfr fvcom runs"]["fvcom grid"][
                            model_config
                        ]["grid file"],
                        "sigma_levels_file": config["vhfr fvcom runs"]["fvcom grid"][
                            model_config
                        ]["sigma file"],
                        "depth_file": config["vhfr fvcom runs"]["fvcom grid"][
                            model_config
                        ]["depths file"],
                        "coriolis_file": config["vhfr fvcom runs"]["fvcom grid"][
                            model_config
                        ]["coriolis file"],
                        "sponge_file": config["vhfr fvcom runs"]["fvcom grid"][
                            model_config
                        ]["sponge file"],
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.nesting"),
                {
                    "nml_nesting": {
                        "nesting_file_name": f"bdy_{model_config}_{run_type}_brcl_{run_date.format('YYYYMMDD')}.nc"
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.station_timeseries"),
                {
                    "nml_station_timeseries": {
                        "station_file": f"vh_{model_config}_station.txt"
                    }
                },
            ),
        ]

    @pytest.mark.parametrize(
        "model_config, run_type, run_date, time_step",
        (("x2", "forecast", arrow.get("2018-01-15"), 0.5),),
    )
    def test_edit_namelists_forecast(
        self, m_patch_nml, m_logger, model_config, run_type, run_date, time_step, config
    ):
        run_fvcom._edit_namelists(
            config["vhfr fvcom runs"]["case name"][model_config],
            run_date,
            model_config,
            run_type,
            Path("run_prep_dir"),
            config,
        )
        assert m_patch_nml.call_args_list == [
            call(
                Path("run_prep_dir/namelist.case"),
                {
                    "nml_case": {
                        "case_title": config["vhfr fvcom runs"]["case name"][
                            model_config
                        ],
                        "start_date": f"{run_date.shift(days=+1).format('YYYY-MM-DD')} 00:00:00.00",
                        "end_date": f"{run_date.shift(days=+2).format('YYYY-MM-DD')} 12:00:00.00",
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.startup.hotstart"),
                {"nml_startup": {"startup_file": f"vh_{model_config}_restart_0001.nc"}},
            ),
            call(
                Path("run_prep_dir/namelist.numerics"),
                {"nml_integration": {"extstep_seconds": time_step}},
            ),
            call(
                Path("run_prep_dir/namelist.restart"),
                {
                    "nml_restart": {
                        "rst_first_out": f"{run_date.shift(days=+2).format('YYYY-MM-DD')} 00:00:00.00"
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.netcdf"),
                {
                    "nml_netcdf": {
                        "nc_first_out": f"{run_date.shift(days=+1).format('YYYY-MM-DD')} 01:00:00.00",
                        "nc_output_stack": 36,
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.physics"),
                {
                    "nml_heating_calculated": {
                        "heating_calculate_file": f"atmos_{model_config}_{run_type}_hfx_{run_date.shift(days=+1).format('YYYYMMDD')}.nc"
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.surface"),
                {
                    "nml_surface_forcing": {
                        "wind_file": f"atmos_{model_config}_{run_type}_wnd_{run_date.shift(days=+1).format('YYYYMMDD')}.nc",
                        "precipitation_file": f"atmos_{model_config}_{run_type}_precip_{run_date.shift(days=+1).format('YYYYMMDD')}.nc",
                        "airpressure_file": f"atmos_{model_config}_{run_type}_hfx_{run_date.shift(days=+1).format('YYYYMMDD')}.nc",
                    }
                },
            ),
            call(
                Path(f"run_prep_dir/namelist.rivers.{model_config}"),
                {
                    "nml_river_type": {
                        "river_info_file": f"rivers_{model_config}_{run_type}_{run_date.shift(days=+1).format('YYYYMMDD')}.nc_riv.nml"
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.obc"),
                {
                    "nml_open_boundary_control": {
                        "obc_node_list_file": config["vhfr fvcom runs"]["fvcom grid"][
                            model_config
                        ]["obc nodes file"]
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.grid"),
                {
                    "nml_grid_coordinates": {
                        "grid_file": config["vhfr fvcom runs"]["fvcom grid"][
                            model_config
                        ]["grid file"],
                        "sigma_levels_file": config["vhfr fvcom runs"]["fvcom grid"][
                            model_config
                        ]["sigma file"],
                        "depth_file": config["vhfr fvcom runs"]["fvcom grid"][
                            model_config
                        ]["depths file"],
                        "coriolis_file": config["vhfr fvcom runs"]["fvcom grid"][
                            model_config
                        ]["coriolis file"],
                        "sponge_file": config["vhfr fvcom runs"]["fvcom grid"][
                            model_config
                        ]["sponge file"],
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.nesting"),
                {
                    "nml_nesting": {
                        "nesting_file_name": f"bdy_{model_config}_{run_type}_brcl_{run_date.shift(days=+1).format('YYYYMMDD')}.nc"
                    }
                },
            ),
            call(
                Path("run_prep_dir/namelist.station_timeseries"),
                {
                    "nml_station_timeseries": {
                        "station_file": f"vh_{model_config}_station.txt"
                    }
                },
            ),
        ]


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
class TestAssembleNamelist:
    """Unit test for _assemble_namelist() function."""

    def test_assemble_namelist(self, m_logger, model_config, run_type, config, tmpdir):
        run_prep_dir = Path(str(tmpdir.ensure_dir("fvcom-runs")))
        for namelist in config["vhfr fvcom runs"]["namelists"][
            f"vh_{model_config}_run.nml"
        ]:
            tmpdir.ensure("fvcom-runs", namelist)
        namelist_path = run_fvcom._assemble_namelist(
            f"vh_{model_config}", run_type, run_prep_dir, config
        )
        assert namelist_path.exists()


@pytest.mark.parametrize(
    "model_config, run_type, run_date, restart_date, depths_filename",
    (
        ("x2", "nowcast", arrow.get("2018-01-18"), "17jan18", "vh_x2_dep.dat"),
        ("x2", "forecast", arrow.get("2018-01-18"), "18jan18", "vh_x2_dep.dat"),
        ("r12", "nowcast", arrow.get("2019-02-21"), "20feb19", "vh_r12_smp3_dep.dat"),
    ),
)
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
class TestPrepFVCOM_InputDir:
    """Unit test for _prep_fvcom_input_dir() function."""

    def test_prep_fvcom_input_dir(
        self,
        m_logger,
        model_config,
        run_type,
        run_date,
        restart_date,
        depths_filename,
        config,
    ):
        with patch("nowcast.workers.run_fvcom.Path.symlink_to") as m_link:
            run_fvcom._prep_fvcom_input_dir(run_date, model_config, run_type, config)
        assert m_link.call_args_list == [
            call(Path(f"FVCOM-VHFR-config/grid/vh_{model_config}_grd.dat")),
            call(Path(f"FVCOM-VHFR-config/grid/{depths_filename}")),
            call(Path(f"FVCOM-VHFR-config/grid/vh_{model_config}_sigma.dat")),
            call(Path(f"FVCOM-VHFR-config/grid/vh_{model_config}_cor.dat")),
            call(Path(f"FVCOM-VHFR-config/grid/vh_{model_config}_nospg_spg.dat")),
            call(Path(f"FVCOM-VHFR-config/grid/vh_{model_config}_obc.dat")),
            call(Path(f"FVCOM-VHFR-config/output/vh_{model_config}_station.txt")),
            call(
                Path(
                    f"SalishSea/fvcom-nowcast-{model_config}/{restart_date}/vh_{model_config}_restart_0001.nc"
                )
            ),
        ]


@pytest.mark.parametrize(
    "model_config, run_type, run_date",
    (
        ("x2", "nowcast", arrow.get("2017-12-20")),
        ("x2", "forecast", arrow.get("2017-12-20")),
        ("r12", "nowcast", arrow.get("2019-02-21")),
    ),
)
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
@patch("nowcast.workers.run_fvcom._build_script", return_value="script", autospec=True)
class TestCreateRunScript:
    """Unit tests for _create_run_script() function."""

    def test_run_script_path(
        self, m_bld_script, m_logger, model_config, run_type, run_date, config, tmpdir
    ):
        tmp_run_dir = tmpdir.ensure_dir("tmp_run_dir")
        ddmmmyy = run_date.format("DDMMMYY").lower()
        run_id = f"{ddmmmyy}fvcom-{model_config}-{run_type}"
        run_script_path = run_fvcom._create_run_script(
            run_date,
            model_config,
            run_type,
            Path(str(tmp_run_dir)),
            Path(f"{run_id}.yaml"),
            config,
        )
        expected = Path(str(tmp_run_dir.join("VHFR_FVCOM.sh")))
        assert run_script_path == expected


@pytest.mark.parametrize(
    "model_config, run_type, run_date",
    (
        ("x2", "nowcast", arrow.get("2017-12-11")),
        ("x2", "forecast", arrow.get("2017-12-11")),
        ("r12", "nowcast", arrow.get("2019-02-21")),
    ),
)
@patch("nowcast.workers.run_fvcom.yaml.safe_load", autospec=True)
class TestBuildScript:
    """Unit tests for _build_script() function."""

    def test_script(
        self, m_yaml_load, model_config, run_type, run_date, config, tmpdir
    ):
        tmp_run_dir = tmpdir.ensure_dir("tmp_run_dir")
        ddmmmyy = run_date.format("DDMMMYY").lower()
        run_id = f"{ddmmmyy}fvcom-{model_config}-{run_type}"
        run_desc_file_path = tmp_run_dir.ensure(f"{run_id}.yaml")
        m_yaml_load.return_value = {"run_id": run_id}
        results_dir = tmpdir.ensure_dir(
            config["vhfr fvcom runs"]["run types"][f"{run_type} {model_config}"][
                "results"
            ]
        )
        n_processors = config["vhfr fvcom runs"]["number of processors"][model_config]
        script = run_fvcom._build_script(
            Path(str(tmp_run_dir)),
            Path(str(run_desc_file_path)),
            Path(str(results_dir)) / ddmmmyy,
            model_config,
            config,
        )
        expected = textwrap.dedent(
            f"""\
            #!/bin/bash

            RUN_ID="{run_id}"
            RUN_DESC="{run_id}.yaml"
            WORK_DIR="{tmp_run_dir}"
            RESULTS_DIR="{results_dir}/{ddmmmyy}"
            MPIRUN="mpirun --mca btl ^openib --mca orte_tmpdir_base /dev/shm --hostfile ${{HOME}}/mpi_hosts.fvcom.{model_config}"
            GATHER="bin/fvc gather"

            mkdir -p ${{RESULTS_DIR}}

            cd ${{WORK_DIR}}
            echo "working dir: $(pwd)" >>${{RESULTS_DIR}}/stdout

            echo "Starting run at $(date)" >>${{RESULTS_DIR}}/stdout
            ${{MPIRUN}} -np {n_processors} --bind-to none ./fvcom \\
              --casename=vh_{model_config} --logfile=./fvcom.log \\
              >>${{RESULTS_DIR}}/stdout 2>>${{RESULTS_DIR}}/stderr
            echo "Ended run at $(date)" >>${{RESULTS_DIR}}/stdout

            /bin/rm -f --verbose ${{WORK_DIR}}/.fvcomtestfile
            /bin/rmdir --verbose ${{WORK_DIR}}/output

            echo "Results gathering started at $(date)" >>${{RESULTS_DIR}}/stdout
            ${{GATHER}} ${{RESULTS_DIR}} --debug >>${{RESULTS_DIR}}/stdout
            echo "Results gathering ended at $(date)" >>${{RESULTS_DIR}}/stdout

            chmod g+rwx ${{RESULTS_DIR}}
            chmod g+rw ${{RESULTS_DIR}}/*
            chmod o+rx ${{RESULTS_DIR}}
            chmod o+r ${{RESULTS_DIR}}/*

            echo "Deleting run directory" >>${{RESULTS_DIR}}/stdout
            rmdir $(pwd)
            echo "Finished at $(date)" >>${{RESULTS_DIR}}/stdout
            """
        )
        assert script == expected


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
class TestDefinitions:
    """Unit tests for _definitions() function."""

    def test_definitions(self, model_config, run_type, config, tmpdir):
        run_desc_file_path = tmpdir.ensure(f"21dec17fvcom-{run_type}.yaml")
        run_desc = {"run_id": f"21dec17fvcom-{run_type}"}
        tmp_run_dir = tmpdir.ensure_dir("tmp_run_dir")
        results_dir = tmpdir.ensure_dir(f"SalishSea/fvcom-{run_type}/21dec17/")
        defns = run_fvcom._definitions(
            run_desc,
            Path(str(tmp_run_dir)),
            Path(str(run_desc_file_path)),
            Path(str(results_dir)),
            model_config,
            config,
        )
        expected = f"""RUN_ID="21dec17fvcom-{run_type}"
        RUN_DESC="21dec17fvcom-{run_type}.yaml"
        WORK_DIR="{tmp_run_dir}"
        RESULTS_DIR="{results_dir}"
        MPIRUN="mpirun --mca btl ^openib --mca orte_tmpdir_base /dev/shm --hostfile {config["vhfr fvcom runs"]["mpi hosts file"][model_config]}"
        GATHER="bin/fvc gather"
        """
        defns = defns.splitlines()
        for i, line in enumerate(expected.splitlines()[:-1]):
            assert defns[i].strip() == line.strip()


@pytest.mark.parametrize(
    "model_config, run_type",
    (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
)
class TestExecute:
    """Unit tests for _execute() function."""

    def test_execute(self, model_config, run_type, config):
        script = run_fvcom._execute(model_config, config)
        n_processors = config["vhfr fvcom runs"]["number of processors"][model_config]
        expected = textwrap.dedent(
            f"""\
            mkdir -p ${{RESULTS_DIR}}

            cd ${{WORK_DIR}}
            echo "working dir: $(pwd)" >>${{RESULTS_DIR}}/stdout

            echo "Starting run at $(date)" >>${{RESULTS_DIR}}/stdout
            ${{MPIRUN}} -np {n_processors} --bind-to none ./fvcom \\
              --casename=vh_{model_config} --logfile=./fvcom.log \\
              >>${{RESULTS_DIR}}/stdout 2>>${{RESULTS_DIR}}/stderr
            echo "Ended run at $(date)" >>${{RESULTS_DIR}}/stdout

            /bin/rm -f --verbose ${{WORK_DIR}}/.fvcomtestfile
            /bin/rmdir --verbose ${{WORK_DIR}}/output

            echo "Results gathering started at $(date)" >>${{RESULTS_DIR}}/stdout
            ${{GATHER}} ${{RESULTS_DIR}} --debug >>${{RESULTS_DIR}}/stdout
            echo "Results gathering ended at $(date)" >>${{RESULTS_DIR}}/stdout
            """
        )
        assert script == expected


@pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
@patch("nowcast.workers.run_fvcom.logger", autospec=True)
@patch("nowcast.workers.run_fvcom.subprocess.Popen", autospec=True)
@patch("nowcast.workers.run_fvcom.subprocess.run", autospec=True)
class TestLaunchRunScript:
    """Unit tests for _launch_run_script() function."""

    def test_launch_run_script(self, m_run, m_popen, m_logger, run_type):
        run_fvcom._launch_run_script(run_type, "VHFR_FVCOM.sh", "arbutus.cloud")
        m_popen.assert_called_once_with(["bash", "VHFR_FVCOM.sh"])

    def test_find_run_process_id(self, m_run, m_popen, m_logger, run_type):
        run_fvcom._launch_run_script(run_type, "VHFR_FVCOM.sh", "arbutus.cloud")
        m_run.assert_called_once_with(
            ["pgrep", "--newest", "--exact", "--full", "bash VHFR_FVCOM.sh"],
            stdout=subprocess.PIPE,
            check=True,
            universal_newlines=True,
        )

    def test_run_exec_cmd(self, m_run, m_popen, m_logger, run_type):
        run_exec_cmd = run_fvcom._launch_run_script(
            run_type, "VHFR_FVCOM.sh", "arbutus.cloud"
        )
        assert run_exec_cmd == "bash VHFR_FVCOM.sh"
