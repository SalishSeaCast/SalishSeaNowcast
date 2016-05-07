# Copyright 2013-2016 The Salish Sea MEOPAR contributors
# and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for Salish Sea NEMO nowcast lib module.
"""
import argparse
from datetime import datetime

import arrow
import pytest

from nowcast import lib


class TestArrowDate:
    """Unit tests for arrow_date() function.
    """
    def test_arrow_date_default_timezone(self):
        arw = lib.arrow_date('2015-07-26')
        expected = arrow.get(datetime(2015, 7, 26, 0, 0, 0), 'Canada/Pacific')
        assert arw == expected

    def test_arrow_date_timezone(self):
        arw = lib.arrow_date('2015-07-26', 'Canada/Atlantic')
        expected = arrow.get(datetime(2015, 7, 26, 0, 0, 0), 'Canada/Atlantic')
        assert arw == expected

    def test_arrow_date_parse_erroe(self):
        with pytest.raises(argparse.ArgumentTypeError):
            lib.arrow_date('205-7-261')
