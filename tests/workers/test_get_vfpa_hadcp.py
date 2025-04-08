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


"""Unit tests for SalishSeaCast get_vfpa_hadcp worker."""
import logging
import os
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest
import xarray

from nowcast.workers import get_vfpa_hadcp


@pytest.fixture
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                observations:
                  hadcp data:
                    csv dir: opp/obs/AISDATA/
                    dest dir: opp/obs/AISDATA/netcdf/
                    filepath template: 'VFPA_2ND_NARROWS_HADCP_2s_{yyyymm}.nc'
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(get_vfpa_hadcp, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = get_vfpa_hadcp.main()

        assert worker.name == "get_vfpa_hadcp"
        assert worker.description.startswith(
            "SalishSeaCast worker that processes VFPA HADCP observations from the 2nd Narrows Rail Bridge"
        )

    def test_add_data_date_option(self, mock_worker):
        worker = get_vfpa_hadcp.main()
        assert worker.cli.parser._actions[3].dest == "data_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[3].type == expected
        assert worker.cli.parser._actions[3].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[3].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "get_vfpa_hadcp" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["get_vfpa_hadcp"]
        assert msg_registry["checklist key"] == "VFPA HADCP data"

    @pytest.mark.parametrize("msg", ("success", "failure", "crash"))
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["get_vfpa_hadcp"]
        assert msg in msg_registry

    def test_observations(self, prod_config):
        assert "hadcp data" in prod_config["observations"]
        hadcp_obs = prod_config["observations"]["hadcp data"]
        assert hadcp_obs["csv dir"] == "/opp/observations/AISDATA/"
        assert hadcp_obs["dest dir"] == "/opp/observations/AISDATA/netcdf/"
        assert hadcp_obs["filepath template"] == "VFPA_2ND_NARROWS_HADCP_2s_{yyyymm}.nc"


class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, caplog):
        parsed_args = SimpleNamespace(data_date=arrow.get("2018-10-01"))
        caplog.set_level(logging.DEBUG)
        msg_type = get_vfpa_hadcp.success(parsed_args)
        assert caplog.records[0].levelname == "INFO"
        expected = "VFPA HADCP observations added to 2018-10 netcdf file"
        assert caplog.messages[0] == expected
        assert msg_type == "success"


class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, caplog):
        parsed_args = SimpleNamespace(data_date=arrow.get("2018-10-01"))
        caplog.set_level(logging.DEBUG)
        msg_type = get_vfpa_hadcp.failure(parsed_args)
        assert caplog.records[0].levelname == "CRITICAL"
        expected = "Addition of VFPA HADCP observations to 2018-10 netcdf file failed"
        assert caplog.messages[0] == expected
        assert msg_type == "failure"


