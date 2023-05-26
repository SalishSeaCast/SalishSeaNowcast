#  Copyright 2013 – present by the SalishSeaCast Project contributors
#  and The University of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# SPDX-License-Identifier: Apache-2.0


"""Unit test for SalishSeaCast make_v202111_runoff_file worker.
"""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import make_v202111_runoff_file


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(make_v202111_runoff_file, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = make_v202111_runoff_file.main()

        assert worker.name == "make_v202111_runoff_file"
        assert worker.description.startswith(
            "SalishSeaCast worker that calculates NEMO runoff forcing file from day-averaged river"
        )

    def test_add_data_date_option(self, mock_worker):
        worker = make_v202111_runoff_file.main()

        assert worker.cli.parser._actions[3].dest == "data_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[3].type == expected
        assert worker.cli.parser._actions[3].default == arrow.now().floor("day")
        assert worker.cli.parser._actions[3].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_v202111_runoff_file" in prod_config["message registry"]["workers"]

    def test_checklist_key(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "make_v202111_runoff_file"
        ]

        assert msg_registry["checklist key"] == "v202111 rivers forcing"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "make_v202111_runoff_file"
        ]

        assert list(msg_registry.keys()) == [
            "checklist key",
            "success",
            "failure",
            "crash",
        ]


class TestModuleVariables:
    """
    Unit tests for config-type information that is stored in module variables in the
    make_v202111_runoff_file worker.
    """

    def test_watershed_names(self):
        expected = [
            "bute",
            "evi_n",
            "jervis",
            "evi_s",
            "howe",
            "jdf",
            "skagit",
            "puget",
            "toba",
            "fraser",
        ]

        assert make_v202111_runoff_file.watershed_names == expected

    def test_rivers_for_watershed(self):
        expected = {
            "bute": {"primary": "Homathko_Mouth", "secondary": None},
            "evi_n": {"primary": "Salmon_Sayward", "secondary": None},
            "jervis": {"primary": "Clowhom_ClowhomLake", "secondary": "RobertsCreek"},
            "evi_s": {"primary": "Englishman", "secondary": None},
            "howe": {"primary": "Squamish_Brackendale", "secondary": None},
            "jdf": {"primary": "SanJuan_PortRenfrew", "secondary": None},
            "skagit": {
                "primary": "Skagit_MountVernon",
                "secondary": "Snohomish_Monroe",
            },
            "puget": {
                "primary": "Nisqually_McKenna",
                "secondary": "Greenwater_Greenwater",
            },
            "toba": {"primary": "Homathko_Mouth", "secondary": "Theodosia"},
            "fraser": {"primary": "Fraser", "secondary": "Nicomekl_Langley"},
        }

        assert make_v202111_runoff_file.rivers_for_watershed == expected


class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, caplog):
        parsed_args = SimpleNamespace(data_date=arrow.get("2023-05-19"))
        caplog.set_level(logging.DEBUG)

        msg_type = make_v202111_runoff_file.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        assert caplog.messages[0] == "2023-05-19 runoff file creation completed"
        assert msg_type == "success"


class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, caplog):
        parsed_args = SimpleNamespace(data_date=arrow.get("2023-05-19"))
        caplog.set_level(logging.DEBUG)

        msg_type = make_v202111_runoff_file.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        assert caplog.messages[0] == "2023-05-19 runoff file creation failed"
        assert msg_type == "failure"


class TestMakeV202111RunoffFile:
    """Unit tests for make_v202111_runoff_file() function."""

    @staticmethod
    @pytest.fixture
    def mock_calc_watershed_flows(monkeypatch):
        def _mock_calc_watershed_flows(obs_date, config):
            pass

        monkeypatch.setattr(
            make_v202111_runoff_file,
            "_calc_watershed_flows",
            _mock_calc_watershed_flows,
        )

    def test_checklist(self, mock_calc_watershed_flows, config, caplog):
        parsed_args = SimpleNamespace(data_date=arrow.get("2023-05-19"))

        checklist = make_v202111_runoff_file.make_v202111_runoff_file(
            parsed_args, config
        )

        assert checklist == {}

    def test_log_messages(self, mock_calc_watershed_flows, config, caplog):
        parsed_args = SimpleNamespace(data_date=arrow.get("2023-05-26"))
        caplog.set_level(logging.DEBUG)

        make_v202111_runoff_file.make_v202111_runoff_file(parsed_args, config)

        assert caplog.records[0].levelname == "INFO"
        expected = (
            "calculating NEMO runoff forcing for 202108 bathymetry for 2023-05-26"
        )
        assert caplog.messages[0] == expected


