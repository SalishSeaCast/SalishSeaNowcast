# Copyright 2013-2015 The Salish Sea MEOPAR contributors
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

"""Unit tests for Salish Sea NEMO nowcast get_NeahBay_ssh worker.
"""
import datetime

import pytest
import pytz


@pytest.fixture
def get_NeahBay_ssh_module():
    from nowcast.workers import get_NeahBay_ssh
    return get_NeahBay_ssh


class TestUTCNowToRunDate(object):
    """Unit tests for utc_now_to_run_date() function.
    """
    def test_nowcast(self, get_NeahBay_ssh_module):
        utc_now = datetime.datetime(
            2014, 12, 25, 17, 52, 42, tzinfo=pytz.timezone('UTC'))
        run_day = get_NeahBay_ssh_module.utc_now_to_run_date(
            utc_now, 'nowcast')
        assert run_day == datetime.date(2014, 12, 25)

    def test_forecast(self, get_NeahBay_ssh_module):
        utc_now = datetime.datetime(
            2014, 12, 25, 19, 54, 42, tzinfo=pytz.timezone('UTC'))
        run_day = get_NeahBay_ssh_module.utc_now_to_run_date(
            utc_now, 'forecast')
        assert run_day == datetime.date(2014, 12, 25)

    def test_forecast2(self, get_NeahBay_ssh_module):
        utc_now = datetime.datetime(
            2014, 12, 26, 12, 53, 42, tzinfo=pytz.timezone('UTC'))
        run_day = get_NeahBay_ssh_module.utc_now_to_run_date(
            utc_now, 'forecast2')
        assert run_day == datetime.date(2014, 12, 25)
