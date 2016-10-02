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

"""Unit tests for nowcast.next_workers module.
"""
import pytest

from nemo_nowcast import (
    Message,
    NextWorker,
)

from nowcast import next_workers


class TestAfterDownloadWeather:
    """Unit tests for the after_download_weather function.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure 00',
        'failure 06',
        'failure 12',
        'failure 18',
    ])
    def test_no_next_worker_msg_types(self, msg_type):
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type))
        assert workers == []

    @pytest.mark.parametrize('msg_type', [
        'success 00',
        'success 06',
        'success 12',
        'success 18',
    ])
    def test_success_make_weather_forcing_next(self, msg_type):
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type))
        assert workers == []
