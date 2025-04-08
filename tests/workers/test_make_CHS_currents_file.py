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


"""Unit tests for SalishSeaCast make_CHS_currents_file worker."""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_CHS_currents_file


@pytest.fixture
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                file group: allen

                run types:
                  nowcast:
                    mesh mask: mesh_mask201702.nc
                  forecast:
                    mesh mask: mesh_mask201702.nc
                  forecast2:
                    mesh mask: mesh_mask201702.nc

                results archive:
                  nowcast: nowcast-blue/
                  forecast: forecast/
                  forecast2: forecast2/

                figures:
                  grid dir:
                    nowcast-sys/grid/
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(make_CHS_currents_file, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = make_CHS_currents_file.main()
        assert worker.name == "make_CHS_currents_file"
        assert worker.description.startswith(
            "SalishSeaCast worker that averages, unstaggers and rotates the near surface velocities,"
        )

    def test_add_run_type_arg(self, mock_worker):
        worker = make_CHS_currents_file.main()
        assert worker.cli.parser._actions[3].dest == "run_type"
        assert worker.cli.parser._actions[3].choices == {
            "nowcast",
            "forecast",
            "forecast2",
        }
        assert worker.cli.parser._actions[3].help

    def test_add_run_date_option(self, mock_worker):
        worker = make_CHS_currents_file.main()
        assert worker.cli.parser._actions[4].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[4].type == expected
        expected = arrow.now().floor("day")
        assert worker.cli.parser._actions[4].default == expected
        assert worker.cli.parser._actions[4].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_CHS_currents_file" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"][
            "make_CHS_currents_file"
        ]
        assert msg_registry["checklist key"] == "CHS currents file"

    @pytest.mark.parametrize(
        "msg",
        (
            "success nowcast",
            "failure nowcast",
            "success forecast",
            "failure forecast",
            "success forecast2",
            "failure forecast2",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "make_CHS_currents_file"
        ]
        assert msg in msg_registry

    def test_figures_section(self, prod_config):
        figures = prod_config["figures"]
        assert figures["grid dir"] == "/SalishSeaCast/grid/"

    def test_run_types_section(self, prod_config):
        run_types = prod_config["run types"]
        assert run_types["nowcast"]["mesh mask"] == "mesh_mask202108.nc"
        assert run_types["forecast"]["mesh mask"] == "mesh_mask202108.nc"
        assert run_types["forecast2"]["mesh mask"] == "mesh_mask202108.nc"

    def test_results_archive_section(self, prod_config):
        results_archive = prod_config["results archive"]
        assert results_archive["nowcast"] == "/results/SalishSea/nowcast-blue.202111/"
        assert results_archive["forecast"] == "/results/SalishSea/forecast.202111/"
        assert results_archive["forecast2"] == "/results/SalishSea/forecast2.202111/"

    def test_file_group(self, prod_config):
        assert prod_config["file group"] == "sallen"


@pytest.mark.parametrize("run_type", ["nowcast", "forecast", "forecast2"])
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, run_type, caplog):
        run_date = arrow.get("2018-09-01")
        parsed_args = SimpleNamespace(run_type=run_type, run_date=run_date)
        caplog.set_level(logging.DEBUG)

        msg_type = make_CHS_currents_file.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = (
            f"Made CHS currents file for {run_date.format("YYYY-MM-DD")} for {run_type}"
        )
        assert caplog.records[0].message == expected
        assert msg_type == f"success {run_type}"


@pytest.mark.parametrize("run_type", ["nowcast", "forecast", "forecast2"])
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, run_type, caplog):
        run_date = arrow.get("2018-09-01")
        parsed_args = SimpleNamespace(run_type=run_type, run_date=run_date)
        caplog.set_level(logging.DEBUG)

        msg_type = make_CHS_currents_file.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"Making CHS currents file for {run_date.format("YYYY-MM-DD")} failed for {run_type}"
        assert caplog.records[0].message == expected
        assert msg_type == f"failure {run_type}"


class TestMakeCHSCurrentsFile:
    """Unit tests for make_CHS_currents_function."""

    @staticmethod
    @pytest.fixture
    def mock_read_avg_unstagger_rotate(monkeypatch):
        def _mock_read_avg_unstagger_rotate(
            meshfilename, src_dir, ufile, vfile, run_type
        ):
            return "urot5", "vrot5", "urot10", "vrot10"

        monkeypatch.setattr(
            make_CHS_currents_file,
            "_read_avg_unstagger_rotate",
            _mock_read_avg_unstagger_rotate,
        )

    @staticmethod
    @pytest.fixture
    def mock_write_netcdf(monkeypatch):
        def _mock_write_netcdf(src_dir, urot5, vrot5, urot10, vrot10, run_type):
            return f"{src_dir}/CHS_currents.nc"

        monkeypatch.setattr(make_CHS_currents_file, "_write_netcdf", _mock_write_netcdf)

    @staticmethod
    @pytest.fixture
    def mock_fix_perms(monkeypatch):
        def _mock_fix_perms(path, grp_name):
            pass

        monkeypatch.setattr(make_CHS_currents_file.lib, "fix_perms", _mock_fix_perms)

    @pytest.mark.parametrize("run_type", ["nowcast", "forecast", "forecast2"])
    def test_checklist(
        self,
        mock_read_avg_unstagger_rotate,
        mock_write_netcdf,
        mock_fix_perms,
        run_type,
        config,
        caplog,
    ):
        run_date = arrow.get("2018-09-01")
        parsed_args = SimpleNamespace(run_type=run_type, run_date=run_date)
        checklist = make_CHS_currents_file.make_CHS_currents_file(parsed_args, config)
        expected_filepath = f"{Path(config["results archive"][run_type])
            /run_date.format("DDMMMYY").lower()
            /"CHS_currents.nc"}"
        expected = {run_type: {"filename": expected_filepath, "run date": "2018-09-01"}}
        assert checklist == expected
