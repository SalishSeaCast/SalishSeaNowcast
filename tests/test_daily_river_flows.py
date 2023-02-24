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


"""Unit tests for daily_river_flows module.
"""
import io
import os
import textwrap
from pathlib import Path

import arrow
import nemo_nowcast
import numpy.testing
import pandas.testing
import pytest

from nowcast import daily_river_flows


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


class TestParseLongCSVLine:
    """Unit test for daily_river_flows._parse_long_csv_line()."""

    def test_parse_long_csv_line(self):
        line = daily_river_flows._parse_long_csv_line(
            "1923 02 13 1.100000E+01 B".split()
        )

        assert line == "1923 02 13 1.100000E+01".split()


class TestReadRiverCSV:
    """Unit tests for daily_river_flows._read_river_csv()"""

    def test_well_formed_lines(self):
        csv_lines = textwrap.dedent(
            """\
            1923 01 26 2.750000E+01
            1923 01 27 2.970000E+01
            """
        )

        river_flow = daily_river_flows._read_river_csv(io.StringIO(csv_lines))

        expected = pandas.DataFrame(
            {
                "year": 1923,
                "month": 1,
                "day": [26, 27],
                "flow": [2.75e1, 2.97e1],
            }
        )
        pandas.testing.assert_frame_equal(river_flow, expected)

    def test_one_long_line(self):
        csv_lines = textwrap.dedent(
            """\
            1923 02 20 1.130000E+01 B
            1923 02 21 5.970000E+01
            """
        )

        river_flow = daily_river_flows._read_river_csv(io.StringIO(csv_lines))

        expected = pandas.DataFrame(
            {
                "year": 1923,
                "month": 2,
                "day": [20, 21],
                "flow": [1.13e1, 5.97e1],
            }
        )
        pandas.testing.assert_frame_equal(river_flow, expected)


class TestSetDateAsIndex:
    """Unit test for daily_river_flows._set_date_as_index()."""

    def test_set_date_as_index(self):
        river_flow = pandas.DataFrame(
            {
                "year": 1923,
                "month": 2,
                "day": [20, 21],
                "flow": [1.13e1, 5.97e1],
            }
        )

        daily_river_flows._set_date_as_index(river_flow)

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


class TestReadRiver:
    """Unit tests for daily_river_flows._read_river()."""

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

        monkeypatch.setattr(daily_river_flows, "_read_river_csv", mock_read_river_csv)

        river_name = "Squamish_Brackendale"

        river_flow = daily_river_flows._read_river(river_name, ps, config)

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


class TestReadRiverTheodosia:
    """Unit tests for daily_river_flows._read_river_Theodosia()."""

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

        monkeypatch.setattr(daily_river_flows, "_read_river_csv", mock_read_river_csv)

        theodosia = daily_river_flows._read_river_Theodosia(config)

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

        monkeypatch.setattr(daily_river_flows, "_read_river_csv", mock_read_river_csv)

        theodosia = daily_river_flows._read_river_Theodosia(config)

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


class TestPatchFitting:
    """Unit tests for daily_river_flows._patch_fitting()."""

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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)

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

        flux = daily_river_flows._patch_fitting(
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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)

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

        flux = daily_river_flows._patch_fitting(
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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)

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

        flux = daily_river_flows._patch_fitting(
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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)

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

        flux = daily_river_flows._patch_fitting(
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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)

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

        flux = daily_river_flows._patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        )

        assert numpy.isnan(flux)


