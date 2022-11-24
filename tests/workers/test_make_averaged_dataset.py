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


"""Unit tests for SalishSeaCast make_averaged_dataset worker.
"""
import logging
import os
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest
from nemo_nowcast import WorkerError

from nowcast.workers import make_averaged_dataset


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                averaged datasets:
                  reshapr config dir: config/reshapr/
                  day:
                    biology:
                      reshapr config: day-average_202111_biology.yaml
                      file pattern: "SalishSea_1d_{yyyymmdd}_{yyyymmdd}_biol_T.nc"
                    chemistry:
                      reshapr config: day-average_202111_chemistry.yaml
                      file pattern: "SalishSea_1d_{yyyymmdd}_{yyyymmdd}_chem_T.nc"
                    physics:
                      reshapr config: day-average_202111_physics.yaml
                      file pattern: "SalishSea_1d_{yyyymmdd}_{yyyymmdd}_grid_T.nc"
                  month:
                    biology:
                      reshapr config: month-average_202111_biology.yaml
                      file pattern: "SalishSeaCast_1m_biol_T_{yyyymmdd}_{yyyymmdd}.nc"
                    chemistry:
                      reshapr config: month-average_202111_chemistry.yaml
                      file pattern: "SalishSeaCast_1m_chem_T_{yyyymmdd}_{yyyymmdd}.nc"
                    physics:
                      reshapr config: month-average_202111_physics.yaml
                      file pattern: "SalishSeaCast_1m_grid_T_{yyyymmdd}_{yyyymmdd}.nc"
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(make_averaged_dataset, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = make_averaged_dataset.main()

        assert worker.name == "make_averaged_dataset"
        assert worker.description.startswith(
            "SalishSeaCast worker that creates a down-sampled time-series dataset netCDF4 file"
        )

    def test_add_host_name_arg(self, mock_worker):
        worker = make_averaged_dataset.main()

        assert worker.cli.parser._actions[3].dest == "host_name"
        assert worker.cli.parser._actions[3].help

    def test_add_avg_time_interval_arg(self, mock_worker):
        worker = make_averaged_dataset.main()

        assert worker.cli.parser._actions[4].dest == "avg_time_interval"
        assert worker.cli.parser._actions[4].choices == {"day", "month"}
        assert worker.cli.parser._actions[4].help

    def test_add_reshapr_var_group_arg(self, mock_worker):
        worker = make_averaged_dataset.main()

        assert worker.cli.parser._actions[5].dest == "reshapr_var_group"
        assert worker.cli.parser._actions[5].choices == {
            "biology",
            "chemistry",
            "physics",
        }
        assert worker.cli.parser._actions[5].help

    def test_add_run_date_option(self, mock_worker):
        worker = make_averaged_dataset.main()
        assert worker.cli.parser._actions[6].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[6].type == expected
        assert worker.cli.parser._actions[6].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[6].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_averaged_dataset" in prod_config["message registry"]["workers"]

        msg_registry = prod_config["message registry"]["workers"][
            "make_averaged_dataset"
        ]

        assert msg_registry["checklist key"] == "averaged dataset"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "make_averaged_dataset"
        ]

        assert list(msg_registry.keys()) == [
            "checklist key",
            "success",
            "failure",
            "crash",
        ]

    def test_averaged_datasets(self, prod_config):
        averaged_datasets = prod_config["averaged datasets"]
        expected = "/SalishSeaCast/SalishSeaNowcast/config/reshapr/"

        assert averaged_datasets["reshapr config dir"] == expected

    @pytest.mark.parametrize(
        "var_group, config_yaml, file_pattern",
        (
            (
                "biology",
                "day-average_202111_biology.yaml",
                "SalishSea_1d_{yyyymmdd}_{yyyymmdd}_biol_T.nc",
            ),
            (
                "chemistry",
                "day-average_202111_chemistry.yaml",
                "SalishSea_1d_{yyyymmdd}_{yyyymmdd}_chem_T.nc",
            ),
            (
                "physics",
                "day-average_202111_physics.yaml",
                "SalishSea_1d_{yyyymmdd}_{yyyymmdd}_grid_T.nc",
            ),
        ),
    )
    def test_day_averaged_datasets(
        self, var_group, config_yaml, file_pattern, prod_config
    ):
        day_averaged_datasets = prod_config["averaged datasets"]["day"]

        assert day_averaged_datasets[var_group]["reshapr config"] == config_yaml
        assert day_averaged_datasets[var_group]["file pattern"] == file_pattern
        reshapr_config_dir = Path("config/reshapr/")
        assert (reshapr_config_dir / config_yaml).is_file()

    @pytest.mark.parametrize(
        "var_group, config_yaml, file_pattern",
        (
            (
                "biology",
                "month-average_202111_biology.yaml",
                "SalishSeaCast_1m_biol_T_{yyyymmdd}_{yyyymmdd}.nc",
            ),
            (
                "chemistry",
                "month-average_202111_chemistry.yaml",
                "SalishSeaCast_1m_chem_T_{yyyymmdd}_{yyyymmdd}.nc",
            ),
            (
                "physics",
                "month-average_202111_physics.yaml",
                "SalishSeaCast_1m_grid_T_{yyyymmdd}_{yyyymmdd}.nc",
            ),
        ),
    )
    def test_month_averaged_datasets(
        self, var_group, config_yaml, file_pattern, prod_config
    ):
        month_averaged_datasets = prod_config["averaged datasets"]["month"]

        assert month_averaged_datasets[var_group]["reshapr config"] == config_yaml
        assert month_averaged_datasets[var_group]["file pattern"] == file_pattern
        reshapr_config_dir = Path("config/reshapr/")
        assert (reshapr_config_dir / config_yaml).is_file()


