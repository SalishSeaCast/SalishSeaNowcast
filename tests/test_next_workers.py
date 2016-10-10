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
    Config,
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
        'success 00',
        'success 18',
    ])
    def test_no_next_worker_msg_types(self, msg_type):
        config = {'run types': {'nowcast': {}, 'forecast2': {}}}
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type), config)
        assert workers == []

    def test_success_06_launch_make_runoff_file(self):
        config = {'run types': {'nowcast': {}, 'forecast2': {}}}
        workers = next_workers.after_download_weather(
            Message('download_weather', 'success 06'), config)
        expected = NextWorker(
            'nowcast.workers.make_runoff_file', [], host='localhost')
        assert expected in workers

    @pytest.mark.parametrize('msg_type, args', [
        ('success 06', ['forecast2']),
        ('success 12', ['nowcast']),
    ])
    def test_success_launch_get_NeahBay_ssh(self, msg_type, args):
        config = {'run types': {'nowcast': {}, 'forecast2': {}}}
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type), config)
        expected = NextWorker(
            'nowcast.workers.get_NeahBay_ssh', args, host='localhost')
        assert expected in workers

    @pytest.mark.parametrize('msg_type, args', [
        ('success 06', ['forecast2']),
        ('success 12', ['nowcast+']),
    ])
    def test_success_launch_grib_to_netcdf(self, msg_type, args):
        config = {'run types': {'nowcast': {}, 'forecast2': {}}}
        workers = next_workers.after_download_weather(
            Message('download_weather', msg_type), config)
        expected = NextWorker(
            'nowcast.workers.grib_to_netcdf', args, host='localhost')
        assert expected in workers


class TestAfterMakeRunoffFile:
    """Unit tests for the after_make_runoff_file function.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure',
        'success',
    ])
    def test_no_next_worker_msg_types(self, msg_type):
        workers = next_workers.after_make_runoff_file(
            Message('make_runoff_file', msg_type), Config())
        assert workers == []


class TestAfterGetNeahBaySsh:
    """Unit tests for the after_get_NeahBay_ssh function.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast',
        'failure forecast',
        'failure forecast2',
        'success nowcast',
        'success forecast',
        'success forecast2',
    ])
    def test_no_next_worker_msg_types(self, msg_type):
        workers = next_workers.after_get_NeahBay_ssh(
            Message('get_NeahBay_ssh', msg_type), Config())
        assert workers == []


class TestAfterGribToNetcdf:
    """Unit tests for the after_grib_to_netcdf function.
    """
    @pytest.mark.parametrize('msg_type', [
        'crash',
        'failure nowcast+',
        'failure forecast2',
        'success nowcast+',
        'success forecast2',
    ])
    def test_no_next_worker_msg_types(self, msg_type):
        workers = next_workers.after_grib_to_netcdf(
            Message('grib_to_netcdf', msg_type), Config())
        assert workers == []
