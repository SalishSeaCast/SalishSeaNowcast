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

import pandas.testing
import pytest

from nowcast import daily_river_flows


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
    def test_read_river(self, ps, expected_col_name, monkeypatch):
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
        config = {
            "rivers": {
                "SOG river files": {
                    "SquamishBrackendale": "forcing/rivers/observations/Squamish_Brackendale_flow",
                }
            }
        }

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