class TestPatchMissingObs:
    """Unit tests for daily_river_flows._patch_missing_obs()."""

    def test_obs_date_not_at_end_of_timeseries(self, config):
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
        ) as excinfo:
            daily_river_flows._patch_missing_obs(
                river_name, river_flow, obs_date, config
            )

    def test_persist(self, config):
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

        flux = daily_river_flows._patch_missing_obs(
            river_name, river_flow, obs_date, config
        )

        assert flux == pytest.approx(4.036944e00)

    def test_fit(self, config, monkeypatch):
        def mock_patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        ):
            flux = 54.759385
            return flux

        monkeypatch.setattr(daily_river_flows, "_patch_fitting", mock_patch_fitting)

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

        flux = daily_river_flows._patch_missing_obs(
            river_name, river_flow, obs_date, config
        )

        assert flux == pytest.approx(54.759385)

    def test_backup(self, config, monkeypatch):
        mock_patch_fitting_returns = [
            # bad, flux
            numpy.nan,  # fit from Englishman River fails
            68.43567,  # fit from Roberts Creek
        ]

        def mock_patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        ):
            return mock_patch_fitting_returns.pop(0)

        monkeypatch.setattr(daily_river_flows, "_patch_fitting", mock_patch_fitting)

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

        flux = daily_river_flows._patch_missing_obs(
            river_name, river_flow, obs_date, config
        )

        assert flux == pytest.approx(68.43567)

    def test_perist_is_last_resort(self, config, monkeypatch):
        mock_patch_fitting_returns = [
            # bad, flux
            numpy.nan,  # fit from Englishman River fails
            numpy.nan,  # fit from Roberts Creek fails
        ]

        def mock_patch_fitting(
            river_flow, fit_from_river_name, obs_date, gap_length, config
        ):
            return mock_patch_fitting_returns.pop(0)

        monkeypatch.setattr(daily_river_flows, "_patch_fitting", mock_patch_fitting)

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

        flux = daily_river_flows._patch_missing_obs(
            river_name, river_flow, obs_date, config
        )

        assert flux == pytest.approx(5.195243e01)


@pytest.mark.parametrize(
    "flow_col_label", ("Primary River Flow", "Secondary River Flow")
)
class TestGetRiverFlow:
    """Unit tests for daily_river_flows._get_river_flow()."""

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

        river_flow = daily_river_flows._get_river_flow(
            river_name, river_df, obs_date, config
        )

        assert river_flow == pytest.approx(5.195243e01)

    def test_patch(self, flow_col_label, config, monkeypatch):
        def mock_patch_missing_obs(river_name, river_flow, obs_date, config):
            flux = 4.749479e01
            return flux

        monkeypatch.setattr(
            daily_river_flows, "_patch_missing_obs", mock_patch_missing_obs
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

        river_flow = daily_river_flows._get_river_flow(
            river_name, river_df, obs_date, config
        )

        assert river_flow == pytest.approx(4.749479e01)


class TestDoAPair:
    """Unit tests for daily_river_flows._do_a_pair()."""

    def test_primary_river_only_no_patch_reqd(self, config, monkeypatch):
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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)

        watershed_name = "bute"
        obs_date = arrow.get("2023-02-13")
        primary_river_name = "Homathko_Mouth"
        secondary_river_name = None

        watershed_flux = daily_river_flows._do_a_pair(
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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)

        def mock_patch_missing_obs(river_name, river_flow, obs_date, config):
            mock_flux = 5.338837e01
            return mock_flux

        monkeypatch.setattr(
            daily_river_flows, "_patch_missing_obs", mock_patch_missing_obs
        )

        watershed_name = "bute"
        obs_date = arrow.get("2023-02-18")
        primary_river_name = "Homathko_Mouth"
        secondary_river_name = None

        watershed_flux = daily_river_flows._do_a_pair(
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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)

        watershed_name = "jervis"
        obs_date = arrow.get("2023-02-13")
        primary_river_name = "Clowhom_ClowhomLake"
        secondary_river_name = "RobertsCreek"

        watershed_flux = daily_river_flows._do_a_pair(
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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)

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
            daily_river_flows, "_read_river_Theodosia", mock_read_river_Theodosia
        )

        watershed_name = "toba"
        obs_date = arrow.get("2023-02-18")
        primary_river_name = "Homathko_Mouth"
        secondary_river_name = "Theodosia"

        watershed_flux = daily_river_flows._do_a_pair(
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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)

        def mock_patch_missing_obs(river_name, river_flow, obs_date, config):
            mock_flux = 8.285429e-01
            return mock_flux

        monkeypatch.setattr(
            daily_river_flows, "_patch_missing_obs", mock_patch_missing_obs
        )

        watershed_name = "jervis"
        obs_date = arrow.get("2023-02-13")
        primary_river_name = "Clowhom_ClowhomLake"
        secondary_river_name = "RobertsCreek"

        watershed_flux = daily_river_flows._do_a_pair(
            watershed_name, obs_date, primary_river_name, config, secondary_river_name
        )

        assert watershed_flux == pytest.approx(123.54403)


