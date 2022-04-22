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


"""Unit tests for SalishSeaCast split_results worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import split_results


@pytest.fixture
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                results archive:
                  hindcast:
                    localhost: results/SalishSea/hindcast.201905/
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(split_results, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = split_results.main()
        assert worker.name == "split_results"
        assert worker.description.startswith(
            "SalishSeaCast worker that splits downloaded results of multi-day runs"
        )

    def test_add_run_type_arg(self, mock_worker):
        worker = split_results.main()
        assert worker.cli.parser._actions[3].dest == "run_type"
        assert worker.cli.parser._actions[3].choices == {"hindcast"}
        assert worker.cli.parser._actions[3].help

    def test_add_run_date_arg(self, mock_worker):
        worker = split_results.main()
        assert worker.cli.parser._actions[4].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[4].type == expected
        assert worker.cli.parser._actions[4].default == None
        assert worker.cli.parser._actions[4].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "split_results" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["split_results"]
        assert msg_registry["checklist key"] == "results splitting"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["split_results"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success hindcast",
            "failure hindcast",
            "crash",
        ]

    def test_results_archive(self, prod_config):
        archives = {
            "nowcast": "/results/SalishSea/nowcast-blue.201905/",
            "nowcast-dev": "/results/SalishSea/nowcast-dev.201905/",
            "forecast": "/results/SalishSea/forecast.201905/",
            "forecast2": "/results/SalishSea/forecast2.201905/",
            "nowcast-green": "/results2/SalishSea/nowcast-green.201905/",
            "nowcast-agrif": "/results/SalishSea/nowcast-agrif.201702/",
            "hindcast": {
                "localhost": "/results2/SalishSea/nowcast-green.201905/",
                "graham-dtn": "/nearline/rrg-allen/SalishSea/nowcast-green.201905/",
            },
        }
        assert prod_config["results archive"].keys() == archives.keys()
        for run_type, results_dir in archives.items():
            assert prod_config["results archive"][run_type] == results_dir


class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, caplog):
        parsed_args = SimpleNamespace(
            run_type="hindcast", run_date=arrow.get("2019-10-27")
        )
        caplog.set_level(logging.INFO)
        msg_type = split_results.success(parsed_args)
        assert caplog.records[0].levelname == "INFO"
        assert "results files split into daily directories" in caplog.messages[0]
        assert msg_type == "success hindcast"


class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, caplog):
        parsed_args = SimpleNamespace(
            run_type="hindcast", run_date=arrow.get("2019-10-27")
        )
        caplog.set_level(logging.CRITICAL)
        msg_type = split_results.failure(parsed_args)
        assert caplog.records[0].levelname == "CRITICAL"
        assert "results files splitting failed" in caplog.messages[0]
        assert msg_type == "failure hindcast"


class TestSplitResults:
    """Integration test for split_reults() function."""

    def test_checklist(self, config, caplog, tmp_path, monkeypatch):
        run_type_results = tmp_path / Path(
            config["results archive"]["hindcast"]["localhost"]
        )
        run_type_results.mkdir(parents=True)
        monkeypatch.setitem(
            config["results archive"]["hindcast"], "localhost", run_type_results
        )

        results_dir = run_type_results / "01jan07"
        results_dir.mkdir()
        nc_files = [
            results_dir / "SalishSea_1h_20070101_20070102_grid_T_20070101-20070101.nc",
            results_dir / "SalishSea_1h_20070101_20070102_grid_T_20070102-20070102.nc",
        ]
        for nc_file in nc_files:
            nc_file.write_bytes(b"")
        restart_file = results_dir / "SalishSea_01587600_restart.nc"
        restart_file.write_bytes(b"")

        def mock_glob(path, pattern):
            if pattern == "*.nc":
                for glob in nc_files + [restart_file]:
                    yield glob
            else:
                yield restart_file

        monkeypatch.setattr(split_results.Path, "glob", mock_glob)

        run_type = "hindcast"
        run_date = arrow.get("2007-01-01")
        parsed_args = SimpleNamespace(run_type=run_type, run_date=run_date)

        caplog.set_level(logging.INFO)
        checklist = split_results.split_results(parsed_args, config)
        assert caplog.records[0].levelname == "INFO"
        expected = (
            f'splitting {run_date.format("YYYY-MM-DD")} {run_type} '
            f"results files into daily directories"
        )
        assert caplog.messages[0] == expected
        assert checklist == {"2007-01-01", "2007-01-02"}
        assert (
            tmp_path
            / run_type_results
            / "01jan07"
            / "SalishSea_1h_20070101_20070101_grid_T.nc"
        ).exists()
        assert (run_type_results / "02jan07" / "SalishSea_01587600_restart.nc").exists()


class TestMkDestDir:
    """Unit test for _mk_dest_dir() function."""

    def test_mk_dest_dir(self, tmp_path):
        run_type_results = tmp_path / "hindcast.201905"
        run_type_results.mkdir()
        date = arrow.get("2019-10-28")
        dest_dir = split_results._mk_dest_dir(run_type_results, date)
        assert dest_dir == run_type_results / "28oct19"
        assert dest_dir.exists()


class TestMoveResultsNcFile:
    """Unit tests for _move_results_nc_file() function."""

    def test_move_nemo_grid_nc_file(self, caplog, tmp_path):
        run_type_results = tmp_path / "hindcast.201905"
        run_type_results.mkdir()
        results_dir = run_type_results / "01jan07"
        results_dir.mkdir()
        nc_file = (
            results_dir / "SalishSea_1h_20070101_20070331_grid_T_20070102-20070102.nc"
        )
        nc_file.write_bytes(b"")
        dest_dir = run_type_results / "02jan07"
        dest_dir.mkdir()

        caplog.set_level(logging.DEBUG)

        split_results._move_results_nc_file(nc_file, dest_dir, arrow.get("2007-01-02"))
        assert (dest_dir / "SalishSea_1h_20070102_20070102_grid_T.nc").exists()
        assert caplog.records[0].levelname == "DEBUG"
        expected = f"moved {nc_file} to {dest_dir / 'SalishSea_1h_20070102_20070102_grid_T.nc'}"
        assert caplog.messages[0] == expected

    def test_move_other_nc_file(self, caplog, tmp_path):
        run_type_results = tmp_path / "hindcast.201905"
        run_type_results.mkdir()
        results_dir = run_type_results / "01jan07"
        results_dir.mkdir()
        nc_file = results_dir / "FVCOM_T_20070101-20070101.nc"
        nc_file.write_bytes(b"")
        dest_dir = run_type_results / "02jan07"
        dest_dir.mkdir()

        caplog.set_level(logging.DEBUG)

        split_results._move_results_nc_file(nc_file, dest_dir, arrow.get("2007-01-02"))
        assert (dest_dir / "FVCOM_T.nc").exists()
        assert caplog.records[0].levelname == "DEBUG"
        expected = f"moved {nc_file} to {dest_dir / 'FVCOM_T.nc'}"
        assert caplog.messages[0] == expected


class TestMoveRestartFile:
    """Unit tests for _move_results_nc_file() function."""

    def test_move_restart_file(self, caplog, tmp_path):
        run_type_results = tmp_path / "hindcast.201905"
        run_type_results.mkdir()
        results_dir = run_type_results / "01jan07"
        results_dir.mkdir()
        restart_file = results_dir / "SalishSea_01587600_restart.nc"
        restart_file.write_bytes(b"")
        dest_dir = run_type_results / "31mar07"
        dest_dir.mkdir()

        caplog.set_level(logging.DEBUG)

        split_results._move_restart_file(restart_file, dest_dir)
        assert (dest_dir / "SalishSea_01587600_restart.nc").exists()
        assert caplog.records[0].levelname == "DEBUG"
        expected = f"moved {restart_file} to {dest_dir}"
        assert caplog.messages[0] == expected
