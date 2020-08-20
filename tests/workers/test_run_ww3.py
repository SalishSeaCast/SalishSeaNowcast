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
"""Unit tests for Salish Sea WaveWatch3 nowcast/forecast run_ww3 worker.
"""
import logging
import os
import stat
import subprocess
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import run_ww3


@pytest.fixture()
def config(base_config, tmp_path):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
    run_prep_dir = tmp_path / "wwatch3-runs"
    run_prep_dir.mkdir()
    nowcast_results_dir = tmp_path / "wwatch3-nowcast"
    nowcast_results_dir.mkdir()
    forecast_results_dir = tmp_path / "wwatch3-forecast"
    forecast_results_dir.mkdir()

    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                f"""\
                wave forecasts:
                    run prep dir: {run_prep_dir}
                    wwatch3 exe path: wwatch3-5.16/exe
                    salishsea cmd: salishsea
                    results:
                        nowcast: {nowcast_results_dir}
                        forecast: {forecast_results_dir}
                        forecast2: wwatch3-forecast2/
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_now(monkeypatch):
    def now():
        return arrow.get("2020-07-30 14:20:43.123456-0700")

    monkeypatch.setattr(run_ww3.arrow, "now", now)


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(run_ww3, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, mock_worker):
        worker = run_ww3.main()
        assert worker.name == "run_ww3"
        assert worker.description.startswith(
            "SalishSeaCast WaveWatch3 nowcast/forecast worker that prepares"
        )

    def test_add_host_name_arg(self, mock_worker):
        worker = run_ww3.main()
        assert worker.cli.parser._actions[3].dest == "host_name"
        assert worker.cli.parser._actions[3].help

    def test_add_run_type_arg(self, mock_worker):
        worker = run_ww3.main()
        assert worker.cli.parser._actions[4].dest == "run_type"
        expected = {"nowcast", "forecast", "forecast2"}
        assert worker.cli.parser._actions[4].choices == expected
        assert worker.cli.parser._actions[4].help

    def test_add_run_date_option(self, mock_worker):
        worker = run_ww3.main()
        assert worker.cli.parser._actions[5].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[5].type == expected
        assert worker.cli.parser._actions[5].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[5].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

    def test_message_registry(self, prod_config):
        assert "run_ww3" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["run_ww3"]
        assert msg_registry["checklist key"] == "WWATCH3 run"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["run_ww3"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success forecast2",
            "failure forecast2",
            "success nowcast",
            "failure nowcast",
            "success forecast",
            "failure forecast",
            "crash",
        ]

    @pytest.mark.parametrize(
        "run_type, expected",
        (
            ("nowcast", "/nemoShare/MEOPAR/SalishSea/wwatch3-nowcast/"),
            ("forecast", "/nemoShare/MEOPAR/SalishSea/wwatch3-forecast/"),
            ("forecast2", "/nemoShare/MEOPAR/SalishSea/wwatch3-forecast2/"),
        ),
    )
    def test_results(self, run_type, expected, prod_config):
        results = prod_config["wave forecasts"]["results"]
        assert results[run_type] == expected

    def test_run_prep_dir(self, prod_config):
        run_prep_dir = prod_config["wave forecasts"]["run prep dir"]
        assert run_prep_dir == "/nemoShare/MEOPAR/nowcast-sys/wwatch3-runs"

    def test_wwatch3_exe(self, prod_config):
        wwatch3_exe_path = prod_config["wave forecasts"]["wwatch3 exe path"]
        assert wwatch3_exe_path == "/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/exe"

    def test_salishsea_cmd(self, prod_config):
        salishsea_cmd = prod_config["wave forecasts"]["salishsea cmd"]
        assert (
            salishsea_cmd == "/nemoShare/MEOPAR/nowcast-sys/nowcast-env/bin/salishsea"
        )


@pytest.mark.parametrize("run_type", ["forecast2", "nowcast", "forecast"])
class TestSuccess:
    """Unit tests for success() function.
    """

    def test_success(self, run_type, caplog):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2020-07-24"),
        )
        caplog.set_level(logging.INFO)

        msg_type = run_ww3.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"{run_type} WaveWatch3 run for 2020-07-24 on {parsed_args.host_name} started"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["forecast2", "nowcast", "forecast"])
class TestFailure:
    """Unit tests for failure() function.
    """

    def test_failure(self, run_type, caplog):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2020-07-24"),
        )
        caplog.set_level(logging.CRITICAL)

        msg_type = run_ww3.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"{run_type} WaveWatch3 run for 2020-07-24 on {parsed_args.host_name} failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {run_type}"


@patch("nowcast.workers.run_ww3.logger", autospec=True)
class TestRunWW3:
    """Unit tests for run_ww3() function.
    """

    @pytest.mark.parametrize("run_type", ["forecast2", "nowcast", "forecast"])
    @patch("nowcast.workers.run_ww3._build_tmp_run_dir", autospec=True)
    @patch("nowcast.workers.run_ww3._write_run_script", autospec=True)
    @patch(
        "nowcast.workers.run_ww3._launch_run",
        return_value="bash SoGWW3.sh",
        autospec=True,
    )
    def test_checklist(
        self,
        m_launch_run,
        m_write_run_script,
        m_create_tmp_run_dir,
        m_logger,
        run_type,
        config,
    ):
        parsed_args = SimpleNamespace(
            host_name="arbutus.cloud",
            run_type=run_type,
            run_date=arrow.get("2017-03-25"),
        )
        m_create_tmp_run_dir.return_value = Path(
            "/wwatch3-runs/a1e00274-11a3-11e7-ad44-80fa5b174bd6"
        )

        checklist = run_ww3.run_ww3(parsed_args, config)
        expected = {
            run_type: {
                "host": "arbutus.cloud",
                "run dir": "/wwatch3-runs/a1e00274-11a3-11e7-ad44-80fa5b174bd6",
                "run exec cmd": "bash SoGWW3.sh",
                "run date": "2017-03-25",
            }
        }
        assert checklist == expected


class TestBuildTmpRunDir:
    """Unit tests for _build_tmp_run_dir() function.
    """

    @pytest.mark.parametrize("run_type", ["forecast2", "nowcast", "forecast"])
    @patch("nowcast.workers.run_ww3._write_ww3_input_files", autospec=True)
    def test_run_dir_path(
        self, m_write_ww3_input_files, run_type, mock_now, config,
    ):
        run_dir_path = run_ww3._build_tmp_run_dir(
            arrow.get("2017-03-24"), run_type, config
        )

        run_prep_dir = Path(config["wave forecasts"]["run prep dir"])
        assert (
            run_dir_path == run_prep_dir / f"{run_type}_2020-07-30T142043.123456-0700"
        )


@pytest.mark.parametrize("run_type", ["forecast2", "nowcast", "forecast"])
class TestMakeRunDir:
    """Unit test for _make_run_dir() function.
    """

    @pytest.mark.skipif(
        "GITHUB_ACTIONS" in os.environ,
        reason="Actions file system seems to disallow 0o775 mode for directories",
    )
    def test_make_run_dir(self, run_type, mock_now, config):
        run_prep_dir = Path(config["wave forecasts"]["run prep dir"])

        run_dir_path = run_ww3._make_run_dir(run_type, run_prep_dir)

        assert (
            run_dir_path == run_prep_dir / f"{run_type}_2020-07-30T142043.123456-0700"
        )
        assert stat.S_IMODE(run_prep_dir.stat().st_mode) == 0o775


class TestCreateSymlinks:
    """Unit tests for _create_symlinks() function.
    """

    @pytest.mark.parametrize("run_type", ("forecast2", "nowcast", "forecast"))
    def test_mod_def_wind_current(self, run_type, config):
        run_date = arrow.get("2020-07-30")
        run_prep_path = Path(config["wave forecasts"]["run prep dir"])
        mod_def_ww3_file = run_prep_path / "mod_def.ww3"
        mod_def_ww3_file.write_bytes(b"")
        wind_dir = run_prep_path / "wind"
        wind_dir.mkdir()
        current_dir = run_prep_path / "current"
        current_dir.mkdir()
        run_dir_path = run_prep_path / "nowcast_2020-07-30T142043.123456-0700"
        run_dir_path.mkdir()

        run_ww3._create_symlinks(
            run_date, run_type, run_prep_path, run_dir_path, config
        )

        assert (run_dir_path / "mod_def.ww3").is_symlink()
        assert (run_dir_path / "mod_def.ww3").resolve() == mod_def_ww3_file
        assert (run_dir_path / "wind").is_symlink()
        assert (run_dir_path / "wind").resolve() == wind_dir
        assert (run_dir_path / "current").is_symlink()
        assert (run_dir_path / "current").resolve() == current_dir

    @pytest.mark.parametrize(
        "run_type, restart_from, restart_date",
        (
            ("nowcast", "nowcast", "29jul20"),
            ("forecast", "nowcast", "30jul20"),
            ("forecast2", "forecast", "29jul20"),
        ),
    )
    def test_restart(self, run_type, restart_from, restart_date, config):
        run_date = arrow.get("2020-07-30")
        run_prep_path = Path(config["wave forecasts"]["run prep dir"])
        mod_def_ww3_file = run_prep_path / "mod_def.ww3"
        mod_def_ww3_file.write_bytes(b"")
        wind_dir = run_prep_path / "wind"
        wind_dir.mkdir()
        current_dir = run_prep_path / "current"
        current_dir.mkdir()
        prev_run_path = (
            Path(config["wave forecasts"]["results"][restart_from]) / restart_date
        )
        prev_run_path.mkdir()
        restart_file = prev_run_path / "restart001.ww3"
        restart_file.write_bytes(b"")
        run_dir_path = run_prep_path / "nowcast_2020-07-30T142043.123456-0700"
        run_dir_path.mkdir()

        run_ww3._create_symlinks(
            run_date, run_type, run_prep_path, run_dir_path, config
        )

        assert (run_dir_path / "restart.ww3").is_symlink()
        assert (run_dir_path / "restart.ww3").resolve() == restart_file


@pytest.mark.parametrize("run_type", ["forecast2", "nowcast", "forecast"])
class TestWW3PrncWindContents:
    """Unit test for _ww3_prnc_wind_contents() function.
    """

    def test_ww3_prnc_wind_contents(self, run_type):
        contents = run_ww3._ww3_prnc_wind_contents(arrow.get("2017-03-25"), run_type)
        assert "'WND' 'LL' T T" in contents
        assert "x y" in contents
        assert "u_wind v_wind" in contents
        assert "'wind/SoG_wind_20170325.nc'" in contents


@pytest.mark.parametrize("run_type", ["forecast2", "nowcast", "forecast"])
class TestWW3PrncCurrentContents:
    """Unit test for _ww3_prnc_current_contents() function.
    """

    def test_ww3_prnc_current_contents(self, run_type):
        contents = run_ww3._ww3_prnc_current_contents(arrow.get("2017-03-26"), run_type)
        assert "'CUR' 'LL' T T" in contents
        assert "x y" in contents
        assert "u_current v_current" in contents
        assert "'current/SoG_current_20170326.nc'" in contents


@pytest.mark.parametrize(
    "run_type, run_date, start_date, restart_date, end_date, end_time",
    [
        ("nowcast", "2018-09-18", "20180918", "20180919", "20180919", "000000"),
        ("forecast", "2018-09-18", "20180919", "20180920", "20180920", "120000"),
        ("forecast2", "2018-09-18", "20180919", "20180920", "20180920", "060000"),
    ],
)
class TestWW3ShelContents:
    """Unit test for _ww3_shel_contents() function.
    """

    def test_ww3_shel_contents(
        self, run_type, run_date, start_date, restart_date, end_date, end_time
    ):
        contents = run_ww3._ww3_shel_contents(arrow.get(run_date), run_type)
        # Forcing/inputs to use
        assert "F F  Water levels w/ homogeneous field data" in contents
        assert "T F  Currents w/ homogeneous field data" in contents
        assert "T F  Winds w/ homogeneous field data" in contents
        assert "F    Ice concentration" in contents
        assert "F    Assimilation data : Mean parameters" in contents
        assert "F    Assimilation data : 1-D spectra" in contents
        assert "F    Assimilation data : 2-D spectra." in contents
        # Start/end time
        assert f"{start_date} 000000  Start time (YYYYMMDD HHmmss)" in contents
        assert f"{end_date} {end_time}  End time (YYYYMMDD HHmmss)" in contents
        # Output server mode
        assert "2  dedicated process" in contents
        # Field outputs
        assert f"{start_date} 000000 1800 {end_date} {end_time}" in contents
        assert "N  by name" in contents
        assert "HS LM WND CUR FP T02 DIR DP WCH WCC TWO FOC USS" in contents
        # Point outputs
        assert f"{start_date} 000000 600 {end_date} {end_time}" in contents
        assert "236.52 48.66 'C46134PatB'" in contents
        assert "236.27 49.34 'C46146HalB'" in contents
        assert "235.01 49.91 'C46131SenS'" in contents
        assert "0.0 0.0 'STOPSTRING'" in contents
        # Along-track output (required placeholder for unused feature)
        assert f"{start_date} 000000 0 {end_date} {end_time}" in contents
        # Restart files
        assert f"{restart_date} 000000 3600 {restart_date} 000000" in contents
        # Boundary data (required placeholder for unused feature)
        assert f"{start_date} 000000 0 {end_date} {end_time}" in contents
        # Separated wave field data (required placeholder for unused feature)
        assert f"{start_date} 000000 0 {end_date} {end_time}" in contents
        # Homogeneous field data (required placeholder for unused feature)
        assert "STP" in contents


@pytest.mark.parametrize(
    "run_type, run_date, start_date, output_count",
    [
        ("nowcast", "2017-03-26", "20170326", 48),
        ("forecast", "2017-03-26", "20170327", 72),
        ("forecast2", "2017-03-26", "20170327", 60),
    ],
)
class TestWW3OunfContents:
    """Unit test for _ww3_ounf_contents() function.
    """

    def test_ww3_ounf_contents(self, run_type, run_date, start_date, output_count):
        contents = run_ww3._ww3_ounf_contents(arrow.get(run_date), run_type)
        assert f"{start_date} 000000 1800 {output_count}" in contents
        assert "N  by name" in contents
        assert "HS LM WND CUR FP T02 DIR DP WCH WCC TWO FOC USS" in contents
        assert "4" in contents
        assert "4" in contents
        assert "0 1 2" in contents
        assert "T" in contents
        assert "SoG_ww3_fields_" in contents
        assert "8" in contents
        assert "1 1000000 1 1000000" in contents


@pytest.mark.parametrize(
    "run_type, run_date, start_date, output_count",
    [
        ("nowcast", "2017-03-26", "20170326", 144),
        ("forecast", "2017-03-26", "20170327", 216),
        ("forecast2", "2017-03-26", "20170327", 180),
    ],
)
class TestWW3OunpContents:
    """Unit test for _ww3_ounp_contents() function.
    """

    def test_ww3_ounp_contents(self, run_type, run_date, start_date, output_count):
        contents = run_ww3._ww3_ounp_contents(arrow.get(run_date), run_type)
        assert f"{start_date} 000000 600 {output_count}" in contents
        assert "-1" in contents
        assert "SoG_ww3_points_" in contents
        assert "8" in contents
        assert "4" in contents
        assert "T 100" in contents
        assert "2" in contents
        assert "0" in contents
        assert "6" in contents
        assert "T" in contents


class TestBuildRunScript:
    """Unit test for _build_run_script() function.
    """

    @pytest.mark.parametrize("run_type", ["forecast2", "nowcast", "forecast"])
    def test_top_of_script(self, run_type, config):
        script = run_ww3._build_run_script(
            arrow.get("2017-03-29"),
            run_type,
            Path("wwatch3-runs/tmp_run_dir"),
            Path(f"wwatch3-{run_type}"),
            config,
        )
        assert script.startswith(
            "#!/bin/bash\n"
            "set -e  # abort on first error\n"
            "set -u  # abort if undefinded variable is encountered\n"
        )


class TestDefinitions:
    """Unit test for _definitions() function.
    """

    @pytest.mark.parametrize("run_type", ["forecast2", "nowcast", "forecast"])
    def test_definitions(self, run_type, config):
        defns = run_ww3._definitions(
            arrow.get("2017-03-29"),
            run_type,
            Path("wwatch3-runs/tmp_run_dir"),
            Path(f"wwatch3-{run_type}"),
            config,
        )
        expected = f"""RUN_ID="29mar17ww3-{run_type}"
        WORK_DIR="wwatch3-runs/tmp_run_dir"
        RESULTS_DIR="wwatch3-{run_type}/29mar17"
        WW3_EXE="wwatch3-5.16/exe"
        MPIRUN="mpirun --mca btl ^openib --mca orte_tmpdir_base /dev/shm --hostfile ${{HOME}}/mpi_hosts"
        GATHER="salishsea gather"
        """

        expected = expected.splitlines()
        for i, line in enumerate(defns.splitlines()):
            assert line.strip() == expected[i].strip()


class TestPrepare:
    """Unit test for _prepare() function.
    """

    def test_prepare(self):
        preparations = run_ww3._prepare()
        expected = """mkdir -p ${RESULTS_DIR}

        cd ${WORK_DIR}
        echo "working dir: $(pwd)" >>${RESULTS_DIR}/stdout

        echo "Starting wind.nc file creation at $(date)" >>${RESULTS_DIR}/stdout
        ln -s ww3_prnc_wind.inp ww3_prnc.inp && \\
          ${WW3_EXE}/ww3_prnc >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\
          rm -f ww3_prnc.inp
      echo "Ending wind.nc file creation at $(date)" >>${RESULTS_DIR}/stdout

        echo "Starting current.nc file creation at $(date)" >>${RESULTS_DIR}/stdout
        ln -s ww3_prnc_current.inp ww3_prnc.inp && \\
          ${WW3_EXE}/ww3_prnc >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\
          rm -f ww3_prnc.inp
        echo "Ending current.nc file creation at $(date)" >>${RESULTS_DIR}/stdout
        """
        expected = expected.splitlines()
        for i, line in enumerate(preparations.splitlines()):
            assert line.strip() == expected[i].strip()


class TestExecute:
    """Unit test for _execute() function.
    """

    @pytest.mark.parametrize("run_type", ["forecast2", "forecast"])
    def test_forecast_execute(self, run_type):
        execution = run_ww3._execute(run_type, arrow.get("2017-04-20"))
        expected = textwrap.dedent(
            """\
            echo "Starting run at $(date)" >>${RESULTS_DIR}/stdout
            ${MPIRUN} -np 75 --bind-to none ${WW3_EXE}/ww3_shel \\
              >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\
            mv log.ww3 ww3_shel.log && \\
            rm current.ww3 wind.ww3 && \\
            rm current/SoG_current_20170420.nc && \\
            rm wind/SoG_wind_20170420.nc
            echo "Ended run at $(date)" >>${RESULTS_DIR}/stdout
            """
        )
        assert execution.splitlines() == expected.splitlines()

    def test_nowcast_execute(self):
        execution = run_ww3._execute("nowcast", arrow.get("2017-04-20"))
        expected = textwrap.dedent(
            """\
            echo "Starting run at $(date)" >>${RESULTS_DIR}/stdout
            ${MPIRUN} -np 75 --bind-to none ${WW3_EXE}/ww3_shel \\
              >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\
            mv log.ww3 ww3_shel.log && \\
            rm current.ww3 wind.ww3 && \\
            echo "Ended run at $(date)" >>${RESULTS_DIR}/stdout
            """
        )
        assert execution.splitlines() == expected.splitlines()


class TestNetcdfOutput:
    """Unit test for _netcdf_output() function.
    """

    @pytest.mark.parametrize("run_type", ["forecast2", "forecast"])
    def test_forecast_netcdf_output(self, run_type):
        output_to_netcdf = run_ww3._netcdf_output(arrow.get("2017-03-30"), run_type)
        expected = """echo "Starting netCDF4 fields output at $(date)" >>${RESULTS_DIR}/stdout
        ${WW3_EXE}/ww3_ounf >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\
        ncrcat -4 -L4 -o SoG_ww3_fields_20170331_20170401.nc \\
          SoG_ww3_fields_20170331.nc SoG_ww3_fields_20170401.nc \\
          >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\
        rm SoG_ww3_fields_20170331.nc SoG_ww3_fields_20170401.nc && \\
        rm out_grd.ww3
        echo "Ending netCDF4 fields output at $(date)" >>${RESULTS_DIR}/stdout
        
        echo "Starting netCDF4 points output at $(date)" >>${RESULTS_DIR}/stdout
        ${WW3_EXE}/ww3_ounp >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\
        ncrcat -4 -L4 -o SoG_ww3_points_20170331_20170401.nc \\
          SoG_ww3_points_20170331_tab.nc SoG_ww3_points_20170401_tab.nc \\
          >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\
        rm SoG_ww3_points_20170331_tab.nc SoG_ww3_points_20170401_tab.nc && \\
        rm out_pnt.ww3
        echo "Ending netCDF4 points output at $(date)" >>${RESULTS_DIR}/stdout
        """
        expected = expected.splitlines()
        for i, line in enumerate(output_to_netcdf.splitlines()):
            assert line.strip() == expected[i].strip()

    def test_nowcast_netcdf_output(self):
        output_to_netcdf = run_ww3._netcdf_output(arrow.get("2017-03-30"), "nowcast")
        expected = """echo "Starting netCDF4 fields output at $(date)" >>${RESULTS_DIR}/stdout
        ${WW3_EXE}/ww3_ounf >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\
        ncks -4 -L4 -o SoG_ww3_fields_20170330_20170330.nc \\
          SoG_ww3_fields_20170330.nc \\
          >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\
        rm SoG_ww3_fields_20170330.nc && \\
        rm out_grd.ww3
        echo "Ending netCDF4 fields output at $(date)" >>${RESULTS_DIR}/stdout

        echo "Starting netCDF4 points output at $(date)" >>${RESULTS_DIR}/stdout
        ${WW3_EXE}/ww3_ounp >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\
        ncks -4 -L4 -o SoG_ww3_points_20170330_20170330.nc \\
          SoG_ww3_points_20170330_tab.nc \\
          >>${RESULTS_DIR}/stdout 2>>${RESULTS_DIR}/stderr && \\
        rm SoG_ww3_points_20170330_tab.nc && \\
        rm out_pnt.ww3
        echo "Ending netCDF4 points output at $(date)" >>${RESULTS_DIR}/stdout
        """
        expected = expected.splitlines()
        for i, line in enumerate(output_to_netcdf.splitlines()):
            assert line.strip() == expected[i].strip()


class TestCleanup:
    """Unit test for _cleanup() function.
    """

    def test_cleanup(self):
        cleanup = run_ww3._cleanup()
        expected = """echo "Results gathering started at $(date)" >>${RESULTS_DIR}/stdout
        ${GATHER} ${RESULTS_DIR} --debug >>${RESULTS_DIR}/stdout
        echo "Results gathering ended at $(date)" >>${RESULTS_DIR}/stdout
        
        echo "Deleting run directory" >>${RESULTS_DIR}/stdout
        rmdir $(pwd)
        echo "Finished at $(date)" >>${RESULTS_DIR}/stdout
        """
        expected = expected.splitlines()
        for i, line in enumerate(cleanup.splitlines()):
            assert line.strip() == expected[i].strip()


@pytest.mark.parametrize("run_type", ["forecast2", "forecast"])
@patch("nowcast.workers.run_ww3.logger", autospec=True)
@patch("nowcast.workers.run_ww3.subprocess.Popen", autospec=True)
@patch("nowcast.workers.run_ww3.subprocess.run", autospec=True)
class TestLaunchRun:
    """Unit tests for _launch_run() function.
    """

    def test_launch_run(self, m_run, m_popen, m_logger, run_type):
        run_ww3._launch_run(run_type, Path("SoGWW3.sh"), "arbutus.cloud")
        m_popen.assert_called_once_with(["bash", "SoGWW3.sh"])

    def test_find_run_process_pid(self, m_run, m_popen, m_logger, run_type):
        run_ww3._launch_run(run_type, Path("SoGWW3.sh"), "arbutus.cloud")
        m_run.assert_called_once_with(
            ["pgrep", "--newest", "--exact", "--full", "bash SoGWW3.sh"],
            stdout=subprocess.PIPE,
            check=True,
            universal_newlines=True,
        )

    def test_run_exec_cmd(self, m_run, m_popen, m_logger, run_type):
        m_run.return_value = SimpleNamespace(stdout=43)
        run_exec_cmd = run_ww3._launch_run(run_type, Path("SoGWW3.sh"), "arbutus.cloud")
        assert run_exec_cmd == "bash SoGWW3.sh"