class TestGetVFPA_HADCP:
    """Unit test for get_vfpa_hadcp() function."""

    @staticmethod
    @pytest.fixture
    def mock_make_hour_dataset(monkeypatch):

        def _mock_make_hour_dataset(csv_dir, utc_start_hr, place):
            return xarray.Dataset()

        monkeypatch.setattr(
            get_vfpa_hadcp, "_make_hour_dataset", _mock_make_hour_dataset
        )

    @staticmethod
    @pytest.fixture
    def mock_write_netcdf(monkeypatch):
        def _mock_write_netcdf(ds, nc_filepath):
            return

        monkeypatch.setattr(get_vfpa_hadcp, "_write_netcdf", _mock_write_netcdf)

    @pytest.mark.parametrize("nc_file_exists", (True, False))
    def test_log_messages(
        self,
        nc_file_exists,
        mock_make_hour_dataset,
        mock_write_netcdf,
        config,
        caplog,
        tmp_path,
        monkeypatch,
    ):
        dest_dir = tmp_path
        monkeypatch.setitem(
            config["observations"]["hadcp data"], "dest dir", os.fspath(dest_dir)
        )
        nc_filepath = dest_dir / "VFPA_2ND_NARROWS_HADCP_2s_202407.nc"
        if nc_file_exists:
            nc_filepath.write_bytes(b"")
        parsed_args = SimpleNamespace(data_date=arrow.get("2024-07-13"))
        caplog.set_level(logging.DEBUG)
        get_vfpa_hadcp.get_vfpa_hadcp(parsed_args, config)
        assert caplog.records[0].levelname == "INFO"
        expected = (
            "processing VFPA HADCP data from 2nd Narrows Rail Bridge for 2024-07-13"
        )
        assert caplog.messages[0] == expected
        if not nc_file_exists:
            assert caplog.records[1].levelname == "INFO"
            assert caplog.records[1].message.startswith("created")
            assert caplog.messages[1].endswith("VFPA_2ND_NARROWS_HADCP_2s_202407.nc")
        for rec_num, hr in zip(range(2, 24), range(1, 23)):
            assert caplog.records[rec_num].levelname == "DEBUG"
            expected = f"no data for 2024-07-13 {hr:02d}:00 hour"
            assert caplog.messages[rec_num] == expected
        assert caplog.records[25].levelname == "INFO"
        expected = f"added VFPA HADCP data from 2nd Narrows Rail Bridge for 2024-07-13 to {nc_filepath}"
        assert caplog.messages[25] == expected

    def test_checklist_create(
        self,
        mock_make_hour_dataset,
        mock_write_netcdf,
        config,
        caplog,
        tmp_path,
        monkeypatch,
    ):
        dest_dir = tmp_path
        monkeypatch.setitem(
            config["observations"]["hadcp data"], "dest dir", os.fspath(dest_dir)
        )
        nc_filepath = dest_dir / "VFPA_2ND_NARROWS_HADCP_2s_201810.nc"
        parsed_args = SimpleNamespace(data_date=arrow.get("2018-10-01"))
        caplog.set_level(logging.DEBUG)
        checklist = get_vfpa_hadcp.get_vfpa_hadcp(parsed_args, config)
        expected = {
            "created": f"{nc_filepath}",
            "UTC date": "2018-10-01",
        }
        assert checklist == expected

    def test_checklist_extend(
        self,
        mock_make_hour_dataset,
        mock_write_netcdf,
        config,
        caplog,
        tmp_path,
        monkeypatch,
    ):
        dest_dir = tmp_path
        monkeypatch.setitem(
            config["observations"]["hadcp data"], "dest dir", os.fspath(dest_dir)
        )
        nc_filepath = dest_dir / "VFPA_2ND_NARROWS_HADCP_2s_201810.nc"
        xarray.DataArray().to_netcdf(nc_filepath)
        parsed_args = SimpleNamespace(data_date=arrow.get("2018-10-21"))
        caplog.set_level(logging.DEBUG)
        checklist = get_vfpa_hadcp.get_vfpa_hadcp(parsed_args, config)
        expected = {
            "extended": f"{nc_filepath}",
            "UTC date": "2018-10-21",
        }
        assert checklist == expected

    def test_checklist_missing_data(
        self,
        mock_make_hour_dataset,
        mock_write_netcdf,
        config,
        caplog,
        tmp_path,
        monkeypatch,
    ):
        dest_dir = tmp_path
        monkeypatch.setitem(
            config["observations"]["hadcp data"], "dest dir", os.fspath(dest_dir)
        )
        nc_filepath = dest_dir / "VFPA_2ND_NARROWS_HADCP_2s_201812.nc"
        nc_filepath.write_bytes(b"")
        caplog.set_level(logging.DEBUG)
        parsed_args = SimpleNamespace(data_date=arrow.get("2018-12-23"))
        checklist = get_vfpa_hadcp.get_vfpa_hadcp(parsed_args, config)
        expected = {
            "missing data": f"{nc_filepath}",
            "UTC date": "2018-12-23",
        }
        assert checklist == expected