class TestDoFraser:
    """Unit tests for daily_river_flows._do_Fraser()."""

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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)

        obs_date = arrow.get("2023-02-19")

        Fraser_flux, secondary_flux = daily_river_flows._do_fraser(obs_date, config)

        assert Fraser_flux == pytest.approx(1094.56091294)
        assert secondary_flux == pytest.approx(63.978142)

    def test_persist_Fraser(self, config, monkeypatch):
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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)

        mock_river_flows = [
            # Fraser
            6.528406e02,
            # Nicomekl_Langley
            2.402962e00,
        ]

        def mock_get_river_flow(river_name, river_flow, obs_date, config):
            return mock_river_flows.pop(0)

        monkeypatch.setattr(daily_river_flows, "_get_river_flow", mock_get_river_flow)

        obs_date = arrow.get("2023-02-19")

        Fraser_flux, secondary_flux = daily_river_flows._do_fraser(obs_date, config)

        assert Fraser_flux == pytest.approx(1083.249638)
        assert secondary_flux == pytest.approx(63.978142)

    def test_patch_Nicomekl(self, config, monkeypatch):
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

        monkeypatch.setattr(daily_river_flows, "_read_river", mock_read_river)
        mock_river_flows = [
            # Fraser
            6.625833e02,
            # Nicomekl_Langley
            2.402962e00,
        ]

        def mock_get_river_flow(river_name, river_flow, obs_date, config):
            return mock_river_flows.pop(0)

        monkeypatch.setattr(daily_river_flows, "_get_river_flow", mock_get_river_flow)

        obs_date = arrow.get("2023-02-19")

        Fraser_flux, secondary_flux = daily_river_flows._do_fraser(obs_date, config)

        assert Fraser_flux == pytest.approx(1094.56091294)
        assert secondary_flux == pytest.approx(63.978142)


class TestCalcWatershedFlows:
    """Unit test for daily_river_flows._calc_watershed_flows()."""

    def test_calc_watershed_flows(self, config, monkeypatch):
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

        def mock_do_a_pair(
            watershed_name,
            obs_date,
            primary_river_name,
            config,
            secondary_river_name=None,
        ):
            return mock_watershed_flows.pop(0)[1]

        monkeypatch.setattr(daily_river_flows, "_do_a_pair", mock_do_a_pair)

        def mock_do_fraser(obs_date, config):
            return 1094.5609129386, 63.9781423614

        monkeypatch.setattr(daily_river_flows, "_do_fraser", mock_do_fraser)

        obs_date = arrow.get("2023-02-19")

        flows = daily_river_flows._calc_watershed_flows(obs_date, config)

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
        for name in daily_river_flows.watershed_names:
            assert flows[name] == pytest.approx(expected[name])
        assert flows["non_fraser"] == pytest.approx(63.9781423614)


@pytest.mark.skipif(
    "GITHUB_ACTIONS" in os.environ,
    reason="_get_area() uses file from grid repo that is too annoying to make available on Actions",
)
class TestCreateRunoffArray:
    """Unit test for daily_river_flows._create_runoff_array()."""

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
        horz_area = daily_river_flows._get_area(config)

        runoff_array = daily_river_flows._create_runoff_array(flows, horz_area)

        # Check selected river runoffs
        # Nicomekl
        assert runoff_array[388, 350] == pytest.approx(0.012653)
        # Fraser (channel head in model)
        assert runoff_array[500, 394] == pytest.approx(5.517576)
        # Qunisam
        numpy.testing.assert_allclose(
            runoff_array[750:752, 123], [0.20318864, 0.20318864]
        )
        # Check total runoff
        assert runoff_array.sum() == pytest.approx(20.7198114)
