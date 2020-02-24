#  Copyright 2013-2020 The Salish Sea MEOPAR contributors
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
"""Unit tests for nowcast.next_workers module.
"""
import arrow
import pytest
from nemo_nowcast import Message, NextWorker

from nowcast import next_workers


@pytest.fixture
def config():
    """Nowcast system config dict data structure;
    a mock for :py:attr:`nemo_nowcast.config.Config._dict`.
    """
    return {
        "rivers": {
            "stations": {
                "Capilano": "08GA010",
                "Englishman": "08HB002",
                "Fraser": "08MF005",
            }
        },
        "observations": {
            "ctd data": {"stations": ["SCVIP", "SEVIP", "USDDL"]},
            "ferry data": {"ferries": {"TWDP": {}}},
            "hadcp data": {},
        },
        "run types": {
            "nowcast": {},
            "nowcast-dev": {},
            "nowcast-green": {},
            "nowcast-agrif": {},
            "forecast": {},
            "forecast2": {},
        },
        "run": {
            "enabled hosts": {
                "arbutus.cloud": {
                    "shared storage": False,
                    "make forcing links": True,
                    "run types": ["nowcast", "forecast", "forecast2", "nowcast-green"],
                },
                "salish": {
                    "shared storage": True,
                    "make forcing links": True,
                    "run types": ["nowcast-dev"],
                },
                "orcinus": {
                    "shared storage": False,
                    "make forcing links": False,
                    "run types": ["nowcast-agrif"],
                },
            },
            "hindcast hosts": {"cedar": {}},
        },
        "wave forecasts": {"host": "arbutus.cloud", "run when": "after nowcast-green"},
        "vhfr fvcom runs": {"host": "arbutus.cloud"},
    }


@pytest.fixture
def checklist():
    """Nowcast system state checklist dict data structure;
    a mock for :py:attr:`nemo_nowcast.manager.NowcastManager.checklist`.
    """
    return {}


class TestAfterDownloadWeather:
    """Unit tests for the after_download_weather function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure 2.5km 00",
            "failure 2.5km 06",
            "failure 2.5km 12",
            "failure 2.5km 18",
            "success 2.5km 00",
            "failure 1km 00",
            "failure 1km 12",
            "success 2.5km 18",
            "success 1km 00",
            "success 1km 12",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_download_weather(
            Message("download_weather", msg_type), config, checklist
        )
        assert workers == []

    def test_success_2_5_km_06(self, config, checklist, monkeypatch):
        def mock_now():
            return arrow.get("2018-12-27")

        monkeypatch.setattr(next_workers.arrow, "now", mock_now)

        def mock_utcnow():
            return arrow.get("2018-12-27")

        monkeypatch.setattr(next_workers.arrow, "utcnow", mock_utcnow)

        workers = next_workers.after_download_weather(
            Message("download_weather", "success 2.5km 06"), config, checklist
        )
        expected = [
            NextWorker(
                "nowcast.workers.collect_river_data",
                ["Capilano", "--data-date", "2018-12-26"],
                host="localhost",
            ),
            NextWorker(
                "nowcast.workers.collect_river_data",
                ["Englishman", "--data-date", "2018-12-26"],
                host="localhost",
            ),
            NextWorker(
                "nowcast.workers.collect_river_data",
                ["Fraser", "--data-date", "2018-12-26"],
                host="localhost",
            ),
            NextWorker("nowcast.workers.get_onc_ctd", ["SCVIP"], host="localhost"),
            NextWorker("nowcast.workers.get_onc_ctd", ["SEVIP"], host="localhost"),
            NextWorker("nowcast.workers.get_onc_ctd", ["USDDL"], host="localhost"),
            NextWorker("nowcast.workers.get_onc_ferry", ["TWDP"], host="localhost"),
            NextWorker(
                "nowcast.workers.get_NeahBay_ssh", ["forecast2"], host="localhost"
            ),
            NextWorker(
                "nowcast.workers.grib_to_netcdf", ["forecast2"], host="localhost"
            ),
        ]
        assert len(workers) == len(expected)
        for next_worker in expected:
            assert next_worker in workers

    def test_success_2_5_km_12(self, config, checklist):
        workers, race_condition_workers = next_workers.after_download_weather(
            Message("download_weather", "success 2.5km 12"), config, checklist
        )
        expected = [
            NextWorker(
                "nowcast.workers.get_NeahBay_ssh", ["nowcast"], host="localhost"
            ),
            NextWorker(
                "nowcast.workers.grib_to_netcdf", ["nowcast+"], host="localhost"
            ),
            NextWorker("nowcast.workers.download_live_ocean", [], host="localhost"),
        ]
        assert len(workers) == len(expected)
        for next_worker in expected:
            assert next_worker in workers
        assert race_condition_workers == {"grib_to_netcdf", "make_live_ocean_files"}


class TestAfterCollectWeather:
    """Unit tests for the after_collect_weather function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure 2.5km 00",
            "failure 2.5km 06",
            "failure 2.5km 12",
            "failure 2.5km 18",
            "failure 1km 00",
            "failure 1km 12",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_collect_weather(
            Message("collect_weather", msg_type), config, checklist
        )
        assert workers == []

    def test_success_2_5_km_06(self, config, checklist, monkeypatch):
        def mock_now():
            return arrow.get("2018-12-27")

        monkeypatch.setattr(next_workers.arrow, "now", mock_now)

        def mock_utcnow():
            return arrow.get("2018-12-27")

        monkeypatch.setattr(next_workers.arrow, "utcnow", mock_utcnow)

        workers = next_workers.after_collect_weather(
            Message("collect_weather", "success 2.5km 06"), config, checklist
        )
        expected = [
            NextWorker(
                "nowcast.workers.collect_river_data",
                ["Capilano", "--data-date", "2018-12-26"],
                host="localhost",
            ),
            NextWorker(
                "nowcast.workers.collect_river_data",
                ["Englishman", "--data-date", "2018-12-26"],
                host="localhost",
            ),
            NextWorker(
                "nowcast.workers.collect_river_data",
                ["Fraser", "--data-date", "2018-12-26"],
                host="localhost",
            ),
            NextWorker("nowcast.workers.get_onc_ctd", ["SCVIP"], host="localhost"),
            NextWorker("nowcast.workers.get_onc_ctd", ["SEVIP"], host="localhost"),
            NextWorker("nowcast.workers.get_onc_ctd", ["USDDL"], host="localhost"),
            NextWorker("nowcast.workers.get_onc_ferry", ["TWDP"], host="localhost"),
            NextWorker(
                "nowcast.workers.get_NeahBay_ssh", ["forecast2"], host="localhost"
            ),
            NextWorker(
                "nowcast.workers.grib_to_netcdf", ["forecast2"], host="localhost"
            ),
            NextWorker(
                "nowcast.workers.collect_weather", ["12", "2.5km"], host="localhost"
            ),
        ]
        assert len(workers) == len(expected)
        for next_worker in expected:
            assert next_worker in workers

    def test_success_2_5_km_12(self, config, checklist):
        workers, race_condition_workers = next_workers.after_collect_weather(
            Message("collect_weather", "success 2.5km 12"), config, checklist
        )
        expected = [
            NextWorker(
                "nowcast.workers.get_NeahBay_ssh", ["nowcast"], host="localhost"
            ),
            NextWorker(
                "nowcast.workers.grib_to_netcdf", ["nowcast+"], host="localhost"
            ),
            NextWorker("nowcast.workers.download_live_ocean", [], host="localhost"),
            NextWorker(
                "nowcast.workers.collect_weather", ["18", "2.5km"], host="localhost"
            ),
        ]
        assert len(workers) == len(expected)
        for next_worker in expected:
            assert next_worker in workers
        assert race_condition_workers == {"grib_to_netcdf", "make_live_ocean_files"}

    def test_success_2_5_km_18(self, config, checklist):
        workers = next_workers.after_collect_weather(
            Message("collect_weather", "success 2.5km 18"), config, checklist
        )
        expected = [
            NextWorker(
                "nowcast.workers.download_weather",
                ["00", "1km", "--no-verify-certs"],
                host="localhost",
            ),
            NextWorker(
                "nowcast.workers.download_weather",
                ["12", "1km", "--no-verify-certs"],
                host="localhost",
            ),
            NextWorker(
                "nowcast.workers.collect_weather", ["00", "2.5km"], host="localhost"
            ),
        ]
        assert len(workers) == len(expected)
        for next_worker in expected:
            assert next_worker in workers

    def test_success_2_5_km_00(self, config, checklist):
        workers = next_workers.after_collect_weather(
            Message("collect_weather", "success 2.5km 00"), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.collect_weather", ["06", "2.5km"], host="localhost"
        )
        assert expected in workers


