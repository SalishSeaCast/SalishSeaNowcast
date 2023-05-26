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
import pandas
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
                rivers:
                  SOG river files:
                    HomathkoMouth: forcing/rivers/observations/Homathko_Mouth_flow
                    SquamishBrackendale: forcing/rivers/observations/Squamish_Brackendale_flow
                    TheodosiaScotty: forcing/rivers/observations/Theodosia_Scotty_flow
                    TheodosiaBypass: forcing/rivers/observations/Theodosia_Bypass_flow
                    TheodosiaDiversion: forcing/rivers/observations/Theodosia_Diversion_flow
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

    def test_SOG_river_files(self, prod_config):
        SOG_river_files = prod_config["rivers"]["SOG river files"]

        expected = {
            "Capilano": "/opp/observations/rivers/Capilano/Caplilano_08GA010_day_avg_flow",
            "ChilliwackVedder": "/results/forcing/rivers/observations/Chilliwack_Vedder_flow",
            "ClowhomClowhomLake": "/results/forcing/rivers/observations/Clowhom_ClowhomLake_flow",
            "Englishman": "/data/dlatorne/SOG-projects/SOG-forcing/ECget/Englishman_flow",
            "Fraser": "/data/dlatorne/SOG-projects/SOG-forcing/ECget/Fraser_flow",
            "GreenwaterGreenwater": "/results/forcing/rivers/observations/Greenwater_Greenwater_flow",
            "HomathkoMouth": "/results/forcing/rivers/observations/Homathko_Mouth_flow",
            "NisquallyMcKenna": "/results/forcing/rivers/observations/Nisqually_McKenna_flow",
            "NicomeklLangley": "/results/forcing/rivers/observations/Nicomekl_Langley_flow",
            "RobertsCreek": "/results/forcing/rivers/observations/RobertsCreek_flow",
            "SalmonSayward": "/results/forcing/rivers/observations/Salmon_Sayward_flow",
            "SanJuanPortRenfrew": "/results/forcing/rivers/observations/SanJuan_PortRenfrew_flow",
            "SkagitMountVernon": "/results/forcing/rivers/observations/Skagit_MountVernon_flow",
            "SnohomishMonroe": "/results/forcing/rivers/observations/Snohomish_Monroe_flow",
            "SquamishBrackendale": "/results/forcing/rivers/observations/Squamish_Brackendale_flow",
            "TheodosiaScotty": "/results/forcing/rivers/observations/Theodosia_Scotty_flow",
            "TheodosiaBypass": "/results/forcing/rivers/observations/Theodosia_Bypass_flow",
            "TheodosiaDiversion": "/results/forcing/rivers/observations/Theodosia_Diversion_flow",
        }
        assert SOG_river_files == expected


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

    def test_watershed_from_river(self):
        expected = {
            "bute": {"primary": 2.015},
            "jervis": {"primary": 8.810, "secondary": 140.3},
            "howe": {"primary": 2.276},
            "jdf": {"primary": 8.501},
            "evi_n": {"primary": 10.334},
            "evi_s": {"primary": 24.60},
            "toba": {"primary": 0.4563, "secondary": 14.58},
            "skagit": {"primary": 1.267, "secondary": 1.236},
            "puget": {"primary": 8.790, "secondary": 29.09},
            "fraser": {"primary": 1.161, "secondary": 162, "nico_into_fraser": 0.83565},
        }

        assert make_v202111_runoff_file.watershed_from_river == expected


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


