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


"""Unit tests for SalishSeaCast make_live_ocean_files worker."""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_live_ocean_files


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                temperature salinity:
                  download:
                    dest dir: forcing/LiveOcean/downloaded
                  bc dir: forcing/LiveOcean/boundary_conditions
                  file template: 'LiveOcean_v201905_{:y%Ym%md%d}.nc'
                  mesh mask: grid/mesh_mask201702.nc
                  parameter set: v201905
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(make_live_ocean_files, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = make_live_ocean_files.main()
        assert worker.name == "make_live_ocean_files"
        assert worker.description.startswith(
            "SalishSeaCast nowcast worker that produces hourly temperature and salinity"
        )

    def test_add_run_date_option(self, mock_worker):
        worker = make_live_ocean_files.main()
        assert worker.cli.parser._actions[3].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[3].type == expected
        expected = arrow.now().floor("day")
        assert worker.cli.parser._actions[3].default == expected
        assert worker.cli.parser._actions[3].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_live_ocean_files" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"][
            "make_live_ocean_files"
        ]
        assert msg_registry["checklist key"] == "Live Ocean boundary conditions"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "make_live_ocean_files"
        ]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success",
            "failure",
            "crash",
        ]

    def test_temperature_salinity_section(self, prod_config):
        temperature_salinity = prod_config["temperature salinity"]
        assert (
            temperature_salinity["bc dir"]
            == "/results/forcing/LiveOcean/boundary_conditions"
        )
        assert (
            temperature_salinity["file template"] == "LiveOcean_v201905_{:y%Ym%md%d}.nc"
        )
        assert (
            temperature_salinity["mesh mask"]
            == "/SalishSeaCast/grid/mesh_mask202108.nc"
        )
        assert (
            temperature_salinity["download"]["dest dir"]
            == "/results/forcing/LiveOcean/downloaded/"
        )
        assert temperature_salinity["parameter set"] == "v201905"


class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, caplog):
        run_date = arrow.get("2020-02-15")
        parsed_args = SimpleNamespace(run_date=run_date)
        caplog.set_level(logging.DEBUG)

        msg_type = make_live_ocean_files.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"{run_date.format('YYYY-MM-DD')} Live Ocean western boundary conditions files created"
        assert caplog.messages[0] == expected
        assert msg_type == "success"


class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, caplog):
        run_date = arrow.get("2020-02-15")
        parsed_args = SimpleNamespace(run_date=run_date)
        caplog.set_level(logging.DEBUG)

        msg_type = make_live_ocean_files.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = (
            f"{run_date.format('YYYY-MM-DD')} Live Ocean western boundary conditions files "
            f"preparation failed"
        )
        assert caplog.messages[0] == expected
        assert msg_type == "failure"


class TestMakeLiveOceanFiles:
    """Unit test for make_live_ocean_files() function."""

    @staticmethod
    @pytest.fixture
    def mock_create_LiveOcean_TS_BCs(config, monkeypatch):
        def _mock_create_LiveOcean_TS_BCs(
            date, file_template, meshfilename, bc_dir, LO_dir, LO_to_SSC_parameters
        ):
            return (
                "forcing/LiveOcean/boundary_conditions/LiveOcean_v201905_y2024m07d26.nc"
            )

        monkeypatch.setattr(
            make_live_ocean_files,
            "create_LiveOcean_TS_BCs",
            _mock_create_LiveOcean_TS_BCs,
        )

    def test_checklist(self, mock_create_LiveOcean_TS_BCs, config, caplog):
        run_date = arrow.get("2024-07-26")
        parsed_args = SimpleNamespace(run_date=run_date)
        filename = config["temperature salinity"]["file template"].format(
            run_date.datetime
        )
        bc_dir = config["temperature salinity"]["bc dir"]
        filepath = f"{bc_dir}/{filename}"
        caplog.set_level(logging.DEBUG)

        checklist = make_live_ocean_files.make_live_ocean_files(parsed_args, config)
        assert checklist == {"temperature & salinity": filepath}

    def test_log_messages(self, mock_create_LiveOcean_TS_BCs, config, caplog):
        run_date = arrow.get("2024-07-26")
        parsed_args = SimpleNamespace(run_date=run_date)
        filename = config["temperature salinity"]["file template"].format(
            run_date.datetime
        )
        bc_dir = config["temperature salinity"]["bc dir"]
        filepath = f"{bc_dir}/{filename}"
        caplog.set_level(logging.DEBUG)

        make_live_ocean_files.make_live_ocean_files(parsed_args, config)
        assert caplog.records[0].levelname == "INFO"
        expected = (
            f"Creating T&S western boundary conditions file from "
            f"{run_date.format('YYYY-MM-DD')} Live Ocean run"
        )
        assert caplog.messages[0] == expected
        assert caplog.records[1].levelname == "INFO"
        assert (
            caplog.messages[1]
            == f"Stored T&S western boundary conditions file: {filepath}"
        )
