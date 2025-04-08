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


"""Unit test for SalishSeaCast make_runoff_file worker."""
import logging
import os
import textwrap
from pathlib import Path
from types import SimpleNamespace

import arrow
import nemo_nowcast
import numpy
import pandas
import pytest
import xarray

from nowcast.workers import make_runoff_file


@pytest.fixture
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
                  rivers dir: results/forcing/rivers/
                  file templates:
                    b202108:  "R202108Dailies_{:y%Ym%md%d}.nc"
                  prop_dict modules:
                    b202108: salishsea_tools.river_202108

                run types:
                  nowcast-green:
                    coordinates: coordinates_seagrid_SalishSea201702.nc

                run:
                  enabled hosts:
                    salish-nowcast:
                      grid dir: /SalishSeaCast/grid/
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(make_runoff_file, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = make_runoff_file.main()

        assert worker.name == "make_runoff_file"
        assert worker.description.startswith(
            "SalishSeaCast worker that calculates NEMO runoff forcing file."
        )

    def test_add_data_date_option(self, mock_worker):
        worker = make_runoff_file.main()

        assert worker.cli.parser._actions[3].dest == "data_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[3].type == expected
        expected = arrow.now().floor("day").shift(days=-1)
        assert worker.cli.parser._actions[3].default == expected
        assert worker.cli.parser._actions[3].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "make_runoff_file" in prod_config["message registry"]["workers"]

    def test_checklist_key(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["make_runoff_file"]

        assert msg_registry["checklist key"] == "rivers forcing"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["make_runoff_file"]

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

    def test_rivers_dir(self, prod_config):
        assert prod_config["rivers"]["rivers dir"] == "/results/forcing/rivers/"

    def test_filename_tmpl(self, prod_config):
        filename_tmpl = prod_config["rivers"]["file templates"]["b202108"]

        assert filename_tmpl == "R202108Dailies_{:y%Ym%md%d}.nc"

    def test_prop_dict_modules(self, prod_config):
        prop_dict_module = prod_config["rivers"]["prop_dict modules"]["b202108"]

        assert prop_dict_module == "salishsea_tools.river_202108"

    def test_grid_dir(self, prod_config):
        grid_dir = Path(
            prod_config["run"]["enabled hosts"]["salish-nowcast"]["grid dir"]
        )

        expected = Path("/SalishSeaCast/grid/")
        assert grid_dir == expected

    def test_coords_file(self, prod_config):
        coords_file = prod_config["run types"]["nowcast-green"]["coordinates"]
        expected = "coordinates_seagrid_SalishSea201702.nc"
        assert coords_file == expected


class TestModuleVariables:
    """
    Unit tests for config-type information that is stored in module variables in the
    make_runoff_file worker.
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

        assert make_runoff_file.watershed_names == expected

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

        assert make_runoff_file.rivers_for_watershed == expected

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

        assert make_runoff_file.watershed_from_river == expected

    def test_theodosia_from_diversion_only(self):
        assert make_runoff_file.theodosia_from_diversion_only == 1.429

    def test_persist_until(self):
        expected = {
            # number of days to persist last observation for before switching to fitting strategies
            "Englishman": 0,
            "Fraser": 10_000,  # always persist
            "Theodosia": 0,
            "RobertsCreek": 0,
            "Salmon_Sayward": 0,
            "Squamish_Brackendale": 0,
            "SanJuan_PortRenfrew": 0,
            "Nisqually_McKenna": 4,
            "Snohomish_Monroe": 0,
            "Skagit_MountVernon": 3,
            "Homathko_Mouth": 1,
            "Nicomekl_Langley": 0,
            "Greenwater_Greenwater": 1,
            "Clowhom_ClowhomLake": 2,
        }

        assert make_runoff_file.persist_until == expected

    def test_patching_dictionary(self):
        expected = {
            "Englishman": ["fit", "persist"],
            "Fraser": ["persist"],
            "Theodosia": ["fit", "backup", "persist"],
            "RobertsCreek": ["fit", "persist"],
            "Salmon_Sayward": ["fit", "persist"],
            "Squamish_Brackendale": ["fit", "persist"],
            "SanJuan_PortRenfrew": ["fit", "backup", "persist"],
            "Nisqually_McKenna": ["fit", "persist"],
            "Snohomish_Monroe": ["fit", "persist"],
            "Skagit_MountVernon": ["fit", "persist"],
            "Homathko_Mouth": ["fit", "persist"],
            "Nicomekl_Langley": ["fit", "persist"],
            "Greenwater_Greenwater": ["fit", "persist"],
            "Clowhom_ClowhomLake": ["fit", "persist"],
        }

        assert make_runoff_file.patching_dictionary == expected

    def test_patching_fit_types(self):
        # Valid fit types are limited to cases handled in _patch_missing_ob()
        valid_fit_types = ["persist", "fit", "backup"]

        for fit_types in make_runoff_file.patching_dictionary.values():
            for fit_type in fit_types:
                assert fit_type in valid_fit_types

    def test_persist_is_last_patching_fit_type(self):
        for fit_types in make_runoff_file.patching_dictionary.values():
            assert fit_types[-1] == "persist"

    def test_matching_dictionary(self):
        expected = {
            "Englishman": "Salmon_Sayward",
            "Theodosia": "Clowhom_ClowhomLake",
            "RobertsCreek": "Englishman",
            "Salmon_Sayward": "Englishman",
            "Squamish_Brackendale": "Homathko_Mouth",
            "SanJuan_PortRenfrew": "Englishman",
            "Nisqually_McKenna": "Snohomish_Monroe",
            "Snohomish_Monroe": "Skagit_MountVernon",
            "Skagit_MountVernon": "Snohomish_Monroe",
            "Homathko_Mouth": "Squamish_Brackendale",
            "Nicomekl_Langley": "RobertsCreek",
            "Greenwater_Greenwater": "Snohomish_Monroe",
            "Clowhom_ClowhomLake": "Theodosia_Diversion",
        }

        assert make_runoff_file.matching_dictionary == expected

    def test_backup_dictionary(self):
        expected = {"SanJuan_PortRenfrew": "RobertsCreek", "Theodosia": "Englishman"}

        assert make_runoff_file.backup_dictionary == expected


class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, caplog):
        parsed_args = SimpleNamespace(data_date=arrow.get("2023-05-19"))
        caplog.set_level(logging.DEBUG)

        msg_type = make_runoff_file.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        assert caplog.messages[0] == "2023-05-19 runoff file creation completed"
        assert msg_type == "success"


class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, caplog):
        parsed_args = SimpleNamespace(data_date=arrow.get("2023-05-19"))
        caplog.set_level(logging.DEBUG)

        msg_type = make_runoff_file.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        assert caplog.messages[0] == "2023-05-19 runoff file creation failed"
        assert msg_type == "failure"


class TestMakeV202111RunoffFile:
    """Unit tests for make_runoff_file() function."""

    @staticmethod
    @pytest.fixture
    def mock_calc_watershed_flows(monkeypatch):
        def _mock_calc_watershed_flows(obs_date, config):
            flows = {
                "bute": 97.0915257,
                "evi_n": 565.25543574,
                "jervis": 217.69422748000002,
                "evi_s": 180.9227418,
                "howe": 127.6401284,
                "jdf": 621.7123890299999,
                "skagit": 1133.0656029000002,
                "puget": 577.08733426,
                "toba": 106.458897294,
                "fraser": 1168.6866122853,
                "non_fraser": 56.6227761147,
            }
            return flows

        monkeypatch.setattr(
            make_runoff_file,
            "_calc_watershed_flows",
            _mock_calc_watershed_flows,
        )

    @staticmethod
    @pytest.fixture
    def mock_get_grid_cell_areas(monkeypatch):
        def _mock_get_grid_cell_areas(config):
            grid_cell_areas = numpy.empty((898, 398), dtype=float)
            grid_cell_areas.fill(200_000)
            return grid_cell_areas

        monkeypatch.setattr(
            make_runoff_file, "_get_grid_cell_areas", _mock_get_grid_cell_areas
        )

    @staticmethod
    @pytest.fixture
    def mock_to_netcdf(monkeypatch):
        def _mock_to_netcdf(runoff_ds, encoding, nc_file_path):
            pass

        monkeypatch.setattr(make_runoff_file, "to_netcdf", _mock_to_netcdf)

    def test_checklist(
        self,
        mock_calc_watershed_flows,
        mock_get_grid_cell_areas,
        mock_to_netcdf,
        config,
        caplog,
        tmp_path,
        monkeypatch,
    ):
        rivers_dir = Path(config["rivers"]["rivers dir"])
        tmp_rivers_dir = tmp_path / rivers_dir
        tmp_rivers_dir.mkdir(parents=True)
        monkeypatch.setitem(config["rivers"], "rivers dir", tmp_rivers_dir)

        parsed_args = SimpleNamespace(data_date=arrow.get("2023-05-19"))

        checklist = make_runoff_file.make_runoff_file(parsed_args, config)

        expected = {
            "b202108": os.fspath(tmp_rivers_dir / "R202108Dailies_y2023m05d19.nc")
        }
        assert checklist == expected

    def test_log_messages(
        self,
        mock_calc_watershed_flows,
        mock_get_grid_cell_areas,
        mock_to_netcdf,
        config,
        caplog,
        tmp_path,
        monkeypatch,
    ):
        rivers_dir = Path(config["rivers"]["rivers dir"])
        tmp_rivers_dir = tmp_path / rivers_dir
        tmp_rivers_dir.mkdir(parents=True)
        monkeypatch.setitem(config["rivers"], "rivers dir", tmp_rivers_dir)

        parsed_args = SimpleNamespace(data_date=arrow.get("2023-05-26"))
        caplog.set_level(logging.DEBUG)

        make_runoff_file.make_runoff_file(parsed_args, config)

        assert caplog.records[0].levelname == "INFO"
        expected = (
            "calculating NEMO runoff forcing for 202108 bathymetry for 2023-05-26"
        )
        assert caplog.messages[0] == expected
        assert caplog.records[2].levelname == "INFO"
        expected = (
            f"stored NEMO runoff forcing for 202108 bathymetry for 2023-05-26: "
            f"{tmp_rivers_dir / 'R202108Dailies_y2023m05d26.nc'}"
        )
        assert caplog.messages[2] == expected


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

        monkeypatch.setattr(make_runoff_file, "_do_a_river_pair", _mock_do_a_river_pair)

    @staticmethod
    @pytest.fixture
    def mock_do_fraser(monkeypatch):
        def _mock_do_fraser(obs_date, config):
            return 1094.5609129386, 63.9781423614

        monkeypatch.setattr(make_runoff_file, "_do_fraser", _mock_do_fraser)

    def test_calc_watershed_flows(
        self, mock_do_a_river_pair, mock_do_fraser, config, monkeypatch
    ):
        obs_date = arrow.get("2023-02-19")

        flows = make_runoff_file._calc_watershed_flows(obs_date, config)

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
        for name in make_runoff_file.watershed_names:
            assert flows[name] == pytest.approx(expected[name])
        assert flows["non_fraser"] == pytest.approx(63.9781423614)

    def test_log_messages(
        self, mock_do_a_river_pair, mock_do_fraser, config, caplog, monkeypatch
    ):
        obs_date = arrow.get("2023-02-26")
        caplog.set_level(logging.DEBUG)

        make_runoff_file._calc_watershed_flows(obs_date, config)

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

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)

        obs_date = arrow.get("2023-02-19")

        fraser_flux, secondary_flux = make_runoff_file._do_fraser(obs_date, config)

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

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)

        mock_river_flows = [
            # Fraser
            6.528406e02,
            # Nicomekl_Langley
            2.402962e00,
        ]

        def mock_get_river_flow(river_name, river_flow, obs_date, config):
            return mock_river_flows.pop(0)

        monkeypatch.setattr(make_runoff_file, "_get_river_flow", mock_get_river_flow)

        obs_date = arrow.get("2023-02-19")

        fraser_flux, secondary_flux = make_runoff_file._do_fraser(obs_date, config)

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

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)
        mock_river_flows = [
            # Fraser
            6.625833e02,
            # Nicomekl_Langley
            2.402962e00,
        ]

        def mock_get_river_flow(river_name, river_flow, obs_date, config):
            return mock_river_flows.pop(0)

        monkeypatch.setattr(make_runoff_file, "_get_river_flow", mock_get_river_flow)

        obs_date = arrow.get("2023-02-19")

        fraser_flux, secondary_flux = make_runoff_file._do_fraser(obs_date, config)

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

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)

        watershed_name = "bute"
        obs_date = arrow.get("2023-02-13")
        primary_river_name = "Homathko_Mouth"
        secondary_river_name = None

        watershed_flux = make_runoff_file._do_a_river_pair(
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

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)

        def mock_patch_missing_obs(river_name, river_flow, obs_date, config):
            mock_flux = 5.338837e01
            return mock_flux

        monkeypatch.setattr(
            make_runoff_file, "_patch_missing_obs", mock_patch_missing_obs
        )

        watershed_name = "bute"
        obs_date = arrow.get("2023-02-18")
        primary_river_name = "Homathko_Mouth"
        secondary_river_name = None

        watershed_flux = make_runoff_file._do_a_river_pair(
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

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)

        watershed_name = "jervis"
        obs_date = arrow.get("2023-02-13")
        primary_river_name = "Clowhom_ClowhomLake"
        secondary_river_name = "RobertsCreek"

        watershed_flux = make_runoff_file._do_a_river_pair(
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

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)

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
            make_runoff_file, "_read_river_Theodosia", mock_read_river_Theodosia
        )

        watershed_name = "toba"
        obs_date = arrow.get("2023-02-18")
        primary_river_name = "Homathko_Mouth"
        secondary_river_name = "Theodosia"

        watershed_flux = make_runoff_file._do_a_river_pair(
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

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)

        def mock_patch_missing_obs(river_name, river_flow, obs_date, config):
            mock_flux = 8.285429e-01
            return mock_flux

        monkeypatch.setattr(
            make_runoff_file, "_patch_missing_obs", mock_patch_missing_obs
        )

        watershed_name = "jervis"
        obs_date = arrow.get("2023-02-13")
        primary_river_name = "Clowhom_ClowhomLake"
        secondary_river_name = "RobertsCreek"

        watershed_flux = make_runoff_file._do_a_river_pair(
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

        river_flow = make_runoff_file._get_river_flow(
            river_name, river_df, obs_date, config
        )

        assert river_flow == pytest.approx(5.195243e01)

    def test_patch(self, flow_col_label, config, caplog, monkeypatch):
        def mock_patch_missing_obs(river_name, river_flow, obs_date, config):
            flux = 4.749479e01
            return flux

        monkeypatch.setattr(
            make_runoff_file, "_patch_missing_obs", mock_patch_missing_obs
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

        river_flow = make_runoff_file._get_river_flow(
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

        monkeypatch.setattr(make_runoff_file, "_read_river_csv", mock_read_river_csv)

        river_name = "Squamish_Brackendale"

        river_flow = make_runoff_file._read_river(river_name, ps, config)

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
        line = make_runoff_file._parse_long_csv_line(
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

        make_runoff_file._set_date_as_index(river_flow)

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


class TestReadRiverTheodosia:
    """Unit tests for _read_river_Theodosia()."""

    def test_read_river_Theodosia(self, config, monkeypatch):
        mock_dataframes = [
            # TheodosiaScotty
            pandas.DataFrame(
                {
                    "year": 2023,
                    "month": 2,
                    "day": [11, 12],
                    "flow": [5.902153e0, 5.576458e0],
                }
            ),
            # TheodosiaBypass
            pandas.DataFrame(
                {
                    "year": 2023,
                    "month": 2,
                    "day": [11, 12],
                    "flow": [4.423993e0, 4.274444e0],
                }
            ),
            # TheodosiaDiversion
            pandas.DataFrame(
                {
                    "year": 2023,
                    "month": 2,
                    "day": [11, 12],
                    "flow": [4.795868e0, 4.090347e0],
                }
            ),
        ]

        def mock_read_river_csv(filename):
            return mock_dataframes.pop(0)

        monkeypatch.setattr(make_runoff_file, "_read_river_csv", mock_read_river_csv)

        theodosia = make_runoff_file._read_river_Theodosia(config)

        expected = pandas.DataFrame(
            data={
                "Secondary River Flow": [6.27403e0, 5.39236e0],
            },
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-11"),
                    pandas.to_datetime("2023-02-12"),
                ],
                name="date",
            ),
        )
        pandas.testing.assert_frame_equal(theodosia, expected)

    def test_read_river_Theodosia_wo_Scotty(self, config, monkeypatch):
        mock_dataframes = [
            # TheodosiaScotty
            pandas.DataFrame(
                {
                    "year": 2003,
                    "month": 10,
                    "day": [16, 17],
                    "flow": [7.83e0, 2.3e1],
                }
            ),
            # TheodosiaBypass
            pandas.DataFrame(
                {
                    "year": 2003,
                    "month": 10,
                    "day": [15, 16, 17],
                    "flow": [3.13e0, 5.20e0, 4.07e0],
                }
            ),
            # TheodosiaDiversion
            pandas.DataFrame(
                {
                    "year": 2003,
                    "month": 10,
                    "day": [15, 16, 17],
                    "flow": [4.38e0, 3.17e1, 5.89e1],
                }
            ),
        ]

        def mock_read_river_csv(filename):
            return mock_dataframes.pop(0)

        monkeypatch.setattr(make_runoff_file, "_read_river_csv", mock_read_river_csv)

        theodosia = make_runoff_file._read_river_Theodosia(config)

        expected = pandas.DataFrame(
            data={
                "Secondary River Flow": [6.25902e0, 3.433000e1, 7.783000e1],
            },
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2003-10-15"),
                    pandas.to_datetime("2003-10-16"),
                    pandas.to_datetime("2003-10-17"),
                ],
                name="date",
            ),
        )
        pandas.testing.assert_frame_equal(theodosia, expected)


class TestPatchMissingObs:
    """Unit tests for make_runoff_file._patch_missing_obs()."""

    def test_obs_date_not_at_end_of_timeseries(self, config, caplog):
        river_name = "Nicomekl_Langley"
        river_flow = pandas.DataFrame(
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-10"),
                    pandas.to_datetime("2023-02-11"),
                    pandas.to_datetime("2023-02-12"),
                    pandas.to_datetime("2023-02-13"),
                    pandas.to_datetime("2023-02-14"),
                    pandas.to_datetime("2023-02-15"),
                    pandas.to_datetime("2023-02-16"),
                ],
                name="date",
            ),
            data={
                "Primary River Flow": [
                    1.910105e00,
                    1.379547e00,
                    2.236864e00,
                    3.346551e00,
                    1.748188e00,
                    1.233519e00,
                    1.151951e00,
                ],
            },
        )
        obs_date = arrow.get("2023-02-13")

        with pytest.raises(
            ValueError, match=r".* is not beyond end of time series at .*"
        ):
            make_runoff_file._patch_missing_obs(
                river_name, river_flow, obs_date, config
            )

    def test_persist(self, config, caplog):
        river_name = "Clowhom_ClowhomLake"
        river_flow = pandas.DataFrame(
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-13"),
                    pandas.to_datetime("2023-02-14"),
                    pandas.to_datetime("2023-02-15"),
                ],
                name="date",
            ),
            data={
                "Primary River Flow": [
                    5.549688e00,
                    4.717500e00,
                    4.036944e00,
                ],
            },
        )
        obs_date = arrow.get("2023-02-16")
        caplog.set_level(logging.DEBUG)

        flux = make_runoff_file._patch_missing_obs(
            river_name, river_flow, obs_date, config
        )

        assert caplog.records[0].levelname == "DEBUG"
        expected = (
            "patched missing 2023-02-16 Clowhom_ClowhomLake discharge by persistence"
        )
        assert caplog.messages[0] == expected

        assert flux == pytest.approx(4.036944e00)

    def test_fit(self, config, caplog, monkeypatch):
        def mock_patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        ):
            flux = 54.759385
            return flux

        monkeypatch.setattr(make_runoff_file, "_patch_fitting", mock_patch_fitting)

        river_name = "Squamish_Brackendale"
        river_flow = pandas.DataFrame(
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-06"),
                    pandas.to_datetime("2023-02-07"),
                    pandas.to_datetime("2023-02-08"),
                    pandas.to_datetime("2023-02-09"),
                    pandas.to_datetime("2023-02-10"),
                    pandas.to_datetime("2023-02-11"),
                    pandas.to_datetime("2023-02-12"),
                    pandas.to_datetime("2023-02-13"),
                ],
                name="date",
            ),
            data={
                "Primary River Flow": [
                    4.181135e01,
                    9.415799e01,
                    8.465509e01,
                    6.185860e01,
                    6.616285e01,
                    6.533544e01,
                    5.635754e01,
                    8.004896e01,
                ],
            },
        )
        obs_date = arrow.get("2023-02-14")
        caplog.set_level(logging.DEBUG)

        flux = make_runoff_file._patch_missing_obs(
            river_name, river_flow, obs_date, config
        )

        assert caplog.records[0].levelname == "DEBUG"
        expected = "patched missing 2023-02-14 Squamish_Brackendale discharge by fitting from Homathko_Mouth"
        assert caplog.messages[0] == expected

        assert flux == pytest.approx(54.759385)

    def test_backup(self, config, caplog, monkeypatch):
        mock_patch_fitting_returns = [
            # flux
            numpy.nan,  # fit from Englishman River fails
            68.43567,  # fit from Roberts Creek
        ]

        def mock_patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        ):
            return mock_patch_fitting_returns.pop(0)

        monkeypatch.setattr(make_runoff_file, "_patch_fitting", mock_patch_fitting)

        river_name = "SanJuan_PortRenfrew"
        river_flow = pandas.DataFrame(
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-13"),
                    pandas.to_datetime("2023-02-14"),
                    pandas.to_datetime("2023-02-15"),
                ],
                name="date",
            ),
            data={
                "Primary River Flow": [
                    6.963472e01,
                    5.954271e01,
                    5.195243e01,
                ],
            },
        )
        obs_date = arrow.get("2023-02-16")
        caplog.set_level(logging.DEBUG)

        flux = make_runoff_file._patch_missing_obs(
            river_name, river_flow, obs_date, config
        )

        assert caplog.records[0].levelname == "DEBUG"
        expected = "patched missing 2023-02-16 SanJuan_PortRenfrew discharge by fitting from backup river: RobertsCreek"
        assert caplog.messages[0] == expected

        assert flux == pytest.approx(68.43567)

    def test_persist_is_last_resort(self, config, caplog, monkeypatch):
        mock_patch_fitting_returns = [
            # bad, flux
            numpy.nan,  # fit from Englishman River fails
            numpy.nan,  # fit from Roberts Creek fails
        ]

        def mock_patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        ):
            return mock_patch_fitting_returns.pop(0)

        monkeypatch.setattr(make_runoff_file, "_patch_fitting", mock_patch_fitting)

        river_name = "SanJuan_PortRenfrew"
        river_flow = pandas.DataFrame(
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-13"),
                    pandas.to_datetime("2023-02-14"),
                    pandas.to_datetime("2023-02-15"),
                ],
                name="date",
            ),
            data={
                "Primary River Flow": [
                    6.963472e01,
                    5.954271e01,
                    5.195243e01,
                ],
            },
        )
        obs_date = arrow.get("2023-02-16")
        caplog.set_level(logging.DEBUG)

        flux = make_runoff_file._patch_missing_obs(
            river_name, river_flow, obs_date, config
        )

        assert caplog.records[0].levelname == "DEBUG"
        expected = (
            "patched missing 2023-02-16 SanJuan_PortRenfrew discharge by persistence"
        )
        assert caplog.messages[0] == expected

        assert flux == pytest.approx(5.195243e01)


class TestPatchFitting:
    """Unit tests for make_runoff_file._patch_fitting()."""

    def test_1_day_missing_patch_successful(self, config, monkeypatch):
        def mock_read_river(river_name, ps, config):
            return pandas.DataFrame(
                # Homathko_Mouth
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-06"),
                        pandas.to_datetime("2023-02-07"),
                        pandas.to_datetime("2023-02-08"),
                        pandas.to_datetime("2023-02-09"),
                        pandas.to_datetime("2023-02-10"),
                        pandas.to_datetime("2023-02-11"),
                        pandas.to_datetime("2023-02-12"),
                        pandas.to_datetime("2023-02-13"),
                        pandas.to_datetime("2023-02-14"),
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [
                        3.690729e01,
                        6.113299e01,
                        5.083090e01,
                        4.158090e01,
                        4.387431e01,
                        4.237986e01,
                        4.243368e01,
                        4.444965e01,
                        3.756528e01,
                    ],
                },
            )

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)

        river_flow = pandas.DataFrame(
            # Squamish_Brackendale
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-06"),
                    pandas.to_datetime("2023-02-07"),
                    pandas.to_datetime("2023-02-08"),
                    pandas.to_datetime("2023-02-09"),
                    pandas.to_datetime("2023-02-10"),
                    pandas.to_datetime("2023-02-11"),
                    pandas.to_datetime("2023-02-12"),
                    pandas.to_datetime("2023-02-13"),
                ],
                name="date",
            ),
            data={
                "Primary River Flow": [
                    4.181135e01,
                    9.415799e01,
                    8.465509e01,
                    6.185860e01,
                    6.616285e01,
                    6.533544e01,
                    5.635754e01,
                    8.004896e01,
                ],
            },
        )
        fit_from_river_name = "Homathko_Mouth"
        obs_date = arrow.get("2023-02-14")
        gap_length = 1

        flux = make_runoff_file._patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        )

        assert flux == pytest.approx(54.759385)

    def test_3_days_missing_patch_successful(self, config, monkeypatch):
        def mock_read_river(river_name, ps, config):
            return pandas.DataFrame(
                # Homathko_Mouth
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-04"),
                        pandas.to_datetime("2023-02-05"),
                        pandas.to_datetime("2023-02-06"),
                        pandas.to_datetime("2023-02-07"),
                        pandas.to_datetime("2023-02-08"),
                        pandas.to_datetime("2023-02-09"),
                        pandas.to_datetime("2023-02-10"),
                        pandas.to_datetime("2023-02-11"),
                        pandas.to_datetime("2023-02-12"),
                        pandas.to_datetime("2023-02-13"),
                        pandas.to_datetime("2023-02-14"),
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [
                        3.107431e01,
                        3.446285e01,
                        3.690729e01,
                        6.113299e01,
                        5.083090e01,
                        4.158090e01,
                        4.387431e01,
                        4.237986e01,
                        4.243368e01,
                        4.444965e01,
                        3.756528e01,
                    ],
                },
            )

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)

        river_flow = pandas.DataFrame(
            # Squamish_Brackendale
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-04"),
                    pandas.to_datetime("2023-02-05"),
                    pandas.to_datetime("2023-02-06"),
                    pandas.to_datetime("2023-02-07"),
                    pandas.to_datetime("2023-02-08"),
                    pandas.to_datetime("2023-02-09"),
                    pandas.to_datetime("2023-02-10"),
                    pandas.to_datetime("2023-02-11"),
                ],
                name="date",
            ),
            data={
                "Primary River Flow": [
                    4.714132e01,
                    4.199236e01,
                    4.181135e01,
                    9.415799e01,
                    8.465509e01,
                    6.185860e01,
                    6.616285e01,
                    6.533544e01,
                ],
            },
        )
        fit_from_river_name = "Homathko_Mouth"
        obs_date = arrow.get("2023-02-14")
        gap_length = 3

        flux = make_runoff_file._patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        )

        assert flux == pytest.approx(54.038875)

    def test_gap_in_river_to_patch_failure(self, config, monkeypatch):
        def mock_read_river(river_name, ps, config):
            return pandas.DataFrame(
                # Homathko_Mouth
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-06"),
                        pandas.to_datetime("2023-02-07"),
                        pandas.to_datetime("2023-02-08"),
                        pandas.to_datetime("2023-02-09"),
                        pandas.to_datetime("2023-02-10"),
                        pandas.to_datetime("2023-02-11"),
                        pandas.to_datetime("2023-02-12"),
                        pandas.to_datetime("2023-02-13"),
                        pandas.to_datetime("2023-02-14"),
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [
                        3.690729e01,
                        6.113299e01,
                        5.083090e01,
                        4.158090e01,
                        4.387431e01,
                        4.237986e01,
                        4.243368e01,
                        4.444965e01,
                        3.756528e01,
                    ],
                },
            )

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)

        river_flow = pandas.DataFrame(
            # Squamish_Brackendale
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-06"),
                    pandas.to_datetime("2023-02-07"),
                    pandas.to_datetime("2023-02-08"),
                    # missing day
                    pandas.to_datetime("2023-02-10"),
                    pandas.to_datetime("2023-02-11"),
                    pandas.to_datetime("2023-02-12"),
                    pandas.to_datetime("2023-02-13"),
                ],
                name="date",
            ),
            data={
                "Primary River Flow": [
                    4.181135e01,
                    9.415799e01,
                    8.465509e01,
                    # missing day
                    6.616285e01,
                    6.533544e01,
                    5.635754e01,
                    8.004896e01,
                ],
            },
        )
        fit_from_river_name = "Homathko_Mouth"
        obs_date = arrow.get("2023-02-14")
        gap_length = 1

        flux = make_runoff_file._patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        )

        assert numpy.isnan(flux)

    def test_gap_in_river_to_fit_from_failure(self, config, monkeypatch):
        def mock_read_river(river_name, ps, config):
            return pandas.DataFrame(
                # Homathko_Mouth
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-06"),
                        pandas.to_datetime("2023-02-07"),
                        pandas.to_datetime("2023-02-08"),
                        # missing day
                        pandas.to_datetime("2023-02-10"),
                        pandas.to_datetime("2023-02-11"),
                        pandas.to_datetime("2023-02-12"),
                        pandas.to_datetime("2023-02-13"),
                        pandas.to_datetime("2023-02-14"),
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [
                        3.690729e01,
                        6.113299e01,
                        5.083090e01,
                        # missing day
                        4.387431e01,
                        4.237986e01,
                        4.243368e01,
                        4.444965e01,
                        3.756528e01,
                    ],
                },
            )

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)

        river_flow = pandas.DataFrame(
            # Squamish_Brackendale
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-06"),
                    pandas.to_datetime("2023-02-07"),
                    pandas.to_datetime("2023-02-08"),
                    pandas.to_datetime("2023-02-09"),
                    pandas.to_datetime("2023-02-10"),
                    pandas.to_datetime("2023-02-11"),
                    pandas.to_datetime("2023-02-12"),
                    pandas.to_datetime("2023-02-13"),
                ],
                name="date",
            ),
            data={
                "Primary River Flow": [
                    4.181135e01,
                    9.415799e01,
                    8.465509e01,
                    6.185860e01,
                    6.616285e01,
                    6.533544e01,
                    5.635754e01,
                    8.004896e01,
                ],
            },
        )
        fit_from_river_name = "Homathko_Mouth"
        obs_date = arrow.get("2023-02-14")
        gap_length = 1

        flux = make_runoff_file._patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        )

        assert numpy.isnan(flux)

    def test_river_to_patch_from_missing_obs_date_failure(self, config, monkeypatch):
        def mock_read_river(river_name, ps, config):
            return pandas.DataFrame(
                # Homathko_Mouth
                index=pandas.Index(
                    data=[
                        pandas.to_datetime("2023-02-06"),
                        pandas.to_datetime("2023-02-07"),
                        pandas.to_datetime("2023-02-08"),
                        pandas.to_datetime("2023-02-09"),
                        pandas.to_datetime("2023-02-10"),
                        pandas.to_datetime("2023-02-11"),
                        pandas.to_datetime("2023-02-12"),
                        pandas.to_datetime("2023-02-13"),
                        # missing obs date
                    ],
                    name="date",
                ),
                data={
                    "Primary River Flow": [
                        3.690729e01,
                        6.113299e01,
                        5.083090e01,
                        4.158090e01,
                        4.387431e01,
                        4.237986e01,
                        4.243368e01,
                        4.444965e01,
                        # missing obs date value
                    ],
                },
            )

        monkeypatch.setattr(make_runoff_file, "_read_river", mock_read_river)

        river_flow = pandas.DataFrame(
            # Squamish_Brackendale
            index=pandas.Index(
                data=[
                    pandas.to_datetime("2023-02-06"),
                    pandas.to_datetime("2023-02-07"),
                    pandas.to_datetime("2023-02-08"),
                    pandas.to_datetime("2023-02-09"),
                    pandas.to_datetime("2023-02-10"),
                    pandas.to_datetime("2023-02-11"),
                    pandas.to_datetime("2023-02-12"),
                    pandas.to_datetime("2023-02-13"),
                ],
                name="date",
            ),
            data={
                "Primary River Flow": [
                    4.181135e01,
                    9.415799e01,
                    8.465509e01,
                    6.185860e01,
                    6.616285e01,
                    6.533544e01,
                    5.635754e01,
                    8.004896e01,
                ],
            },
        )
        fit_from_river_name = "Homathko_Mouth"
        obs_date = arrow.get("2023-02-14")
        gap_length = 1

        flux = make_runoff_file._patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        )

        assert numpy.isnan(flux)


class TestCreateRunoffArray:
    """Unit test for make_runoff_file._create_runoff_array()."""

    def test_create_runoff_array(self, config):
        flows = {
            "bute": 97.0915257,
            "evi_n": 565.25543574,
            "jervis": 217.69422748000002,
            "evi_s": 180.9227418,
            "howe": 127.6401284,
            "jdf": 621.7123890299999,
            "skagit": 1133.0656029000002,
            "puget": 577.08733426,
            "toba": 106.458897294,
            "fraser": 1168.6866122853,
            "non_fraser": 56.6227761147,
        }
        mock_grid_cell_areas = numpy.empty((898, 398), dtype=float)
        mock_grid_cell_areas.fill(200_000)

        runoff_array = make_runoff_file._create_runoff_array(
            flows, mock_grid_cell_areas
        )

        # Check selected river runoffs
        # Nicomekl
        assert runoff_array[388, 350] == pytest.approx(0.0137139)
        # Fraser (channel head in model)
        assert runoff_array[500, 394] == pytest.approx(5.8434331)
        # Qunisam
        numpy.testing.assert_allclose(
            runoff_array[750:752, 123], [0.213957536, 0.213957536]
        )
        # Check total runoff
        assert runoff_array.sum() == pytest.approx(22.54050399)


class TestCalcRunoffDataset:
    """Unit tests for make_runoff_file._calc_runoff_dataset()."""

    @staticmethod
    @pytest.fixture(scope="class")
    def runoff_array():
        _runoff_array = numpy.zeros((898, 398))
        _runoff_array[750:752, 123] = [0.20318864, 0.20318864]
        return _runoff_array

    def test_data_array_values(self, runoff_array, config):
        obs_date = arrow.get("2023-05-11")

        runoff_ds = make_runoff_file._calc_runoff_dataset(
            obs_date, runoff_array, config
        )

        numpy.testing.assert_allclose(
            runoff_ds["rorunoff"][0, 750:752, 123], [0.20318864, 0.20318864]
        )

    def test_data_array_attrs(self, runoff_array, config):
        obs_date = arrow.get("2023-05-11")

        runoff_ds = make_runoff_file._calc_runoff_dataset(
            obs_date, runoff_array, config
        )

        assert runoff_ds["rorunoff"].attrs["standard_name"] == "runoff_flux"
        assert runoff_ds["rorunoff"].attrs["long_name"] == "River Runoff Flux"
        assert runoff_ds["rorunoff"].attrs["units"] == "kg m-2 s-1"

    def test_coords(self, runoff_array, config):
        obs_date = arrow.get("2023-05-11")

        runoff_ds = make_runoff_file._calc_runoff_dataset(
            obs_date, runoff_array, config
        )

        assert len(runoff_ds.coords) == 3
        assert runoff_ds.coords["time_counter"] == pandas.to_datetime(["2023-05-11"])
        assert all(runoff_ds.coords["y"] == numpy.arange(runoff_array.shape[0]))
        assert all(runoff_ds.coords["x"] == numpy.arange(runoff_array.shape[1]))

    def test_dims(self, runoff_array, config):
        obs_date = arrow.get("2023-05-11")

        runoff_ds = make_runoff_file._calc_runoff_dataset(
            obs_date, runoff_array, config
        )

        assert len(runoff_ds.sizes) == 3
        assert runoff_ds.sizes["time_counter"] == 1
        assert runoff_ds.sizes["y"] == runoff_array.shape[0]
        assert runoff_ds.sizes["x"] == runoff_array.shape[1]

    def test_dataset_attrs(self, runoff_array, config, monkeypatch):
        def mock_now(tz):
            return arrow.get("2023-05-11 14:51:43-07:00")

        monkeypatch.setattr(make_runoff_file.arrow, "now", mock_now)

        obs_date = arrow.get("2023-05-11")

        runoff_ds = make_runoff_file._calc_runoff_dataset(
            obs_date, runoff_array, config
        )

        assert runoff_ds.attrs["creator_email"] == "sallen@eoas.ubc.ca"
        assert runoff_ds.attrs["creator_name"] == "SalishSeaCast Project contributors"
        assert (
            runoff_ds.attrs["creator_url"]
            == "https://github.com/SalishSeaCast/SalishSeaNowcast/blob/main/nowcast/workers/make_runoff_file.py"
        )
        assert runoff_ds.attrs["institution"] == "UBC EOAS"
        assert (
            runoff_ds.attrs["institution_fullname"]
            == "Earth, Ocean & Atmospheric Sciences, University of British Columbia"
        )
        assert (
            runoff_ds.attrs["title"]
            == f"River Runoff Fluxes for {obs_date.format('YYYY-MM-DD')}"
        )
        assert runoff_ds.attrs["summary"] == (
            f"Day-average river runoff fluxes calculated for {obs_date.format('YYYY-MM-DD')} "
            f"on v202108 bathymetry. "
            f"The runoff fluxes are calculated from day-averaged discharge (1 day lagged) observations "
            f"from gauged rivers across the SalishSeaCast model domain using fits developed by Susan Allen."
        )
        assert (
            runoff_ds.attrs["development_notebook"]
            == "https://github.com/SalishSeaCast/tools/blob/main/I_ForcingFiles/Rivers/ProductionDailyRiverNCfile.ipynb"
        )
        assert (
            runoff_ds.attrs["rivers_watersheds_proportions"]
            == "salishsea_tools.river_202108"
        )
        assert runoff_ds.attrs["history"] == (
            f"[Thu {obs_date.format('YYYY-MM-DD')} 14:51:43 -07:00] "
            f"python -m nowcast.workers.make_runoff_file $NOWCAST_YAML "
            f"--run-date {obs_date.format('YYYY-MM-DD')}"
        )


class TestWriteNetcdf:
    """Unit test for make_runoff_file._write_netcdf()."""

    def test_write_netcdf(self, config, caplog, tmp_path, monkeypatch):
        def mock_to_netcdf(runoff_ds, encoding, nc_file_path):
            pass

        monkeypatch.setattr(make_runoff_file, "to_netcdf", mock_to_netcdf)
        rivers_dir = Path(config["rivers"]["rivers dir"])
        tmp_rivers_dir = tmp_path / rivers_dir
        tmp_rivers_dir.mkdir(parents=True)
        monkeypatch.setitem(config["rivers"], "rivers dir", tmp_rivers_dir)

        runoff_ds = xarray.Dataset()
        obs_date = arrow.get("2023-05-30")
        caplog.set_level("DEBUG")

        nc_file_path = make_runoff_file._write_netcdf(runoff_ds, obs_date, config)

        assert caplog.records[0].levelname == "DEBUG"
        assert (
            caplog.messages[0]
            == f"wrote {tmp_rivers_dir / 'R202108Dailies_y2023m05d30.nc'}"
        )

        assert nc_file_path == tmp_rivers_dir / "R202108Dailies_y2023m05d30.nc"
