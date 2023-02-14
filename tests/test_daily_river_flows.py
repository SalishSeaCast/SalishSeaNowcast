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
import textwrap
from pathlib import Path

import nemo_nowcast
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
