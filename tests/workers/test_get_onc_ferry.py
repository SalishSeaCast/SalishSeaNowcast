#  Copyright 2013 – present The Salish Sea MEOPAR contributors
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
import numpy
import pandas
import pytest
import xarray

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


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "get_onc_ferry" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["get_onc_ferry"]
        assert msg_registry["checklist key"] == "ONC ferry data"

    def test_message_registry_keys(self, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["get_onc_ferry"]
        assert list(msg_registry.keys()) == [
            "checklist key",
            "success TWDP",
            "failure TWDP",
            "crash",
        ]

    def test_lon_lat_ji_map_path(self, prod_config):
        nemo_ji_map = prod_config["observations"]["lon/lat to NEMO ji map"]
        assert nemo_ji_map == "/SalishSeaCast/grid/grid_from_lat_lon_mask999.nc"

    def test_TWDP_section(self, prod_config):
        ferry_config = prod_config["observations"]["ferry data"]["ferries"]["TWDP"]
        assert ferry_config["route name"] == "Tsawwassen - Duke Point"
        expected = "Mobile Platforms, British Columbia Ferries, Tsawwassen - Duke Point"
        assert ferry_config["ONC station description"] == expected
        expected = "{ferry_platform}/{ferry_platform}_TSG_O2_TURBCHLFL_CO2_METEO_1m_{yyyymmdd}.nc"
        assert ferry_config["filepath template"] == expected

    def test_TWDP_location_section(self, prod_config):
        location_config = prod_config["observations"]["ferry data"]["ferries"]["TWDP"][
            "location"
        ]
        assert location_config["stations"] == ["TWDP.N1", "TWDP.N2"]
        assert location_config["device category"] == "NAV"
        assert location_config["sensors"] == ["longitude", "latitude"]
        assert location_config["terminals"] == ["Tsawwassen", "Duke Pt."]

    def test_TWDP_devices_section(self, prod_config):
        devices_config = prod_config["observations"]["ferry data"]["ferries"]["TWDP"][
            "devices"
        ]
        assert devices_config["TSG"]["sensors"] == {
            "temperature": "temperature",
            "conductivity": "conductivity",
            "salinity": "salinity",
        }
        assert devices_config["OXYSENSOR"]["sensors"] == {
            "o2_saturation": "oxygen_saturation",
            "o2_concentration_corrected": "oxygen_corrected",
            "o2_temperature": "temperature",
        }
        assert devices_config["TURBCHLFL"]["sensors"] == {
            "cdom_fluorescence": "cdom_fluorescence",
            "chlorophyll": "chlorophyll",
            "turbidity": "turbidity",
        }
        assert devices_config["CO2SENSOR"]["sensors"] == {
            "co2_partial_pressure": "partial_pressure",
            "co2_concentration_linearized": "co2",
        }
        assert devices_config["TEMPHUMID"]["sensors"] == {
            "air_temperature": "air_temperature",
            "relative_humidity": "REL_HUMIDITY",
        }
        assert devices_config["BARPRESS"]["sensors"] == {
            "barometric_pressure": "barometric_pressure",
        }
        assert devices_config["PYRANOMETER"]["sensors"] == {
            "solar_radiation": "solar_radiation",
        }
        assert devices_config["PYRGEOMETER"]["sensors"] == {
            "longwave_radiation": "downward_radiation",
        }

    def test_dest_dir(self, prod_config):
        ferry_data_config = prod_config["observations"]["ferry data"]
        assert ferry_data_config["dest dir"] == "/results/observations/ONC/ferries/"


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
class TestResampleNavCoord:
    """Unit test for _resample_nav_coord() function."""

    nav_data = xarray.Dataset(
        data_vars={
            "longitude": (["sampleTime"], numpy.linspace(-123.79566, -123.80266, 59))
        },
        coords={
            "sampleTime": pandas.date_range(
                start="2021-03-08T10:14:43.082000000", periods=59, freq="1S"
            )
        },
        attrs={"station": "TWDP.N1"},
    )

    resampled_coord = get_onc_ferry._resample_nav_coord(
        nav_data, "longitude", "degrees_east"
    )

    expected_times = pandas.date_range(
        start="2021-03-08T10:14:00", end="2021-03-08T10:15:00", freq="1min"
    )
    xarray.testing.assert_equal(
        resampled_coord.time,
        xarray.DataArray(expected_times, coords=[("time", expected_times)]),
    )
    numpy.testing.assert_array_almost_equal(
        resampled_coord.data, numpy.array([-123.796626, -123.800186])
    )
    assert resampled_coord.attrs["units"] == "degrees_east"
    assert resampled_coord.attrs["station"] == "TWDP.N1"


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