class TestDoFraser:
    """Unit tests for _do_Fraser()."""

    def test_no_patches(self, config, monkeypatch):
        mock_dataframes = [
            # Primary river
            pandas.DataFrame(
                # Fraser
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-19"),
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [6.625833e02],
                },
            ),
            # Secondary river
            pandas.DataFrame(
                # Nicomekl_Langley
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-19"),
                    ],
                    name="date",
                ),
                data={
                    "Secondary River Flow": [2.402962e00],
                },
            ),
        ]

        def mock_read_river(river_name, ps, config_):
            return mock_dataframes.pop(0)

        monkeypatch.setattr(make_v202111_runoff_file, "_read_river", mock_read_river)

        obs_date = arrow.get("2023-02-19")

        fraser_flux, secondary_flux = make_v202111_runoff_file._do_fraser(
            obs_date, config
        )

        assert fraser_flux == pytest.approx(1094.56091294)
        assert secondary_flux == pytest.approx(63.978142)

    def test_persist_fraser(self, config, monkeypatch):
        mock_dataframes = [
            # Primary river
            pandas.DataFrame(
                # Fraser
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-18"),
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [6.528406e02],
                },
            ),
            # Secondary river
            pandas.DataFrame(
                # Nicomekl_Langley
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-19"),
                    ],
                    name="date",
                ),
                data={
                    "Secondary River Flow": [2.402962e00],
                },
            ),
        ]

        def mock_read_river(river_name, ps, config_):
            return mock_dataframes.pop(0)

        monkeypatch.setattr(make_v202111_runoff_file, "_read_river", mock_read_river)

        mock_river_flows = [
            # Fraser
            6.528406e02,
            # Nicomekl_Langley
            2.402962e00,
        ]

        def mock_get_river_flow(river_name, river_flow, obs_date, config):
            return mock_river_flows.pop(0)

        monkeypatch.setattr(
            make_v202111_runoff_file, "_get_river_flow", mock_get_river_flow
        )

        obs_date = arrow.get("2023-02-19")

        fraser_flux, secondary_flux = make_v202111_runoff_file._do_fraser(
            obs_date, config
        )

        assert fraser_flux == pytest.approx(1083.249638)
        assert secondary_flux == pytest.approx(63.978142)

    def test_patch_nicomekl(self, config, monkeypatch):
        mock_dataframes = [
            # Primary river
            pandas.DataFrame(
                # Fraser
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-19"),
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [6.625833e02],
                },
            ),
            # Secondary river
            pandas.DataFrame(
                # Nicomekl_Langley
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-18"),
                    ],
                    name="date",
                ),
                data={
                    "Secondary River Flow": [3.095674e00],
                },
            ),
        ]

        def mock_read_river(river_name, ps, config_):
            return mock_dataframes.pop(0)

        monkeypatch.setattr(make_v202111_runoff_file, "_read_river", mock_read_river)
        mock_river_flows = [
            # Fraser
            6.625833e02,
            # Nicomekl_Langley
            2.402962e00,
        ]

        def mock_get_river_flow(river_name, river_flow, obs_date, config):
            return mock_river_flows.pop(0)

        monkeypatch.setattr(
            make_v202111_runoff_file, "_get_river_flow", mock_get_river_flow
        )

        obs_date = arrow.get("2023-02-19")

        fraser_flux, secondary_flux = make_v202111_runoff_file._do_fraser(
            obs_date, config
        )

        assert fraser_flux == pytest.approx(1094.56091294)
        assert secondary_flux == pytest.approx(63.978142)