class TestSuccess:
    """Unit tests for success() function."""

    @pytest.mark.parametrize(
        "avg_time_interval, reshapr_var_group",
        (
            ("day", "biology"),
            ("day", "chemistry"),
            ("day", "physics"),
        ),
    )
    def test_day_average_success(self, avg_time_interval, reshapr_var_group, caplog):
        parsed_args = SimpleNamespace(
            avg_time_interval=avg_time_interval,
            run_date=arrow.get("2022-11-10"),
            reshapr_var_group=reshapr_var_group,
            host_name="test.host",
        )
        caplog.set_level(logging.DEBUG)

        msg_type = make_averaged_dataset.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        avg_time_interval = parsed_args.avg_time_interval
        reshapr_var_group = parsed_args.reshapr_var_group
        host_name = parsed_args.host_name
        expected = f"{avg_time_interval}-averaged dataset for 10-Nov-2022 {reshapr_var_group} created on {host_name}"
        assert caplog.messages[0] == expected
        assert msg_type == "success"

    @pytest.mark.parametrize(
        "avg_time_interval, reshapr_var_group",
        (
            ("month", "biology"),
            ("month", "chemistry"),
            ("month", "physics"),
        ),
    )
    def test_month_average_success(self, avg_time_interval, reshapr_var_group, caplog):
        parsed_args = SimpleNamespace(
            avg_time_interval=avg_time_interval,
            run_date=arrow.get("2022-11-01"),
            reshapr_var_group=reshapr_var_group,
            host_name="test.host",
        )
        caplog.set_level(logging.DEBUG)

        msg_type = make_averaged_dataset.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        avg_time_interval = parsed_args.avg_time_interval
        reshapr_var_group = parsed_args.reshapr_var_group
        host_name = parsed_args.host_name
        expected = f"{avg_time_interval}-averaged dataset for Nov-2022 {reshapr_var_group} created on {host_name}"
        assert caplog.messages[0] == expected
        assert msg_type == "success"


class TestFailure:
    """Unit tests for failure() function."""

    @pytest.mark.parametrize(
        "avg_time_interval, reshapr_var_group",
        (
            ("day", "biology"),
            ("day", "chemistry"),
            ("day", "physics"),
        ),
    )
    def test_day_average_failure(self, avg_time_interval, reshapr_var_group, caplog):
        parsed_args = SimpleNamespace(
            avg_time_interval=avg_time_interval,
            run_date=arrow.get("2022-11-10"),
            reshapr_var_group=reshapr_var_group,
            host_name="test.host",
        )
        caplog.set_level(logging.DEBUG)

        msg_type = make_averaged_dataset.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        avg_time_interval = parsed_args.avg_time_interval
        reshapr_var_group = parsed_args.reshapr_var_group
        host_name = parsed_args.host_name
        expected = f"{avg_time_interval}-averaged dataset for 10-Nov-2022 {reshapr_var_group} creation on {host_name} failed"
        assert caplog.messages[0] == expected
        assert msg_type == "failure"

    @pytest.mark.parametrize(
        "avg_time_interval, reshapr_var_group",
        (
            ("month", "biology"),
            ("month", "chemistry"),
            ("month", "physics"),
        ),
    )
    def test_month_average_failure(self, avg_time_interval, reshapr_var_group, caplog):
        parsed_args = SimpleNamespace(
            avg_time_interval=avg_time_interval,
            run_date=arrow.get("2022-11-01"),
            reshapr_var_group=reshapr_var_group,
            host_name="test.host",
        )
        caplog.set_level(logging.DEBUG)

        msg_type = make_averaged_dataset.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        avg_time_interval = parsed_args.avg_time_interval
        reshapr_var_group = parsed_args.reshapr_var_group
        host_name = parsed_args.host_name
        expected = f"{avg_time_interval}-averaged dataset for Nov-2022 {reshapr_var_group} creation on {host_name} failed"
        assert caplog.messages[0] == expected
        assert msg_type == "failure"


