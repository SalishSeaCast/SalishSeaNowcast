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
"""Unit tests for Salish Sea NEMO nowcast make_live_ocean_files worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_live_ocean_files


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests.
    """
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


@patch("nowcast.workers.make_live_ocean_files.NowcastWorker", spec=True)
class TestMain:
    """Unit tests for main() function.
    """

    def test_instantiate_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_live_ocean_files.main()
        args, kwargs = m_worker.call_args
        assert args == ("make_live_ocean_files",)
        assert "description" in kwargs

    def test_init_cli(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_live_ocean_files.main()
        m_worker().init_cli.assert_called_once_with()

    def test_add_run_date_arg(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_live_ocean_files.main()
        args, kwargs = m_worker().cli.add_date_option.call_args_list[0]
        assert args == ("--run-date",)
        assert kwargs["default"] == arrow.now().floor("day")
        assert "help" in kwargs

    def test_run_worker(self, m_worker):
        m_worker().cli = Mock(name="cli")
        make_live_ocean_files.main()
        args, kwargs = m_worker().run.call_args
        expected = (
            make_live_ocean_files.make_live_ocean_files,
            make_live_ocean_files.success,
            make_live_ocean_files.failure,
        )
        assert args == expected


class TestConfig:
    """Unit tests for production YAML config file elements related to worker.
    """

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
            == "/SalishSeaCast/grid/mesh_mask201702.nc"
        )
        assert (
            temperature_salinity["download"]["dest dir"]
            == "/results/forcing/LiveOcean/downloaded"
        )
        assert temperature_salinity["parameter set"] == "v201905"


class TestSuccess:
    """Unit test for success() function.
    """

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
    """Unit test for failure() function.
    """

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


@patch(
    "nowcast.workers.make_live_ocean_files.LiveOcean_parameters.set_parameters",
    autospec=True,
)
@patch("nowcast.workers.make_live_ocean_files.create_LiveOcean_TS_BCs", spec=True)
class TestMakeLiveOceanFiles:
    """Unit test for make_live_ocean_files() function.
    """

    def test_checklist(self, m_create_ts, m_set_params, config, caplog):
        run_date = arrow.get("2020-02-15")
        parsed_args = SimpleNamespace(run_date=run_date)
        filename = config["temperature salinity"]["file template"].format(
            run_date.datetime
        )
        m_create_ts.return_value = [filename]

        checklist = make_live_ocean_files.make_live_ocean_files(parsed_args, config)
        assert checklist == {"temperature & salinity": filename}

    def test_log_messages(self, m_create_ts, m_set_params, config, caplog):
        run_date = arrow.get("2019-02-15")
        parsed_args = SimpleNamespace(run_date=run_date)
        filename = config["temperature salinity"]["file template"].format(
            run_date.datetime
        )
        m_create_ts.return_value = [filename]
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
            == f"Stored T&S western boundary conditions file: {filename}"
        )