class TestDoARiverPair:
    """Unit tests for _do_a_river_pair()."""

    def test_primary_river_only_no_patch_required(self, config, monkeypatch):
        def mock_read_river(river_name, ps, config_):
            return pandas.DataFrame(
                # Homathko_Mouth
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-13"),
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [4.444965e01],
                },
            )

        monkeypatch.setattr(make_v202111_runoff_file, "_read_river", mock_read_river)

        watershed_name = "bute"
        obs_date = arrow.get("2023-02-13")
        primary_river_name = "Homathko_Mouth"
        secondary_river_name = None

        watershed_flux = make_v202111_runoff_file._do_a_river_pair(
            watershed_name, obs_date, primary_river_name, config, secondary_river_name
        )

        assert watershed_flux == pytest.approx(89.566045)

    def test_primary_river_patched(self, config, monkeypatch):
        def mock_read_river(river_name, ps, config_):
            return pandas.DataFrame(
                # Homathko_Mouth
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-17"),
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [4.329455e01],
                },
            )

        monkeypatch.setattr(make_v202111_runoff_file, "_read_river", mock_read_river)

        def mock_patch_missing_obs(river_name, river_flow, obs_date, config):
            mock_flux = 5.338837e01
            return mock_flux

        monkeypatch.setattr(
            make_v202111_runoff_file, "_patch_missing_obs", mock_patch_missing_obs
        )

        watershed_name = "bute"
        obs_date = arrow.get("2023-02-18")
        primary_river_name = "Homathko_Mouth"
        secondary_river_name = None

        watershed_flux = make_v202111_runoff_file._do_a_river_pair(
            watershed_name, obs_date, primary_river_name, config, secondary_river_name
        )

        assert watershed_flux == pytest.approx(107.577565)

    def test_primary_and_secondary_rivers_no_patches(self, config, monkeypatch):
        mock_dataframes = [
            # Primary river
            pandas.DataFrame(
                # Clowhom_ClowhomLake
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-13"),
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [5.549688e00],
                },
            ),
            # Secondary river
            pandas.DataFrame(
                # RobertsCreek
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-13"),
                    ],
                    name="date",
                ),
                data={
                    "Secondary River Flow": [9.963607e-01],
                },
            ),
        ]

        def mock_read_river(river_name, ps, config_):
            return mock_dataframes.pop(0)

        monkeypatch.setattr(make_v202111_runoff_file, "_read_river", mock_read_river)

        watershed_name = "jervis"
        obs_date = arrow.get("2023-02-13")
        primary_river_name = "Clowhom_ClowhomLake"
        secondary_river_name = "RobertsCreek"

        watershed_flux = make_v202111_runoff_file._do_a_river_pair(
            watershed_name, obs_date, primary_river_name, config, secondary_river_name
        )

        assert watershed_flux == pytest.approx(188.682157)

    def test_secondary_Theodosia_no_patches(self, config, monkeypatch):
        def mock_read_river(river_name, ps, config_):
            return pandas.DataFrame(
                # Homathko_Mouth
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-18"),
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [4.175144e01],
                },
            )

        monkeypatch.setattr(make_v202111_runoff_file, "_read_river", mock_read_river)

        def mock_read_river_Theodosia(config_):
            return pandas.DataFrame(
                # Theodosia
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-18"),
                    ],
                    name="date",
                ),
                data={
                    "Secondary River Flow": [5.39236e0],
                },
            )

        monkeypatch.setattr(
            make_v202111_runoff_file, "_read_river_Theodosia", mock_read_river_Theodosia
        )

        watershed_name = "toba"
        obs_date = arrow.get("2023-02-18")
        primary_river_name = "Homathko_Mouth"
        secondary_river_name = "Theodosia"

        watershed_flux = make_v202111_runoff_file._do_a_river_pair(
            watershed_name, obs_date, primary_river_name, config, secondary_river_name
        )

        assert watershed_flux == pytest.approx(97.67179087)

    def test_secondary_river_patched(self, config, monkeypatch):
        mock_dataframes = [
            # Primary river
            pandas.DataFrame(
                # Clowhom_ClowhomLake
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-18"),
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [3.391116e00],
                },
            ),
            # Secondary river
            pandas.DataFrame(
                # RobertsCreek
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-17"),
                    ],
                    name="date",
                ),
                data={
                    "Secondary River Flow": [6.383818e-01],
                },
            ),
        ]

        def mock_read_river(river_name, ps, config_):
            return mock_dataframes.pop(0)

        monkeypatch.setattr(make_v202111_runoff_file, "_read_river", mock_read_river)

        def mock_patch_missing_obs(river_name, river_flow, obs_date, config):
            mock_flux = 8.285429e-01
            return mock_flux

        monkeypatch.setattr(
            make_v202111_runoff_file, "_patch_missing_obs", mock_patch_missing_obs
        )

        watershed_name = "jervis"
        obs_date = arrow.get("2023-02-13")
        primary_river_name = "Clowhom_ClowhomLake"
        secondary_river_name = "RobertsCreek"

        watershed_flux = make_v202111_runoff_file._do_a_river_pair(
            watershed_name, obs_date, primary_river_name, config, secondary_river_name
        )

        assert watershed_flux == pytest.approx(123.54403)


