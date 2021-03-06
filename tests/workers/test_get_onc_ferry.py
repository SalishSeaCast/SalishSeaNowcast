#  Copyright 2013-2021 The Salish Sea MEOPAR contributors
#  and The University of British Columbia
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Unit tests for SalishSeaCast get_onc_ferry worker.
"""
import logging
from types import SimpleNamespace

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import get_onc_ferry


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    return base_config


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(get_onc_ferry, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = get_onc_ferry.main()
        assert worker.name == "get_onc_ferry"
        assert worker.description.startswith(
            "SalishSeaCast worker that downloads data for a specified UTC day from an ONC BC Ferries"
        )

    def test_add_onc_station_arg(self, mock_worker):
        worker = get_onc_ferry.main()
        assert worker.cli.parser._actions[3].dest == "ferry_platform"
        assert worker.cli.parser._actions[3].choices == {"TWDP"}
        assert worker.cli.parser._actions[4].help

    def test_add_run_date_option(self, mock_worker):
        worker = get_onc_ferry.main()
        assert worker.cli.parser._actions[4].dest == "data_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[4].type == expected
        assert worker.cli.parser._actions[4].default == arrow.now().floor("day").shift(
            days=-1
        )
        assert worker.cli.parser._actions[4].help


@pytest.mark.parametrize("ferry_platform", ["TWDP"])
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, ferry_platform, caplog):
        parsed_args = SimpleNamespace(
            ferry_platform=ferry_platform, data_date=arrow.get("2016-09-09")
        )
        caplog.set_level(logging.INFO)

        msg_type = get_onc_ferry.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"2016-09-09 ONC {ferry_platform} ferry data file created"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {ferry_platform}"


@pytest.mark.parametrize("ferry_platform", ["TWDP"])
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, ferry_platform, caplog):
        parsed_args = SimpleNamespace(
            ferry_platform=ferry_platform, data_date=arrow.get("2016-09-09")
        )
        caplog.set_level(logging.CRITICAL)

        msg_type = get_onc_ferry.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"2016-09-09 ONC {ferry_platform} ferry data file creation failed"
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {ferry_platform}"


@pytest.mark.parametrize("ferry_platform", ["TWDP"])
class TestGetONCFerry:
    """Unit tests for get_onc_ferry() function."""

    pass


@pytest.mark.parametrize("ferry_platform", ["TWDP"])
class TestGetNavData:
    """Unit tests for _get_nav_data() function."""

    pass


@pytest.mark.parametrize("ferry_platform", ["TWDP"])
class TestCalcLocationArrays:
    """Unit tests for _calc_location_arrays() function."""

    pass


@pytest.mark.parametrize("ferry_platform", ["TWDP"])
class TestOnCrossing:
    """Unit tests for _on_crossing() function."""

    pass


@pytest.mark.parametrize("ferry_platform", ["TWDP"])
class TestCalcCrossingNumbers:
    """Unit tests for _calc_crossing_numbers() function."""

    pass


@pytest.mark.parametrize("ferry_platform", ["TWDP"])
class TestGetWaterData:
    """Unit tests for _get_water_data() function."""

    pass


@pytest.mark.parametrize(
    "ferry_platform, device, sensors",
    [("TWDP", "TSG", "temperature,conductivity,salinity")],
)
class TestEmptyDeviceData:
    """Unit tests for _empty_device_data() function."""

    def test_empty_device_data(self, ferry_platform, device, sensors, caplog):
        dataset = get_onc_ferry._empty_device_data(
            ferry_platform, device, "2017-12-01", sensors
        )
        for sensor in sensors.split(","):
            assert sensor in dataset.data_vars
            assert dataset.data_vars[sensor].shape == (0,)
            assert dataset.data_vars[sensor].dtype == float
            assert "sampleTime" in dataset.coords
            assert dataset.sampleTime.shape == (0,)
            assert dataset.sampleTime.dtype == "datetime64[ns]"
            assert "sampleTime" in dataset.dims


@pytest.mark.parametrize("ferry_platform", ["TWDP"])
class TestQaqcFilter:
    """Unit tests for _qaqc_filter() function."""

    pass


@pytest.mark.parametrize("ferry_platform", ["TWDP"])
class TestCreateDataset:
    """Unit tests for _create_dataset() function."""

    pass


@pytest.mark.parametrize("ferry_platform", ["TWDP"])
class TestCreateDataarray:
    """Unit tests for _create_dataarray() function."""

    pass