class TestCalcWatershedFlows:
    """Unit test for _calc_watershed_flows()."""

    @staticmethod
    @pytest.fixture
    def mock_do_a_river_pair(monkeypatch):
        mock_watershed_flows = [
            ("bute", 83.3223456),
            ("evi_n", 354.56739384),
            ("jervis", 118.43897380000001),
            ("evi_s", 175.51416120000002),
            ("howe", 84.56446136),
            ("jdf", 380.26035625),
            ("skagit", 519.6378946),
            ("puget", 442.39027494999993),
            ("toba", 56.474250732),
        ]

        def _mock_do_a_river_pair(
            watershed_name,
            obs_date,
            primary_river_name,
            config,
            secondary_river_name=None,
        ):
            return mock_watershed_flows.pop(0)[1]

        monkeypatch.setattr(
            make_v202111_runoff_file, "_do_a_river_pair", _mock_do_a_river_pair
        )

    @staticmethod
    @pytest.fixture
    def mock_do_fraser(monkeypatch):
        def _mock_do_fraser(obs_date, config):
            return 1094.5609129386, 63.9781423614

        monkeypatch.setattr(make_v202111_runoff_file, "_do_fraser", _mock_do_fraser)

    def test_calc_watershed_flows(
        self, mock_do_a_river_pair, mock_do_fraser, config, monkeypatch
    ):
        obs_date = arrow.get("2023-02-19")

        flows = make_v202111_runoff_file._calc_watershed_flows(obs_date, config)

        expected = {
            "bute": 83.3223456,
            "evi_n": 354.56739384,
            "jervis": 118.43897380000001,
            "evi_s": 175.51416120000002,
            "howe": 84.56446136,
            "jdf": 380.26035625,
            "skagit": 519.6378946,
            "puget": 442.39027494999993,
            "toba": 56.474250732,
            "fraser": 1094.5609129386,
        }
        for name in make_v202111_runoff_file.watershed_names:
            assert flows[name] == pytest.approx(expected[name])
        assert flows["non_fraser"] == pytest.approx(63.9781423614)

    def test_log_messages(
        self, mock_do_a_river_pair, mock_do_fraser, config, caplog, monkeypatch
    ):
        obs_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        make_v202111_runoff_file._calc_watershed_flows(obs_date, config)

        assert caplog.records[0].levelname == "DEBUG"
        assert caplog.messages[0] == "no secondary river for bute watershed"
        assert caplog.messages[1] == "bute watershed flow: 83.322 m3 s-1"
        assert caplog.messages[2] == "no secondary river for evi_n watershed"
        assert caplog.messages[3] == "evi_n watershed flow: 354.567 m3 s-1"
        assert caplog.messages[4] == "jervis watershed flow: 118.439 m3 s-1"
        assert caplog.messages[5] == "no secondary river for evi_s watershed"
        assert caplog.messages[6] == "evi_s watershed flow: 175.514 m3 s-1"
        assert caplog.messages[7] == "no secondary river for howe watershed"
        assert caplog.messages[8] == "howe watershed flow: 84.564 m3 s-1"
        assert caplog.messages[9] == "no secondary river for jdf watershed"
        assert caplog.messages[10] == "jdf watershed flow: 380.260 m3 s-1"
        assert caplog.messages[11] == "skagit watershed flow: 519.638 m3 s-1"
        assert caplog.messages[12] == "puget watershed flow: 442.390 m3 s-1"
        assert caplog.messages[13] == "toba watershed flow: 56.474 m3 s-1"
        assert caplog.messages[14] == "fraser watershed flow: 1094.561 m3 s-1"