@pytest.mark.parametrize(
    "flow_col_label", ("Primary River Flow", "Secondary River Flow")
)
class TestGetRiverFlow:
    """Unit tests for _get_river_flow()."""

    def test_get_river_flow(self, flow_col_label, config):
        river_name = "SanJuan_PortRenfrew"
        river_df = pandas.DataFrame(
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-13"),
                    pandas.to_datetime("2023-02-14"),
                    pandas.to_datetime("2023-02-15"),
                ],
                name="date",
            ),
            data={
                flow_col_label: [
                    6.963472e01,
                    5.954271e01,
                    5.195243e01,
                ],
            },
        )
        obs_date = arrow.get("2023-02-15")

        river_flow = make_v202111_runoff_file._get_river_flow(
            river_name, river_df, obs_date, config
        )

        assert river_flow == pytest.approx(5.195243e01)

    def test_patch(self, flow_col_label, config, caplog, monkeypatch):
        def mock_patch_missing_obs(river_name, river_flow, obs_date, config):
            flux = 4.749479e01
            return flux

        monkeypatch.setattr(
            make_v202111_runoff_file, "_patch_missing_obs", mock_patch_missing_obs
        )

        river_name = "SanJuan_PortRenfrew"
        river_df = pandas.DataFrame(
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-13"),
                    pandas.to_datetime("2023-02-14"),
                    pandas.to_datetime("2023-02-15"),
                ],
                name="date",
            ),
            data={
                flow_col_label: [
                    6.963472e01,
                    5.954271e01,
                    5.195243e01,
                ],
            },
        )
        obs_date = arrow.get("2023-02-16")
        caplog.set_level(logging.DEBUG)

        river_flow = make_v202111_runoff_file._get_river_flow(
            river_name, river_df, obs_date, config
        )

        assert caplog.records[0].levelname == "ERROR"
        assert (
            caplog.messages[0]
            == "no 2023-02-16 discharge obs for SanJuan_PortRenfrew: patching"
        )

        assert river_flow == pytest.approx(4.749479e01)


class TestReadRiver:
    """Unit tests for _read_river()."""

    @pytest.mark.parametrize(
        "ps, expected_col_name",
        (
            ("primary", "Primary River Flow"),
            ("secondary", "Secondary River Flow"),
        ),
    )
    def test_read_river(self, ps, expected_col_name, config, monkeypatch):
        def mock_read_river_csv(filename):
            return pandas.DataFrame(
                {
                    "year": 1923,
                    "month": 2,
                    "day": [20, 21],
                    "flow": [1.13e1, 5.97e1],
                }
            )

        monkeypatch.setattr(
            make_v202111_runoff_file, "_read_river_csv", mock_read_river_csv
        )

        river_name = "Squamish_Brackendale"

        river_flow = make_v202111_runoff_file._read_river(river_name, ps, config)

        expected = pandas.DataFrame(
            data={
                expected_col_name: [1.13e1, 5.97e1],
            },
            index=pandas.Index(
                data=[
                    pandas.to_datetime("1923-02-20"),
                    pandas.to_datetime("1923-02-21"),
                ],
                name="date",
            ),
        )
        pandas.testing.assert_frame_equal(river_flow, expected)


class TestParseLongCSVLine:
    """Unit test for _parse_long_csv_line()."""

    def test_parse_long_csv_line(self):
        line = make_v202111_runoff_file._parse_long_csv_line(
            "1923 02 13 1.100000E+01 B".split()
        )

        assert line == "1923 02 13 1.100000E+01".split()


class TestSetDateAsIndex:
    """Unit test for _set_date_as_index()."""

    def test_set_date_as_index(self):
        river_flow = pandas.DataFrame(
            {
                "year": 1923,
                "month": 2,
                "day": [20, 21],
                "flow": [1.13e1, 5.97e1],
            }
        )

        make_v202111_runoff_file._set_date_as_index(river_flow)

        expected = pandas.DataFrame(
            data={
                "flow": [1.13e1, 5.97e1],
            },
            index=pandas.Index(
                data=[
                    pandas.to_datetime("1923-02-20"),
                    pandas.to_datetime("1923-02-21"),
                ],
                name="date",
            ),
        )
        pandas.testing.assert_frame_equal(river_flow, expected)