class TestAfterCollectRiverData:
    """Unit tests for the after_collect_river_data function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_collect_river_data(
            Message("collect_river_data", msg_type), config, checklist
        )
        assert workers == []

    def test_success_Fraser_launch_make_runoff_file(
        self, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(checklist, "river data", {"river name": "Fraser"})
        workers = next_workers.after_collect_river_data(
            Message("collect_river_data", "success"), config, checklist
        )
        expected = NextWorker("nowcast.workers.make_runoff_file", [], host="localhost")
        assert expected in workers

    def test_success_Englishman_no_launch_make_runoff_file(
        self, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(checklist, "river data", {"river name": "Englishman"})
        workers = next_workers.after_collect_river_data(
            Message("collect_river_data", "success"), config, checklist
        )
        assert workers == []


class TestAfterMakeRunoffFile:
    """Unit tests for the after_make_runoff_file function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure", "success"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_runoff_file(
            Message("make_runoff_file", msg_type), config, checklist
        )
        assert workers == []


class TestAfterGetNeahBaySsh:
    """Unit tests for the after_get_NeahBay_ssh function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure nowcast",
            "failure forecast",
            "failure forecast2",
            "success nowcast",
            "success forecast2",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_get_NeahBay_ssh(
            Message("get_NeahBay_ssh", msg_type), config, checklist
        )
        assert workers == []

    def test_success_forecast_launch_upload_forcing_ssh(self, config, checklist):
        workers = next_workers.after_get_NeahBay_ssh(
            Message("get_NeahBay_ssh", "success forecast"), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.upload_forcing",
            args=["arbutus.cloud", "ssh"],
            host="localhost",
        )
        assert expected in workers


class TestAfterGribToNetcdf:
    """Unit tests for the after_grib_to_netcdf function.
    """

    @pytest.mark.parametrize(
        "msg_type", ["crash", "failure nowcast+", "failure forecast2"]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_grib_to_netcdf(
            Message("grib_to_netcdf", msg_type), config, checklist
        )
        assert workers == []

    def test_success_forecast2_launch_upload_forcing(self, config, checklist):
        workers = next_workers.after_grib_to_netcdf(
            Message("grib_to_netcdf", "success forecast2"), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.upload_forcing",
            args=["arbutus.cloud", "forecast2"],
            host="localhost",
        )
        assert expected in workers

    def test_success_forecast2_shared_storage_no_launch_upload_forcing(
        self, config, checklist
    ):
        workers = next_workers.after_grib_to_netcdf(
            Message("grib_to_netcdf", "success forecast2"), config, checklist
        )
        not_expected = NextWorker(
            "nowcast.workers.upload_forcing",
            args=["saliish", "forecast2"],
            host="localhost",
        )
        assert not_expected not in workers

    @pytest.mark.parametrize("msg_type", ["success nowcast+", "success forecast2"])
    def test_success_no_launch_upload_forcing_nowcastp(
        self, msg_type, config, checklist
    ):
        workers = next_workers.after_grib_to_netcdf(
            Message("grib_to_netcdf", msg_type), config, checklist
        )
        not_expected = NextWorker(
            "nowcast.workers.upload_forcing",
            args=["arbutus.cloud", "nowcast+"],
            host="localhost",
        )
        assert not_expected not in workers

    def test_success_nowcastp_launch_ping_erddap_weather(self, config, checklist):
        workers = next_workers.after_grib_to_netcdf(
            Message("grib_to_netcdf", "success nowcast+"), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.ping_erddap", args=["weather"], host="localhost"
        )
        assert expected in workers


class TestAfterGetONC_CTD:
    """Unit tests for the after_get_onc_ctd function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_get_onc_ctd(
            Message("get_onc_ctd", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize("ctd_stn", ["SCVIP", "SEVIP"])
    #  USDDL node out of service on 11-Mar-2019; may return to service in mid-Sep-2019
    # @pytest.mark.parametrize("ctd_stn", ["SCVIP", "SEVIP", "USDDL"])
    def test_success_launch_ping_erddap(self, ctd_stn, config, checklist):
        workers = next_workers.after_get_onc_ctd(
            Message("get_onc_ctd", "success {}".format(ctd_stn)), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.ping_erddap",
            args=["{}-CTD".format(ctd_stn)],
            host="localhost",
        )
        assert expected in workers


class TestAfterGetONC_Ferry:
    """Unit tests for the after_get_onc_ferry function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_get_onc_ferry(
            Message("get_onc_ferry", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize("ferry_platform", ["TWDP"])
    def test_success_launch_ping_erddap(self, ferry_platform, config, checklist):
        workers = next_workers.after_get_onc_ferry(
            Message("get_onc_ferry", "success {}".format(ferry_platform)),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.ping_erddap",
            args=["{}-ferry".format(ferry_platform)],
            host="localhost",
        )
        assert expected in workers


class TestAfterDownloadLiveOcean:
    """Unit tests for the after_download_live_ocean function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_download_live_ocean(
            Message("download_live_ocean", msg_type), config, checklist
        )
        assert workers == []

    def test_success_launch_make_live_ocean_files(self, config, checklist, monkeypatch):
        # Ensure that run date for make_live_ocean_files is same as most recently downloaded
        # files in the event that the checklist was not cleared after the previous day's
        # operations
        monkeypatch.setitem(
            checklist, "Live Ocean products", {"2017-02-14": [], "2017-02-15": []}
        )
        workers = next_workers.after_download_live_ocean(
            Message("download_live_ocean", "success"), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.make_live_ocean_files",
            args=["--run-date", "2017-02-15"],
            host="localhost",
        )
        assert expected in workers


class TestAfterMakeLiveOceanFiles:
    """Unit tests for the after_make_live_ocean_files function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_live_ocean_files(
            Message("make_live_ocean_files", msg_type), config, checklist
        )
        assert workers == []

    def test_success_launch_upload_forcing(self, config, checklist):
        workers = next_workers.after_make_live_ocean_files(
            Message("make_live_ocean_files", "success"), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.upload_forcing",
            args=["arbutus.cloud", "nowcast+"],
            host="localhost",
        )
        assert expected in workers


class TestAfterMakeTurbidityFile:
    """Unit tests for the after_make_turbidity_file function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_turbidity_file(
            Message("make_turbidity_file", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize("host_name", ["arbutus.cloud", "orcinus"])
    def test_success_launch_upload_forcing(self, host_name, config, checklist):
        workers = next_workers.after_make_turbidity_file(
            Message("make_turbidity_file", "success"), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.upload_forcing",
            args=[host_name, "turbidity"],
            host="localhost",
        )
        assert expected in workers

    def test_success_no_launch_upload_forcing_salish(self, config, checklist):
        workers = next_workers.after_make_turbidity_file(
            Message("make_turbidity_file", "success"), config, checklist
        )
        not_expected = NextWorker(
            "nowcast.workers.upload_forcing",
            args=["salish-nowcast", "turbidity"],
            host="localhost",
        )
        assert not_expected not in workers


class TestAfterUploadForcing:
    """Unit tests for the after_upload_forcing function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure nowcast+",
            "failure forecast2",
            "failure ssh",
            "failure turbidity",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_upload_forcing(
            Message("upload_forcing", msg_type), config, checklist
        )
        assert workers == []

    def test_msg_payload_missing_host_name(self, config, checklist):
        workers = next_workers.after_upload_forcing(
            Message("upload_forcing", "crash"), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize("run_type", ["nowcast+", "ssh", "forecast2"])
    def test_success_launch_make_forcing_links(
        self, run_type, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            config,
            "run",
            {
                "enabled hosts": {
                    "arbutus.cloud": {
                        "run types": "nowcast-agrif",
                        "make forcing links": True,
                    }
                }
            },
        )
        workers = next_workers.after_upload_forcing(
            Message(
                "upload_forcing",
                f"success {run_type}",
                {"arbutus.cloud": f"2016-10-11 {run_type}"},
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_forcing_links",
            args=["arbutus.cloud", run_type],
            host="localhost",
        )
        assert expected in workers

    @pytest.mark.parametrize("run_type", ["nowcast+", "ssh", "forecast2"])
    def test_success_no_launch_make_forcing_links(
        self, run_type, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            config,
            "run",
            {
                "enabled hosts": {
                    "cedar-hindcast": {"run types": {}, "make forcing links": False}
                }
            },
        )
        workers = next_workers.after_upload_forcing(
            Message(
                "upload_forcing",
                f"success {run_type}",
                {"cedar-hindcast": f"2018-04-03 {run_type}"},
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_forcing_links",
            args=["cedar-hindcast", run_type],
            host="localhost",
        )
        assert expected not in workers

    def test_success_turbidity_launch_make_forcing_links_nowcast_green(
        self, config, checklist
    ):
        workers = next_workers.after_upload_forcing(
            Message(
                "upload_forcing",
                "success turbidity",
                {"arbutus.cloud": "2017-08-10 turbidity"},
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_forcing_links",
            args=["arbutus.cloud", "nowcast-green"],
            host="localhost",
        )
        assert expected in workers

    def test_success_turbidity_no_launch_make_forcing_links_agrif(
        self, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            config,
            "run",
            {
                "enabled hosts": {
                    "orcinus": {
                        "run types": "nowcast-agrif",
                        "make forcing links": False,
                    }
                }
            },
        )
        workers = next_workers.after_upload_forcing(
            Message(
                "upload_forcing",
                "success turbidity",
                {"orcinus": "2018-04-03 turbidity"},
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_forcing_links",
            args=["orcinus", "nowcast-agrif"],
            host="localhost",
        )
        assert expected not in workers

    def test_success_turbidity_launch_make_forcing_links_agrif(
        self, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            config,
            "run",
            {
                "enabled hosts": {
                    "orcinus": {
                        "run types": "nowcast-agrif",
                        "make forcing links": True,
                    }
                }
            },
        )
        workers = next_workers.after_upload_forcing(
            Message(
                "upload_forcing",
                "success turbidity",
                {"orcinus": "2018-04-03 turbidity"},
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_forcing_links",
            args=["orcinus", "nowcast-agrif"],
            host="localhost",
        )
        assert expected in workers


class TestAfterMakeForcingLinks:
    """Unit tests for the after_make_forcing_links function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure nowcast+",
            "failure nowcast-green",
            "failure nowcast-agrif",
            "failure forecast2",
            "failure ssh",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_forcing_links(
            Message("make_forcing_links", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "msg_type, args, host_name",
        [
            (
                "success nowcast+",
                ["arbutus.cloud", "nowcast", "--run-date", "2016-10-23"],
                "arbutus.cloud",
            ),
            (
                "success nowcast-green",
                ["arbutus.cloud", "nowcast-green", "--run-date", "2016-10-23"],
                "arbutus.cloud",
            ),
            (
                "success nowcast+",
                ["salish", "nowcast-dev", "--run-date", "2016-10-23"],
                "salish",
            ),
            (
                "success ssh",
                ["arbutus.cloud", "forecast", "--run-date", "2016-10-23"],
                "arbutus.cloud",
            ),
            (
                "success forecast2",
                ["arbutus.cloud", "forecast2", "--run-date", "2016-10-23"],
                "arbutus.cloud",
            ),
        ],
    )
    def test_success_launch_run_NEMO(
        self, msg_type, args, host_name, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            checklist, "forcing links", {args[0]: {"links": "", "run date": args[-1]}}
        )
        workers = next_workers.after_make_forcing_links(
            Message("make_forcing_links", msg_type, payload={args[0]: ""}),
            config,
            checklist,
        )
        expected = NextWorker("nowcast.workers.run_NEMO", args=args, host=host_name)
        assert expected in workers

    @pytest.mark.parametrize(
        "msg_type, args",
        [
            (
                "success nowcast-agrif",
                ["orcinus", "nowcast-agrif", "--run-date", "2018-05-03"],
            )
        ],
    )
    def test_success_nowcast_agrif_launch_run_NEMO_agrif(
        self, msg_type, args, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            checklist, "forcing links", {args[0]: {"links": "", "run date": args[-1]}}
        )
        workers = next_workers.after_make_forcing_links(
            Message("make_forcing_links", msg_type, payload={args[0]: ""}),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.run_NEMO_agrif", args=args, host="localhost"
        )
        assert expected in workers


class TestAfterRunNEMO:
    """Unit tests for the after_run_NEMO function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure nowcast",
            "failure nowcast-green",
            "failure nowcast-dev",
            "failure forecast",
            "failure forecast2",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_run_NEMO(
            Message("run_NEMO", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "msg_type, host",
        [
            ("success nowcast", "arbutus.cloud"),
            ("success nowcast-green", "arbutus.cloud"),
            ("success nowcast-dev", "salish"),
            ("success forecast", "arbutus.cloud"),
            ("success forecast2", "arbutus.cloud"),
        ],
    )
    def test_success_launch_watch_NEMO(self, msg_type, host, config, checklist):
        run_type = msg_type.split()[1]
        workers = next_workers.after_run_NEMO(
            Message("run_NEMO", msg_type, {run_type: {"host": host}}), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.watch_NEMO", args=[host, run_type], host=host
        )
        assert workers[0] == expected


class TestAfterWatchNEMO:
    """Unit tests for the after_watch_NEMO function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure nowcast",
            "failure nowcast-green",
            "failure nowcast-dev",
            "failure forecast",
            "failure forecast2",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_watch_NEMO(
            Message("watch_NEMO", msg_type), config, checklist
        )
        assert workers == []

    def test_success_nowcast_launch_get_NeahBay_ssh_forecast(self, config, checklist):
        workers = next_workers.after_watch_NEMO(
            Message(
                "watch_NEMO",
                "success nowcast",
                {
                    "nowcast": {
                        "host": "arbutus.cloud",
                        "run date": "2016-10-16",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.get_NeahBay_ssh", args=["forecast"], host="localhost"
        )
        assert workers[0] == expected

    def test_success_nowcast_launch_make_fvcom_boundary_x2_nowcast(
        self, config, checklist
    ):
        workers = next_workers.after_watch_NEMO(
            Message(
                "watch_NEMO",
                "success nowcast",
                {
                    "nowcast": {
                        "host": "arbutus.cloud",
                        "run date": "2018-01-20",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_fvcom_boundary",
            args=["arbutus.cloud", "x2", "nowcast"],
            host="arbutus.cloud",
        )
        assert expected in workers

    def test_success_nowcast_launch_make_fvcom_boundary_r12_nowcast(
        self, config, checklist
    ):
        workers = next_workers.after_watch_NEMO(
            Message(
                "watch_NEMO",
                "success nowcast",
                {
                    "nowcast": {
                        "host": "arbutus.cloud",
                        "run date": "2019-04-03",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_fvcom_boundary",
            args=["arbutus.cloud", "r12", "nowcast"],
            host="arbutus.cloud",
        )
        assert expected in workers

    def test_success_forecast_launch_make_turbidity_file(self, config, checklist):
        workers = next_workers.after_watch_NEMO(
            Message(
                "watch_NEMO",
                "success forecast",
                {
                    "forecast": {
                        "host": "arbutus.cloud",
                        "run date": "2017-08-10",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_turbidity_file",
            args=["--run-date", "2017-08-10"],
            host="localhost",
        )
        assert workers[0] == expected

    def test_success_forecast_launch_make_ww3_wind_file_forecast(
        self, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(config["wave forecasts"], "run when", "after forecast")
        workers, race_condition_workers = next_workers.after_watch_NEMO(
            Message(
                "watch_NEMO",
                "success forecast",
                {
                    "forecast": {
                        "host": "arbutus.cloud",
                        "run date": "2017-04-14",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_ww3_wind_file",
            args=["arbutus.cloud", "forecast"],
            host="arbutus.cloud",
        )
        assert workers[0] == expected
        assert race_condition_workers == {"make_ww3_wind_file", "make_ww3_current_file"}

    def test_success_forecast_launch_make_ww3_current_file_forecast(
        self, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(config["wave forecasts"], "run when", "after forecast")
        workers, race_condition_workers = next_workers.after_watch_NEMO(
            Message(
                "watch_NEMO",
                "success forecast",
                {
                    "forecast": {
                        "host": "arbutus.cloud",
                        "run date": "2017-04-14",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_ww3_current_file",
            args=["arbutus.cloud", "forecast"],
            host="arbutus.cloud",
        )
        assert workers[1] == expected
        assert race_condition_workers == {"make_ww3_wind_file", "make_ww3_current_file"}

    def test_success_forecast_no_launch_make_fvcom_boundary(self, config, checklist):
        workers = next_workers.after_watch_NEMO(
            Message(
                "watch_NEMO",
                "success forecast",
                {
                    "forecast": {
                        "host": "arbutus.cloud",
                        "run date": "2018-01-20",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_fvcom_boundary",
            args=["arbutus.cloud", "x2", "forecast"],
            host="arbutus.cloud",
        )
        assert expected not in workers

    def test_success_forecast2_launch_make_ww3_wind_file_forecast2(
        self, config, checklist
    ):
        workers, race_condition_workers = next_workers.after_watch_NEMO(
            Message(
                "watch_NEMO",
                "success forecast2",
                {
                    "forecast2": {
                        "host": "arbutus.cloud",
                        "run date": "2017-04-14",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_ww3_wind_file",
            args=["arbutus.cloud", "forecast2"],
            host="arbutus.cloud",
        )
        assert workers[0] == expected
        assert race_condition_workers == {"make_ww3_wind_file", "make_ww3_current_file"}

    def test_success_forecast2_launch_make_ww3_current_file_forecast2(
        self, config, checklist
    ):
        workers, race_condition_workers = next_workers.after_watch_NEMO(
            Message(
                "watch_NEMO",
                "success forecast2",
                {
                    "forecast2": {
                        "host": "arbutus.cloud",
                        "run date": "2017-04-14",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_ww3_current_file",
            args=["arbutus.cloud", "forecast2"],
            host="arbutus.cloud",
        )
        assert workers[1] == expected
        assert race_condition_workers == {"make_ww3_wind_file", "make_ww3_current_file"}

    def test_success_nowcast_green_launch_make_ww3_wind_file_forecast(
        self, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(config["wave forecasts"], "run when", "after nowcast-green")
        workers, race_condition_workers = next_workers.after_watch_NEMO(
            Message(
                "watch_NEMO",
                "success nowcast-green",
                {
                    "nowcast-green": {
                        "host": "arbutus.cloud",
                        "run date": "2017-04-14",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_ww3_wind_file",
            args=["arbutus.cloud", "forecast"],
            host="arbutus.cloud",
        )
        assert workers[0] == expected
        assert race_condition_workers == {"make_ww3_wind_file", "make_ww3_current_file"}

    def test_success_nowcast_green_launch_make_ww3_current_file_forecast(
        self, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(config["wave forecasts"], "run when", "after nowcast-green")
        workers, race_condition_workers = next_workers.after_watch_NEMO(
            Message(
                "watch_NEMO",
                "success nowcast-green",
                {
                    "nowcast-green": {
                        "host": "arbutus.cloud",
                        "run date": "2017-04-14",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_ww3_current_file",
            args=["arbutus.cloud", "forecast"],
            host="arbutus.cloud",
        )
        assert workers[1] == expected
        assert race_condition_workers == {"make_ww3_wind_file", "make_ww3_current_file"}

    def test_success_nowcast_green_launch_mk_forcing_links_nowcastp_shrdstrg(
        self, config, checklist
    ):
        workers, race_condition_workers = next_workers.after_watch_NEMO(
            Message(
                "watch_NEMO",
                "success nowcast-green",
                {
                    "nowcast-green": {
                        "host": "arbutus.cloud",
                        "run date": "2017-05-31",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_forcing_links",
            args=["salish", "nowcast+", "--shared-storage"],
            host="localhost",
        )
        assert expected in workers
        assert race_condition_workers == {"make_ww3_wind_file", "make_ww3_current_file"}

    @pytest.mark.parametrize(
        "msg",
        [
            Message(
                "watch_NEMO",
                "success nowcast",
                {
                    "nowcast": {
                        "host": "arbutus.cloud",
                        "run date": "2016-10-15",
                        "completed": True,
                    }
                },
            ),
            Message(
                "watch_NEMO",
                "success forecast",
                {
                    "forecast": {
                        "host": "arbutus.cloud",
                        "run date": "2016-10-15",
                        "completed": True,
                    }
                },
            ),
            Message(
                "watch_NEMO",
                "success nowcast-green",
                {
                    "nowcast-green": {
                        "host": "arbutus.cloud",
                        "run date": "2016-10-15",
                        "completed": True,
                    }
                },
            ),
            Message(
                "watch_NEMO",
                "success forecast2",
                {
                    "forecast2": {
                        "host": "arbutus.cloud",
                        "run date": "2016-10-15",
                        "completed": True,
                    }
                },
            ),
        ],
    )
    def test_success_launch_download_results(self, msg, config, checklist):
        workers = next_workers.after_watch_NEMO(msg, config, checklist)
        if isinstance(workers, tuple):
            workers, race_condition_workers = workers
        else:
            race_condition_workers = {}
        run_type = msg.type.split()[1]
        expected = NextWorker(
            "nowcast.workers.download_results",
            args=[
                msg.payload[run_type]["host"],
                run_type,
                "--run-date",
                msg.payload[run_type]["run date"],
            ],
            host="localhost",
        )
        assert expected in workers
        if race_condition_workers:
            assert race_condition_workers == {
                "make_ww3_wind_file",
                "make_ww3_current_file",
            }

    @pytest.mark.parametrize(
        "msg",
        [
            Message(
                "watch_NEMO",
                "success nowcast-dev",
                {
                    "nowcast-dev": {
                        "host": "salish",
                        "run date": "2016-10-15",
                        "completed": True,
                    }
                },
            )
        ],
    )
    def test_success_nowcast_dev_no_launch_download_results(
        self, msg, config, checklist
    ):
        workers = next_workers.after_watch_NEMO(msg, config, checklist)
        download_results = NextWorker(
            "nowcast.workers.download_results",
            args=[
                msg.payload["nowcast-dev"]["host"],
                msg.type.split()[1],
                "--run-date",
                msg.payload["nowcast-dev"]["run date"],
            ],
            host="localhost",
        )
        assert download_results not in workers


class TestAfterRunNEMO_AGRIF:
    """Unit tests for the after_run_NEMO_agrif function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_run_NEMO_agrif(
            Message("run_NEMO_agrif", msg_type), config, checklist
        )
        assert workers == []

    def test_success_launch_watch_NEMO(self, config, checklist):
        workers = next_workers.after_run_NEMO_agrif(
            Message(
                "run_NEMO_agrif",
                "success",
                {"nowcast-agrif": {"host": "orcinus", "job id": "9379405.orca2.ibb"}},
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.watch_NEMO_agrif",
            args=["orcinus", "9379405.orca2.ibb"],
            host="localhost",
        )
        assert workers == [expected]


class TestAfterWatchNEMO_AGRIF:
    """Unit tests for the after_watch_NEMO_agrif function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_watch_NEMO_agrif(
            Message("warch_NEMO_agrif", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "msg",
        [
            Message(
                "watch_NEMO_agrif",
                "success",
                {
                    "nowcast-agrif": {
                        "host": "orcinus",
                        "job id": "9305855",
                        "run date": "2018-05-22",
                        "completed": True,
                    }
                },
            )
        ],
    )
    def test_success_launch_download_results(self, msg, config, checklist):
        workers = next_workers.after_watch_NEMO_agrif(msg, config, checklist)
        expected = NextWorker(
            "nowcast.workers.download_results",
            args=[
                msg.payload["nowcast-agrif"]["host"],
                "nowcast-agrif",
                "--run-date",
                msg.payload["nowcast-agrif"]["run date"],
            ],
            host="localhost",
        )
        assert expected in workers


class TestAfterMakeFVCOMBoundary:
    """Unit tests for the after_make_fvcom_boundary function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        ["crash", "failure x2 nowcast", "failure x2 forecast", "failure r12 nowcast"],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_fvcom_boundary(
            Message("make_fvcom_boundary", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "model_config, run_type",
        [("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")],
    )
    def test_success_launch_make_fvcom_atmos_forcing(
        self, model_config, run_type, config, checklist
    ):

        msg = Message(
            "make_fvcom_boundary",
            f"success {model_config} {run_type}",
            payload={
                run_type: {
                    "run date": "2018-03-16",
                    "model config": model_config,
                    "open boundary file": f"input/bdy_{model_config}_nowcast_btrp_20180316.nc",
                }
            },
        )
        workers = next_workers.after_make_fvcom_boundary(msg, config, checklist)
        expected = NextWorker(
            "nowcast.workers.make_fvcom_atmos_forcing",
            args=[model_config, run_type, "--run-date", "2018-03-16"],
            host="localhost",
        )
        assert expected in workers

    @pytest.mark.parametrize(
        "model_config, run_type",
        [("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")],
    )
    def test_success_launch_make_fvcom_rivers_forcing(
        self, model_config, run_type, config, checklist
    ):
        workers = next_workers.after_make_fvcom_boundary(
            Message(
                "make_fvcom_boundary",
                f"success {model_config} {run_type}",
                payload={
                    run_type: {
                        "run date": "2019-02-06",
                        "model config": model_config,
                        "open boundary file": f"input/bdy_{model_config}_nowcast_btrp_20180316.nc",
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_fvcom_rivers_forcing",
            args=["arbutus.cloud", model_config, run_type, "--run-date", "2019-02-06"],
            host="arbutus.cloud",
        )
        assert expected in workers


class TestAfterMakeFVCOMRiversForcing:
    """Unit tests for the after_make_fvcom_rivers_forcing function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "success x2 nowcast",
            "failure x2 nowcast",
            "success x2 forecast",
            "failure x2 forecast",
            "success r12 nowcast",
            "failure r12 nowcast",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_fvcom_rivers_forcing(
            Message("make_fvcom_rivers_forcing", msg_type), config, checklist
        )
        assert workers == []


class TestAfterMakeFVCOMAtmosForcing:
    """Unit tests for the after_make_fvcom_atmos_forcing function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        ["crash", "failure x2 nowcast", "failure x2 forecast", "failure r12 nowcast"],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_fvcom_atmos_forcing(
            Message("make_fvcom_atmos_forcing", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "model_config, run_type",
        [("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")],
    )
    def test_success_launch_upload_fvcom_atmos_forcing(
        self, model_config, run_type, config, checklist
    ):
        msg = Message(
            "make_fvcom_atmos_forcing",
            f"success {model_config} {run_type}",
            payload={
                run_type: {"run date": "2018-04-04", "model config": model_config}
            },
        )
        workers = next_workers.after_make_fvcom_atmos_forcing(msg, config, checklist)
        expected = NextWorker(
            "nowcast.workers.upload_fvcom_atmos_forcing",
            args=["arbutus.cloud", model_config, run_type, "--run-date", "2018-04-04"],
            host="localhost",
        )
        assert expected in workers


class TestAfterUploadFVCOMAtmosForcing:
    """Unit tests for the after_upload_fvcom_atmos_forcing function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        ["crash", "failure x2 nowcast", "failure x2 forecast", "failure r12 nowcast"],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_upload_fvcom_atmos_forcing(
            Message("upload_fvcom_atmos_forcing", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "model_config, run_type",
        [("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")],
    )
    def test_success_launch_run_fvcom(self, model_config, run_type, config, checklist):
        msg = Message(
            "upload_fvcom_atmos_forcing",
            f"success {model_config} {run_type}",
            payload={
                "arbutus.cloud": {
                    run_type: {"run date": "2018-04-04", "model config": model_config}
                }
            },
        )
        workers = next_workers.after_upload_fvcom_atmos_forcing(msg, config, checklist)
        expected = NextWorker(
            "nowcast.workers.run_fvcom",
            args=["arbutus.cloud", model_config, run_type, "--run-date", "2018-04-04"],
            host="arbutus.cloud",
        )
        assert expected in workers


class TestAfterRunFVCOM:
    """Unit tests for the after_run_fvcom function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        ["crash", "failure x2 nowcast", "failure x2 forecast", "failure r12 nowcast"],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_run_fvcom(
            Message("run_fvcom", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "model_config, run_type",
        [("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")],
    )
    def test_success_launch_watch_fvcom(
        self, model_config, run_type, config, checklist
    ):
        workers = next_workers.after_run_fvcom(
            Message(
                "run_fvcom",
                f"success {model_config} {run_type}",
                {
                    f"{model_config} {run_type}": {
                        "host": "arbutus.cloud",
                        "model config": model_config,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.watch_fvcom",
            args=["arbutus.cloud", model_config, run_type],
            host="arbutus.cloud",
        )
        assert workers == [expected]


class TestAfterWatchFVCOM:
    """Unit tests for the after_watch_fvcom function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        ["crash", "failure x2 nowcast", "failure x2 forecast", "failure r12 nowcast"],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_watch_fvcom(
            Message("watch_fvcom", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "model_config, run_type",
        [("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")],
    )
    def test_success_launch_download_fvcom_results(
        self, model_config, run_type, config, checklist
    ):
        workers = next_workers.after_watch_fvcom(
            Message(
                "watch_fvcom",
                f"success {model_config} {run_type}",
                {
                    f"{model_config} {run_type}": {
                        "host": "arbutus.cloud",
                        "model config": model_config,
                        "run date": "2019-02-27",
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.download_fvcom_results",
            args=["arbutus.cloud", model_config, run_type, "--run-date", "2019-02-27"],
            host="localhost",
        )
        assert expected in workers

    def test_success_nowcast_launch_make_fvcom_boundary_x2_forecast(
        self, config, checklist
    ):
        workers = next_workers.after_watch_fvcom(
            Message(
                "watch_fvcom",
                "success x2 nowcast",
                {
                    "x2 nowcast": {
                        "host": "arbutus.cloud",
                        "model config": "x2",
                        "run date": "2019-01-18",
                        "completed": True,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_fvcom_boundary",
            args=["arbutus.cloud", "x2", "forecast"],
            host="arbutus.cloud",
        )
        assert expected in workers


class TestAfterMakeWW3WindFile:
    """Unit tests for the after_make_ww3_wind_file function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure forecast2",
            "failure forecast",
            "success forecast2",
            "success forecast",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_ww3_wind_file(
            Message("make_ww3_wind_file", msg_type), config, checklist
        )
        assert workers == []


class TestAfterMakeWW3currentFile:
    """Unit tests for the after_make_ww3_current_file function.
    """

    @pytest.mark.parametrize(
        "msg_type", ["crash", "failure forecast2", "failure forecast"]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_ww3_current_file(
            Message("make_ww3_current_file", msg_type), config, checklist
        )
        assert workers == []

    def test_success_forecast_launch_run_ww3_nowcast(self, config, checklist):
        workers = next_workers.after_make_ww3_current_file(
            Message(
                "make_ww3_current_file",
                "success forecast",
                {
                    "forecast": "current/SoG_current_20190805.nc",
                    "run date": "2019-08-05",
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.run_ww3",
            args=["arbutus.cloud", "nowcast", "--run-date", "2019-08-05"],
            host="arbutus.cloud",
        )
        assert workers[0] == expected

    def test_success_forecast2_launch_run_ww3_forecast2(self, config, checklist):
        workers = next_workers.after_make_ww3_current_file(
            Message(
                "make_ww3_current_file",
                "success forecast2",
                {
                    "forecast2": "current/SoG_current_20190805.nc",
                    "run date": "2019-08-05",
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.run_ww3",
            args=["arbutus.cloud", "forecast2", "--run-date", "2019-08-05"],
            host="arbutus.cloud",
        )
        assert workers[0] == expected


class TestAfterRunWW3:
    """Unit tests for the after_run_ww3 function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        ["crash", "failure forecast2", "failure nowcast", "failure forecast"],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_run_ww3(
            Message("run_ww3", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "msg_type, host",
        [("success forecast2", "arbutus.cloud"), ("success forecast", "arbutus.cloud")],
    )
    def test_success_launch_watch_ww3(self, msg_type, host, config, checklist):
        run_type = msg_type.split()[1]
        workers = next_workers.after_run_ww3(
            Message("run_ww3", msg_type, {run_type: {"host": host}}), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.watch_ww3", args=[host, run_type], host=host
        )
        assert workers[0] == expected


class TestAfterWatchWW3:
    """Unit tests for the after_watch_ww3 function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        ["crash", "failure forecast2", "failure nowcast", "failure forecast"],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_watch_ww3(
            Message("watch_ww3", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "msg",
        [
            Message(
                "watch_ww3",
                "success forecast2",
                {
                    "forecast2": {
                        "host": "arbutus.cloud",
                        "run date": "2017-12-24",
                        "completed": True,
                    }
                },
            ),
            Message(
                "watch_ww3",
                "success nowcast",
                {
                    "nowcast": {
                        "host": "arbutus.cloud",
                        "run date": "2018-07-28",
                        "completed": True,
                    }
                },
            ),
            Message(
                "watch_ww3",
                "success forecast",
                {
                    "forecast": {
                        "host": "arbutus.cloud",
                        "run date": "2017-12-24",
                        "completed": True,
                    }
                },
            ),
        ],
    )
    def test_success_launch_download_wwatch3_results(self, msg, config, checklist):
        workers = next_workers.after_watch_ww3(msg, config, checklist)
        run_type = msg.type.split()[1]
        expected = NextWorker(
            "nowcast.workers.download_wwatch3_results",
            args=[
                msg.payload[run_type]["host"],
                run_type,
                "--run-date",
                msg.payload[run_type]["run date"],
            ],
            host="localhost",
        )
        assert expected in workers

    def test_success_nowcast_launch_run_ww3_forecast(self, config, checklist):
        msg = Message(
            "watch_ww3",
            "success nowcast",
            {
                "nowcast": {
                    "host": "arbutus.cloud",
                    "run date": "2018-07-28",
                    "completed": True,
                }
            },
        )
        workers = next_workers.after_watch_ww3(msg, config, checklist)
        run_type = msg.type.split()[1]
        expected = NextWorker(
            "nowcast.workers.run_ww3",
            args=[
                msg.payload[run_type]["host"],
                "forecast",
                "--run-date",
                msg.payload[run_type]["run date"],
            ],
            host="arbutus.cloud",
        )
        assert expected in workers


class TestAfterWatchNEMO_Hindcast:
    """Unit tests for the after_watch_NEMO_hindcast function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_watch_NEMO_hindcast(
            Message("watch_NEMO_hindcast", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "msg",
        [
            Message(
                "watch_NEMO_hindcast",
                "success",
                {
                    "hindcast": {
                        "host": "cedar",
                        "run date": "2018-03-10",
                        "completed": True,
                    }
                },
            )
        ],
    )
    def test_success_launch_download_results(self, msg, config, checklist):
        workers = next_workers.after_watch_NEMO_hindcast(msg, config, checklist)
        expected = NextWorker(
            "nowcast.workers.download_results",
            args=[
                msg.payload["hindcast"]["host"],
                "hindcast",
                "--run-date",
                msg.payload["hindcast"]["run date"],
            ],
            host="localhost",
        )
        assert expected in workers

    @pytest.mark.parametrize(
        "msg",
        [
            Message(
                "watch_NEMO_hindcast",
                "success",
                {
                    "hindcast": {
                        "host": "cedar",
                        "run date": "2018-03-12",
                        "completed": True,
                    }
                },
            )
        ],
    )
    def test_success_launch_watch_NEMO_hindcast(self, msg, config, checklist):
        workers = next_workers.after_watch_NEMO_hindcast(msg, config, checklist)
        expected = NextWorker(
            "nowcast.workers.watch_NEMO_hindcast",
            args=[msg.payload["hindcast"]["host"]],
            host="localhost",
        )
        assert expected in workers

    @pytest.mark.parametrize(
        "msg",
        [
            Message(
                "watch_NEMO_hindcast",
                "success",
                {
                    "hindcast": {
                        "host": "cedar",
                        "run date": "2018-03-12",
                        "completed": True,
                    }
                },
            )
        ],
    )
    def test_success_launch_run_NEMO_hindcast(self, msg, config, checklist):
        workers = next_workers.after_watch_NEMO_hindcast(msg, config, checklist)
        expected = NextWorker(
            "nowcast.workers.run_NEMO_hindcast",
            args=[msg.payload["hindcast"]["host"]],
            host="localhost",
        )
        assert expected in workers


class TestAfterRunNEMO_Hindcast:
    """Unit tests for the after_run_NEMO_hindcast function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure", "success"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_run_NEMO_hindcast(
            Message("run_NEMO_hindcast", msg_type), config, checklist
        )
        assert workers == []


class TestAfterDownloadResults:
    """Unit tests for the after_download_results function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure nowcast",
            "failure nowcast-green",
            "failure forecast",
            "failure forecast2",
            "failure hindcast",
            "failure nowcast-agrif",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        try:
            run_type = msg_type.split()[1]
        except IndexError:
            run_type = None
        workers = next_workers.after_download_results(
            Message(
                "download_results",
                msg_type,
                payload={run_type: {"run date": "2016-10-22"}},
            ),
            config,
            checklist,
        )
        assert workers == []

    @pytest.mark.parametrize(
        "model, run_type, plot_type, run_date, plot_date",
        [
            ("nemo", "nowcast", "research", "2016-10-29", "2016-10-29"),
            ("nemo", "nowcast", "comparison", "2016-10-28", "2016-10-27"),
            ("nemo", "nowcast-green", "research", "2016-10-29", "2016-10-29"),
            ("nemo", "nowcast-agrif", "research", "2018-09-04", "2018-09-04"),
        ],
    )
    def test_success_nowcast_launch_make_plots_specials(
        self, model, run_type, plot_type, run_date, plot_date, config, checklist
    ):
        workers = next_workers.after_download_results(
            Message(
                "download results",
                f"success {run_type}",
                payload={run_type: {"run date": run_date}},
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_plots",
            args=[model, run_type, plot_type, "--run-date", plot_date],
            host="localhost",
        )
        assert expected in workers

    def test_success_nowcast_green_launch_ping_erddap_nowcast_green(
        self, config, checklist
    ):
        workers = next_workers.after_download_results(
            Message(
                "download_results",
                "success nowcast-green",
                payload={"nowcast-green": {"run date": "2017-06-22"}},
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.ping_erddap", args=["nowcast-green"], host="localhost"
        )
        assert expected in workers

    @pytest.mark.parametrize(
        "run_type, run_date",
        [
            ("nowcast", "2018-09-01"),
            ("forecast", "2018-09-01"),
            ("forecast2", "2018-09-01"),
        ],
    )
    def test_success_launch_make_CHS_currents_file(
        self, run_type, run_date, config, checklist
    ):
        workers = next_workers.after_download_results(
            Message(
                "download_results",
                f"success {run_type}",
                payload={run_type: {"run date": run_date}},
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_CHS_currents_file",
            args=[run_type, "--run-date", run_date],
            host="localhost",
        )
        assert expected in workers

    def test_success_hindcast_launch_split_results(
        self, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            checklist, "NEMO run", {"hindcast": {"run id": "11mar18hindcast"}}
        )
        workers = next_workers.after_download_results(
            Message(
                "download_results",
                f"success hindcast",
                payload={"hindcast": {"run date": "2018-03-11"}},
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.split_results",
            args=["hindcast", "2018-03-11"],
            host="localhost",
        )
        assert expected in workers


class TestAfterMakeCHSCurrentsFile:
    """Unit tests for the after_make_CHS_currents_file function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure nowcast",
            "failure forecast",
            "failure forecast2",
            "success nowcast",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_CHS_currents_file(
            Message("make_CHS_currents_file", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "run_type, run_date", [("forecast", "2018-09-13"), ("forecast2", "2018-09-13")]
    )
    def test_success_forecast_launch_update_forecast_datasets(
        self, run_type, run_date, config, checklist
    ):
        workers = next_workers.after_make_CHS_currents_file(
            Message(
                "make_CHS_currents_file",
                f"success {run_type}",
                payload={run_type: {"run date": run_date}},
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.update_forecast_datasets",
            args=["nemo", run_type, "--run-date", run_date],
            host="localhost",
        )
        assert expected in workers


class TestAfterSplitResults:
    """Unit tests for after_split_results function.
    """

    @pytest.mark.parametrize(
        "msg_type", ["crash", "failure hindcast", "success hindcast"]
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_split_results(
            Message("split_results", msg_type), config, checklist
        )
        assert workers == []


class TestAfterDownloadWWatch3Results:
    """Unit tests for the after_download_wwatch3_results function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        ["crash", "failure forecast2", "failure nowcast", "failure forecast"],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist, monkeypatch):
        monkeypatch.setitem(
            checklist, "WWATCH3 run", {"forecast": {"run date": "2017-12-24"}}
        )
        workers = next_workers.after_download_wwatch3_results(
            Message("download_wwatch3_results", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "run_type, run_date", [("forecast", "2018-04-11"), ("forecast2", "2018-04-11")]
    )
    def test_success_forecast_launch_update_forecast_datasets(
        self, run_type, run_date, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            checklist, "WWATCH3 run", {run_type: {"run date": run_date}}
        )
        workers = next_workers.after_download_wwatch3_results(
            Message("download_wwatch3_results", f"success {run_type}"),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.update_forecast_datasets",
            args=["wwatch3", run_type, "--run-date", run_date],
            host="localhost",
        )
        assert expected in workers

    def test_success_nowcast_no_launch_update_forecast_datasets(
        self, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            checklist, "WWATCH3 run", {"nowcast": {"run date": "2018-07-28"}}
        )
        workers = next_workers.after_download_wwatch3_results(
            Message("download_wwatch3_results", "success nowcast"), config, checklist
        )
        assert workers == []


class TestAfterDownloadFVCOMResults:
    """Unit tests for the after_download_fvcom_results function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        ["crash", "failure x2 nowcast", "failure x2 forecast", "failure r12 nowcast"],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_download_fvcom_results(
            Message("download_fvcom_results", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "model_config, run_type",
        [("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")],
    )
    def test_success_launch_get_vfpa_hadcp(
        self, model_config, run_type, config, checklist
    ):
        workers = next_workers.after_download_fvcom_results(
            Message(
                "download_fvcom_results",
                f"success {model_config} {run_type}",
                {
                    run_type: {
                        "host": "arbutus.cloud",
                        "model config": model_config,
                        "run date": "2018-10-25",
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.get_vfpa_hadcp",
            args=["--data-date", "2018-10-25"],
            host="localhost",
        )
        assert expected in workers

    @pytest.mark.parametrize(
        "model_config, run_type",
        (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
    )
    def test_success_vfpa_hadcp_launch_make_plots_fvcom_research(
        self, model_config, run_type, config, checklist
    ):
        run_date = "2018-10-25"
        workers = next_workers.after_download_fvcom_results(
            Message(
                "download_fvcom_results",
                f"success {model_config} {run_type}",
                {
                    run_type: {
                        "host": "arbutus.cloud",
                        "model config": model_config,
                        "run date": run_date,
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_plots",
            args=[
                "fvcom",
                f"{run_type}-{model_config}",
                "research",
                "--run-date",
                run_date,
            ],
            host="localhost",
        )
        assert expected in workers

    @pytest.mark.parametrize(
        "model_config, run_type", (("x2", "nowcast"), ("r12", "nowcast"))
    )
    def test_success_nowcast_no_launch_update_forecast_datasets(
        self, model_config, run_type, config, checklist
    ):
        workers = next_workers.after_download_fvcom_results(
            Message(
                "download_fvcom_results",
                f"success {model_config} {run_type}",
                {
                    run_type: {
                        "host": "arbutus.cloud",
                        "model config": model_config,
                        "run date": "2018-10-25",
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.update_forecast_datasets",
            args=["fvcom", "nowcast", "--run-date", "2018-10-25"],
            host="localhost",
        )
        assert expected not in workers

    def test_success_forecast_launch_update_forecast_datasets(
        self, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            checklist, "FVCOM run", {"forecast": {"run date": "2018-10-25"}}
        )
        workers = next_workers.after_download_fvcom_results(
            Message(
                "download_fvcom_results",
                "success x2 forecast",
                {
                    "forecast": {
                        "host": "arbutus.cloud",
                        "model config": "x2",
                        "run date": "2018-10-25",
                    }
                },
            ),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.update_forecast_datasets",
            args=["fvcom", "forecast", "--run-date", "2018-10-25"],
            host="localhost",
        )
        assert expected in workers


class TestAfterGetVFPA_HADCP:
    """Unit tests for the after_get_vfpa_hadcp function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_get_vfpa_hadcp(
            Message("after_get_vfpa_hadcp", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize("run_type", ["nowcast", "forecast"])
    def test_success_launch_make_plots(self, run_type, config, checklist, monkeypatch):
        monkeypatch.setitem(
            checklist, "FVCOM run", {run_type: {"run date": "2018-10-25"}}
        )
        workers = next_workers.after_get_vfpa_hadcp(
            Message("after_get_vfpa_hadcp", "success"), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.ping_erddap", args=["VFPA-HADCP"], host="localhost"
        )
        assert expected in workers


class TestAfterUpdateForecastDatasets:
    """Unit tests for the after_update_forecast_datasets function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure fvcom forecast",
            "failure nemo forecast",
            "failure nemo forecast2",
            "failure wwatch3 forecast",
            "failure wwatch3 forecast2",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_update_forecast_datasets(
            Message("update_forecast_datasets", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "run_type, run_date", [("forecast", "2018-01-26"), ("forecast2", "2018-01-26")]
    )
    def test_success_nemo_launch_ping_erddap_nemo_forecast(
        self, run_type, run_date, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(checklist, "NEMO run", {run_type: {"run date": run_date}})
        workers = next_workers.after_update_forecast_datasets(
            Message("update_forecast_datasets", f"success nemo {run_type}"),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.ping_erddap", args=["nemo-forecast"], host="localhost"
        )
        assert expected in workers

    def test_success_fvcom_launch_ping_erddap_fvcom_forecast(
        self, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            checklist, "FVCOM run", {"x2 forecast": {"run date": "2019-04-15"}}
        )
        workers = next_workers.after_update_forecast_datasets(
            Message("update_forecast_datasets", f"success fvcom forecast"),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.ping_erddap", args=["fvcom-forecast"], host="localhost"
        )
        assert expected in workers

    @pytest.mark.parametrize(
        "run_type, run_date", [("forecast", "2018-01-26"), ("forecast2", "2018-01-26")]
    )
    def test_success_nemo_launch_make_plots_forecast_publish(
        self, run_type, run_date, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(checklist, "NEMO run", {run_type: {"run date": run_date}})
        workers = next_workers.after_update_forecast_datasets(
            Message("update_forecast_datasets", f"success nemo {run_type}"),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_plots",
            args=["nemo", run_type, "publish", "--run-date", run_date],
            host="localhost",
        )
        assert expected in workers

    @pytest.mark.parametrize(
        "run_type, run_date", [("forecast", "2018-11-30"), ("forecast2", "2018-11-30")]
    )
    def test_success_nemo_launch_make_surface_current_tiles(
        self, run_type, run_date, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(checklist, "NEMO run", {run_type: {"run date": run_date}})
        workers = next_workers.after_update_forecast_datasets(
            Message("update_forecast_datasets", f"success nemo {run_type}"),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.make_surface_current_tiles",
            args=[run_type, "--run-date", run_date],
            host="localhost",
        )
        assert expected in workers

    @pytest.mark.parametrize(
        "run_type, run_date", [("forecast", "2018-04-12"), ("forecast2", "2018-04-12")]
    )
    def test_success_wwatch3_launch_ping_erddap_wwatch3(
        self, run_type, run_date, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            checklist, "WWATCH3 run", {run_type: {"run date": run_date}}
        )
        workers = next_workers.after_update_forecast_datasets(
            Message("update_forecast_datasets", f"success wwatch3 {run_type}"),
            config,
            checklist,
        )
        expected = NextWorker(
            "nowcast.workers.ping_erddap", args=["wwatch3-forecast"], host="localhost"
        )
        assert expected in workers


class TestAfterPingERDDAP:
    """Unit tests for the after_ping_erddap function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure download_weather",
            "failure SCVIP-CTD",
            "failure SEVIP-CTD",
            "failure USDDL-CTD",
            "failure TWDP-ferry",
            "failure VFPA-HADCP",
            "failure nowcast-green",
            "failure nemo-forecast",
            "failure wwatch3-forecast",
            "success download_weather",
            "success SCVIP-CTD",
            "success SEVIP-CTD",
            "success USDDL-CTD",
            "success TWDP-ferry",
            "success nemo-forecast",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_ping_erddap(
            Message("ping_erddap", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize("run_type", ["forecast", "forecast2"])
    def test_success_wwatch3_launch_make_plots_wwatch3(
        self, run_type, config, checklist, monkeypatch
    ):
        run_date = "2018-05-13"
        monkeypatch.setitem(checklist, "ERDDAP flag files", {"wwatch3 - forecast": []})
        monkeypatch.setitem(
            checklist, "WWATCH3 run", {run_type: {"run date": run_date}}
        )
        workers = next_workers.after_ping_erddap(
            Message("ping_erddap", f"success wwatch3-forecast"), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.make_plots",
            args=["wwatch3", run_type, "publish", "--run-date", run_date],
            host="localhost",
        )
        assert expected in workers

    @pytest.mark.parametrize(
        "model_config, run_type",
        (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
    )
    def test_success_vfpa_hadcp_launch_make_plots_fvcom_publish(
        self, model_config, run_type, config, checklist, monkeypatch
    ):
        run_date = "2018-10-25"
        monkeypatch.setitem(checklist, "ERDDAP flag files", {"VFPA-HADCP": []})
        monkeypatch.setitem(
            checklist,
            "FVCOM run",
            {
                f"{model_config} {run_type}": {
                    "completed": True,
                    "model config": model_config,
                    "run date": run_date,
                }
            },
        )
        workers = next_workers.after_ping_erddap(
            Message("ping_erddap", f"success VFPA-HADCP"), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.make_plots",
            args=[
                "fvcom",
                f"{run_type}-{model_config}",
                "publish",
                "--run-date",
                run_date,
            ],
            host="localhost",
        )
        assert expected in workers

    @pytest.mark.parametrize(
        "model_config, run_type",
        (("x2", "nowcast"), ("x2", "forecast"), ("r12", "nowcast")),
    )
    def test_success_vfpa_hadcp_no_fvcom_run_in_checklist(
        self, model_config, run_type, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(checklist, "ERDDAP flag files", {"VFPA-HADCP": []})
        workers = next_workers.after_ping_erddap(
            Message("ping_erddap", f"success VFPA-HADCP"), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "model_config, run_type", (("x2", "nowcast"), ("x2", "forecast"))
    )
    def test_success_vfpa_hadcp_not_complete_run_no_launch_make_plots_fvcom_publish(
        self, model_config, run_type, config, checklist, monkeypatch
    ):
        run_date = "2018-10-25"
        monkeypatch.setitem(checklist, "ERDDAP flag files", {"VFPA-HADCP": []})
        monkeypatch.setitem(
            checklist,
            "FVCOM run",
            {
                f"{model_config} {run_type}": {
                    "completed": True,
                    "model config": model_config,
                    "run date": run_date,
                }
            },
        )
        monkeypatch.setitem(
            checklist,
            "r12 nowcast",
            {
                "model config": "R12",
                "run date": run_date,
                "run exec cmd": "bash VHFR_FVCOM.sh",
            },
        )
        workers = next_workers.after_ping_erddap(
            Message("ping_erddap", f"success VFPA-HADCP"), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.make_plots",
            args=[
                "fvcom",
                f"{run_type}-{model_config}",
                "publish",
                "--run-date",
                run_date,
            ],
            host="localhost",
        )
        assert expected in workers
        not_expected = NextWorker(
            "nowcast.workers.make_plots",
            args=["fvcom", "nowcast-r12", "publish", "--run-date", run_date],
            host="localhost",
        )
        assert not_expected not in workers


class TestAfterMakePlots:
    """Unit tests for the after_make_plots function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        [
            "crash",
            "failure nemo nowcast research",
            "failure nemo nowcast comparison",
            "failure nemo nowcast publish",
            "failure nemo nowcast-green research",
            "failure nemo nowcast-agrif research",
            "failure nemo forecast publish",
            "failure nemo forecast2 publish",
            "failure fvcom nowcast-x2 publish",
            "failure fvcom forecast-x2 publish",
            "failure fvcom nowcast-r12 publish",
            "failure fvcom nowcast-x2 research",
            "failure fvcom forecast-x2 research",
            "failure fvcom nowcast-r12 research",
            "failure wwatch3 forecast publish",
            "failure wwatch3 forecast2 publish",
            "success nemo nowcast research",
            "success nemo nowcast comparison",
            "success nemo nowcast publish",
            "success nemo nowcast-green research",
            "success nemo nowcast-agrif research",
            "success fvcom nowcast-x2 publish",
            "success fvcom forecast-x2 publish",
            "success fvcom nowcast-r12 publish",
            "success fvcom nowcast-x2 research",
            "success fvcom forecast-x2 research",
            "success fvcom nowcast-r12 research",
            "success wwatch3 forecast publish",
            "success wwatch3 forecast2 publish",
        ],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_plots(
            Message("make_plots", msg_type), config, checklist
        )
        assert workers == []

    @pytest.mark.parametrize(
        "msg_type, run_type",
        [
            ("success nemo forecast publish", "forecast"),
            ("success nemo forecast2 publish", "forecast2"),
        ],
    )
    def test_success_nemo_forecast_launch_make_feeds(
        self, msg_type, run_type, config, checklist, monkeypatch
    ):
        monkeypatch.setitem(
            checklist, "NEMO run", {run_type: {"run date": "2016-11-11"}}
        )
        workers = next_workers.after_make_plots(
            Message("make_plots", msg_type), config, checklist
        )
        expected = NextWorker(
            "nowcast.workers.make_feeds",
            args=[run_type, "--run-date", "2016-11-11"],
            host="localhost",
        )
        assert expected in workers


class TestAfterMakeSurfaceCurrentTiles:
    """Unit tests for the after_make_surface_current_tiles function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure", "success"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_surface_current_tiles(
            Message("make_surface_current_tiles", msg_type), config, checklist
        )
        assert workers == []


class TestAfterMakeFeeds:
    """Unit tests for the after_make_feeds function.
    """

    @pytest.mark.parametrize(
        "msg_type",
        ["crash", "failure forecast", "failure forecast2", "success forecast"],
    )
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_make_feeds(
            Message("make_feeds", msg_type), config, checklist
        )
        assert workers == []

    def test_success_forecast2_publish_launch_clear_checklist(self, config, checklist):
        workers = next_workers.after_make_feeds(
            Message("make_feeds", "success forecast2"), config, checklist
        )
        assert workers[-1] == NextWorker(
            "nemo_nowcast.workers.clear_checklist", args=[], host="localhost"
        )


class TestAfterClearChecklist:
    """Unit tests for the after_clear_checklist function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_clear_checklist(
            Message("clear_checklist", msg_type), config, checklist
        )
        assert workers == []

    def test_success_launch_rotate_logs(self, config, checklist):
        workers = next_workers.after_clear_checklist(
            Message("rotate_logs", "success"), config, checklist
        )
        assert workers[-1] == NextWorker(
            "nemo_nowcast.workers.rotate_logs", args=[], host="localhost"
        )


class TestAfterRotateLogs:
    """Unit tests for the after_rotate_logs function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure", "success"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_rotate_logs(
            Message("rotate_logs", msg_type), config, checklist
        )
        assert workers == []


class TestAfterLaunchRemoteWorker:
    """Unit tests for the after_launch_remote_worker function.
    """

    @pytest.mark.parametrize("msg_type", ["crash", "failure", "success"])
    def test_no_next_worker_msg_types(self, msg_type, config, checklist):
        workers = next_workers.after_launch_remote_worker(
            Message("launch_remote_worker", msg_type), config, checklist
        )
        assert workers == []