class TestMakeAveragedDataset:
    """Unit tests for make_archived_dataset() function."""

    @pytest.mark.parametrize(
        "avg_time_interval, reshapr_var_group, nc_filename",
        (
            ("day", "biology", "SalishSea_1d_20221116_20221116_biol_T.nc"),
            ("day", "chemistry", "SalishSea_1d_20221116_20221116_chem_T.nc"),
            ("day", "physics", "SalishSea_1d_20221116_20221116_grid_T.nc"),
        ),
    )
    def test_day_avg_checklist(
        self,
        avg_time_interval,
        reshapr_var_group,
        nc_filename,
        config,
        tmp_path,
        caplog,
        log_output,
        monkeypatch,
    ):
        def mock_extract_netcdf(reshapr_config, reshapr_config_yaml):
            nc_dir = tmp_path / "16nov22"
            nc_dir.mkdir()
            nc_path = nc_dir / "test_results.nc"
            nc_path.write_bytes(b"")
            return nc_path

        monkeypatch.setattr(
            make_averaged_dataset.reshapr.api.v1.extract,
            "extract_netcdf",
            mock_extract_netcdf,
        )

        parsed_args = SimpleNamespace(
            avg_time_interval=avg_time_interval,
            run_date=arrow.get("2022-11-16"),
            reshapr_var_group=reshapr_var_group,
            host_name="test.host",
        )
        caplog.set_level(logging.DEBUG)

        checklist = make_averaged_dataset.make_averaged_dataset(parsed_args, config)

        assert caplog.records[0].levelname == "INFO"
        expected = f"creating {avg_time_interval}-averaged dataset for 16-Nov-2022 {reshapr_var_group} on test.host"
        assert caplog.messages[0] == expected
        expected = {
            "2022-11-16": {
                f"{avg_time_interval} {reshapr_var_group}": os.fspath(
                    tmp_path / "16nov22" / nc_filename
                )
            }
        }
        assert checklist == expected

    @pytest.mark.parametrize(
        "avg_time_interval, reshapr_var_group",
        (
            ("month", "biology"),
            ("month", "chemistry"),
            ("month", "physics"),
        ),
    )
    def test_month_avg_checklist(
        self,
        avg_time_interval,
        reshapr_var_group,
        config,
        tmp_path,
        caplog,
        log_output,
        monkeypatch,
    ):
        def mock_extract_netcdf(reshapr_config, reshapr_config_yaml):
            return tmp_path / "test_results.nc"

        monkeypatch.setattr(
            make_averaged_dataset.reshapr.api.v1.extract,
            "extract_netcdf",
            mock_extract_netcdf,
        )

        parsed_args = SimpleNamespace(
            avg_time_interval=avg_time_interval,
            run_date=arrow.get("2022-11-01"),
            reshapr_var_group=reshapr_var_group,
            host_name="test.host",
        )
        caplog.set_level(logging.DEBUG)

        checklist = make_averaged_dataset.make_averaged_dataset(parsed_args, config)

        assert caplog.records[0].levelname == "INFO"
        expected = f"creating {avg_time_interval}-averaged dataset for Nov-2022 {reshapr_var_group} on test.host"
        assert caplog.messages[0] == expected
        expected = {
            "2022-11-01": {
                f"{avg_time_interval} {reshapr_var_group}": os.fspath(
                    tmp_path / "test_results.nc"
                )
            }
        }
        assert checklist == expected

    def test_bad_month_avg_run_date(self, caplog):
        parsed_args = SimpleNamespace(
            avg_time_interval="month",
            run_date=arrow.get("2022-11-10"),
            reshapr_var_group="biology",
            host_name="test.host",
        )
        caplog.set_level(logging.DEBUG)

        with pytest.raises(WorkerError):
            make_averaged_dataset.make_averaged_dataset(parsed_args, config)

        assert caplog.records[0].levelname == "ERROR"
        expected = f"Month-averaging must start on the first day of a month but run_date = 2022-11-10"
        assert caplog.messages[0] == expected
