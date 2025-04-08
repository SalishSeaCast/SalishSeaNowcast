#  Copyright 2013 – present by the SalishSeaCast Project contributors
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

# SPDX-License-Identifier: Apache-2.0


"""Unit tests for SalishSeaCast update_forecast_datasets worker."""
import logging
import shlex
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

import arrow
import nemo_nowcast
import pytest

from nowcast.workers import update_forecast_datasets


@pytest.fixture()
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
                results archive:
                  nowcast: results/nowcast-blue/
                  forecast: results/forecast/
                  forecast2: results/forecast2/

                rolling forecasts:
                  days from past: 5
                  temporary results archives: /tmp/
                  nemo:
                    dest dir: rolling-forecasts/nemo/
                  wwatch3:
                    dest dir: rolling-forecasts/wwatch3/
                    most recent forecast dir: opp/wwatch3/most_recent_forecast

                wave forecasts:
                  results archive:
                    nowcast: opp/wwatch3/nowcast/
                    forecast: opp/wwatch3/forecast/
                    forecast2: opp/wwatch3/forecast2/
                """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(update_forecast_datasets, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = update_forecast_datasets.main()
        assert worker.name == "update_forecast_datasets"
        assert worker.description.startswith(
            "SalishSeaCast worker that builds a new directory of symlinks to model results files"
        )

    def test_add_model_arg(self, mock_worker):
        worker = update_forecast_datasets.main()
        assert worker.cli.parser._actions[3].dest == "model"
        assert worker.cli.parser._actions[3].choices == {"nemo", "wwatch3"}
        assert worker.cli.parser._actions[3].help

    def test_add_run_type_arg(self, mock_worker):
        worker = update_forecast_datasets.main()
        assert worker.cli.parser._actions[4].dest == "run_type"
        assert worker.cli.parser._actions[4].choices == {"forecast", "forecast2"}
        assert worker.cli.parser._actions[4].help

    def test_add_data_date_arg(self, mock_worker, monkeypatch):
        def mock_now():
            return arrow.get("2022-10-04 14:50:43")

        monkeypatch.setattr(update_forecast_datasets.arrow, "now", mock_now)

        worker = update_forecast_datasets.main()
        assert worker.cli.parser._actions[5].dest == "run_date"
        expected = nemo_nowcast.cli.CommandLineInterface.arrow_date
        assert worker.cli.parser._actions[5].type == expected
        assert worker.cli.parser._actions[5].default == arrow.get("2022-10-04")
        assert worker.cli.parser._actions[5].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "update_forecast_datasets" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"][
            "update_forecast_datasets"
        ]
        assert msg_registry["checklist key"] == "update forecast datasets"

    @pytest.mark.parametrize(
        "msg",
        (
            "success nemo forecast",
            "failure nemo forecast",
            "success nemo forecast2",
            "failure nemo forecast2",
            "success wwatch3 forecast",
            "failure wwatch3 forecast",
            "success wwatch3 forecast2",
            "failure wwatch3 forecast2",
            "crash",
        ),
    )
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"][
            "update_forecast_datasets"
        ]
        assert msg in msg_registry

    def test_results_archives(self, prod_config):
        nemo_run_types = ("nowcast", "forecast", "forecast2")
        for run_type in nemo_run_types:
            assert run_type in prod_config["results archive"]
        wwatch3_run_types = ("nowcast", "forecast", "forecast2")
        for run_type in wwatch3_run_types:
            assert run_type in prod_config["wave forecasts"]["results archive"]

    def test_rolling_foreacsts(self, prod_config):
        assert prod_config["rolling forecasts"]["days from past"] == 5
        assert prod_config["rolling forecasts"]["temporary results archives"] == "/tmp/"
        nemo = prod_config["rolling forecasts"]["nemo"]
        assert nemo["dest dir"] == "/results/SalishSea/rolling-forecasts/nemo/"
        wwatch3 = prod_config["rolling forecasts"]["wwatch3"]
        assert wwatch3["dest dir"] == "/results/SalishSea/rolling-forecasts/wwatch3/"
        assert (
            wwatch3["most recent forecast dir"] == "/opp/wwatch3/most_recent_forecast/"
        )


@pytest.mark.parametrize(
    "model, run_type",
    [
        ("nemo", "forecast"),
        ("nemo", "forecast2"),
        ("wwatch3", "forecast"),
        ("wwatch3", "forecast2"),
    ],
)
class TestSuccess:
    """Unit tests for success() function."""

    def test_success(self, model, run_type, caplog):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2017-11-10")
        )
        caplog.set_level(logging.DEBUG)

        msg_type = update_forecast_datasets.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"{model} 2017-11-10 {run_type} rolling forecast datasets updated"
        assert caplog.messages[0] == expected
        assert msg_type == f"success {model} {run_type}"


@pytest.mark.parametrize(
    "model, run_type",
    [
        ("nemo", "forecast"),
        ("nemo", "forecast2"),
        ("wwatch3", "forecast"),
        ("wwatch3", "forecast2"),
    ],
)
class TestFailure:
    """Unit tests for failure() function."""

    def test_failure(self, model, run_type, caplog):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2017-11-10")
        )
        caplog.set_level(logging.DEBUG)

        msg_type = update_forecast_datasets.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = (
            f"{model} 2017-11-10 {run_type} rolling forecast datasets update failed"
        )
        assert caplog.messages[0] == expected
        assert msg_type == f"failure {model} {run_type}"


class TestUpdateForecastDatasets:
    """Unit tests for update_forecast_datasets() function."""

    @staticmethod
    @pytest.fixture
    def mock_symlink_most_recent_forecast(monkeypatch):
        def mock_symlink_most_recent_forecast(
            run_date, most_recent_fcst_dir, model, run_type, config
        ):
            pass

        monkeypatch.setattr(
            update_forecast_datasets,
            "_symlink_most_recent_forecast",
            mock_symlink_most_recent_forecast,
        )

    @staticmethod
    @pytest.fixture
    def mock_update_rolling_forecast(monkeypatch):
        def mock_update_rolling_forecast(
            run_date, forecast_dir, model, run_type, config
        ):
            pass

        monkeypatch.setattr(
            update_forecast_datasets,
            "_update_rolling_forecast",
            mock_update_rolling_forecast,
        )

    @pytest.mark.parametrize(
        "model, run_type",
        [("wwatch3", "forecast"), ("wwatch3", "forecast2")],
    )
    def test_most_recent_forecast_checklist(
        self,
        mock_update_rolling_forecast,
        mock_symlink_most_recent_forecast,
        model,
        run_type,
        config,
        caplog,
        tmpdir,
        monkeypatch,
    ):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2018-10-24")
        )
        tmp_forecast_results_archive = tmpdir.ensure_dir("tmp")
        dest_dir = Path(config["rolling forecasts"][model]["dest dir"])
        most_recent_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["most recent forecast dir"]
        )
        monkeypatch.setitem(
            config["rolling forecasts"],
            "temporary results archives",
            str(tmp_forecast_results_archive),
        )
        monkeypatch.setitem(
            config["rolling forecasts"][model],
            "most recent forecast dir",
            str(most_recent_fcst_dir),
        )

        checklist = update_forecast_datasets.update_forecast_datasets(
            parsed_args, config
        )

        expected = {model: {run_type: [str(most_recent_fcst_dir), str(dest_dir)]}}
        assert checklist == expected

    @pytest.mark.parametrize(
        "run_type",
        ("forecast", "forecast2"),
    )
    def test_nemo_rolling_forecast_checklist(
        self,
        mock_update_rolling_forecast,
        mock_symlink_most_recent_forecast,
        run_type,
        config,
        caplog,
        tmpdir,
        monkeypatch,
    ):
        parsed_args = SimpleNamespace(
            model="nemo", run_type=run_type, run_date=arrow.get("2017-11-10")
        )
        tmp_forecast_results_archive = tmpdir.ensure_dir("tmp")
        rolling_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"]["nemo"]["dest dir"]
        )
        monkeypatch.setitem(
            config["rolling forecasts"],
            "temporary results archives",
            str(tmp_forecast_results_archive),
        )
        monkeypatch.setitem(
            config["rolling forecasts"]["nemo"], "dest dir", str(rolling_fcst_dir)
        )

        checklist = update_forecast_datasets.update_forecast_datasets(
            parsed_args, config
        )

        expected = {"nemo": {run_type: [str(rolling_fcst_dir)]}}
        assert checklist == expected

    @pytest.mark.parametrize(
        "run_type",
        ("forecast", "forecast2"),
    )
    def test_wwatch3_rolling_forecast_checklist(
        self,
        mock_update_rolling_forecast,
        mock_symlink_most_recent_forecast,
        run_type,
        config,
        caplog,
        tmpdir,
        monkeypatch,
    ):
        parsed_args = SimpleNamespace(
            model="wwatch3", run_type=run_type, run_date=arrow.get("2017-11-10")
        )
        tmp_forecast_results_archive = tmpdir.ensure_dir("tmp")
        rolling_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"]["wwatch3"]["dest dir"]
        )
        most_recent_fcst_dir = Path(
            config["rolling forecasts"]["wwatch3"]["most recent forecast dir"]
        )
        monkeypatch.setitem(
            config["rolling forecasts"],
            "temporary results archives",
            str(tmp_forecast_results_archive),
        )
        monkeypatch.setitem(
            config["rolling forecasts"]["wwatch3"], "dest dir", str(rolling_fcst_dir)
        )

        checklist = update_forecast_datasets.update_forecast_datasets(
            parsed_args, config
        )

        expected = {
            "wwatch3": {run_type: [str(most_recent_fcst_dir), str(rolling_fcst_dir)]}
        }
        assert checklist == expected

    @pytest.mark.parametrize(
        "model, run_type", [("wwatch3", "forecast"), ("wwatch3", "forecast2")]
    )
    def test_most_recent_and_rolling_forecast_checklist(
        self,
        mock_update_rolling_forecast,
        mock_symlink_most_recent_forecast,
        model,
        run_type,
        config,
        caplog,
        tmpdir,
        monkeypatch,
    ):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2017-11-10")
        )
        tmp_forecast_results_archive = tmpdir.ensure_dir("tmp")
        most_recent_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["most recent forecast dir"]
        )
        rolling_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["dest dir"]
        )
        monkeypatch.setitem(
            config["rolling forecasts"],
            "temporary results archives",
            str(tmp_forecast_results_archive),
        )
        monkeypatch.setitem(
            config["rolling forecasts"][model], "dest dir", str(rolling_fcst_dir)
        )
        monkeypatch.setitem(
            config["rolling forecasts"][model],
            "most recent forecast dir",
            str(most_recent_fcst_dir),
        )

        checklist = update_forecast_datasets.update_forecast_datasets(
            parsed_args, config
        )

        expected = {
            model: {run_type: [str(most_recent_fcst_dir), str(rolling_fcst_dir)]}
        }
        assert checklist == expected


class TestSymlinkMostRecentForecast:
    """Unit tests for _symlink_most_recent_forecast() function."""

    @pytest.mark.parametrize(
        "model, run_type",
        [("wwatch3", "forecast"), ("wwatch3", "forecast2")],
    )
    def test_unlink_prev_forecast_files(self, model, run_type, config, caplog, tmpdir):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2018-10-25")
        )
        most_recent_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["most recent forecast dir"]
        )
        prev_fcst_files = ("foo.nc", "bar.nc")
        for f in prev_fcst_files:
            most_recent_fcst_dir.ensure(f)
        update_forecast_datasets._symlink_most_recent_forecast(
            parsed_args.run_date,
            Path(str(most_recent_fcst_dir)),
            model,
            run_type,
            config,
        )
        for f in prev_fcst_files:
            assert not most_recent_fcst_dir.join(f).check(file=True)

    @pytest.mark.parametrize(
        "model, run_type",
        [("wwatch3", "forecast"), ("wwatch3", "forecast2")],
    )
    def test_symlink_new_forecast_files(
        self, model, run_type, config, caplog, tmpdir, monkeypatch
    ):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2018-10-25")
        )
        most_recent_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["most recent forecast dir"]
        )
        runs = {"wwatch3": "wave forecasts"}
        results_archive = tmpdir.ensure_dir(
            config[runs[model]]["results archive"][run_type]
        )
        new_fcst_files = ["foo.nc", "foo_restart.nc", "bar.nc"]
        for f in new_fcst_files:
            results_archive.ensure_dir("25oct18").ensure(f)
        monkeypatch.setitem(
            config[runs[model]]["results archive"],
            run_type,
            str(results_archive),
        )

        update_forecast_datasets._symlink_most_recent_forecast(
            parsed_args.run_date,
            Path(str(most_recent_fcst_dir)),
            model,
            run_type,
            config,
        )

        new_fcst_files.remove("foo_restart.nc")
        for f in new_fcst_files:
            assert most_recent_fcst_dir.join(f).check(link=True)
        assert not most_recent_fcst_dir.join("foo_restart.nc").check(link=True)


class TestUpdateRollingForecast:
    """Unit tests for _u[pdate_rolling_forecast() function."""

    @pytest.mark.parametrize(
        "model, run_type",
        [
            ("nemo", "forecast"),
            ("nemo", "forecast2"),
            ("wwatch3", "forecast"),
            ("wwatch3", "forecast2"),
        ],
    )
    def test_update_rolling_forecast(
        self, model, run_type, config, caplog, tmpdir, monkeypatch
    ):
        parsed_args = SimpleNamespace(
            model=model, run_type=run_type, run_date=arrow.get("2018-10-25")
        )
        tmp_forecast_results_archive = tmpdir.ensure_dir("tmp")
        rolling_fcst_dir = tmpdir.ensure_dir(
            config["rolling forecasts"][model]["dest dir"]
        )
        monkeypatch.setitem(
            config["rolling forecasts"],
            "temporary results archives",
            str(tmp_forecast_results_archive),
        )

        update_forecast_datasets._update_rolling_forecast(
            parsed_args.run_date,
            Path(str(rolling_fcst_dir)),
            model,
            run_type,
            config,
        )

        assert rolling_fcst_dir.check(dir=True)


@pytest.mark.parametrize(
    "model, run_type", [("nemo", "forecast"), ("nemo", "forecast2")]
)
class TestCreateNewForecastDir:
    """Unit tests for _create_new_forecast_dir() function."""

    def test_new_forecast_dir(self, model, run_type, caplog, tmpdir):
        forecast_dir = tmpdir.ensure_dir(f"rolling-forecasts/{model}")
        new_forecast_dir = update_forecast_datasets._create_new_forecast_dir(
            Path(forecast_dir), model, run_type
        )
        assert new_forecast_dir == Path(f"{forecast_dir}_new")


@pytest.fixture
def mock_extract_1st_forecast_day(monkeypatch):
    def mock_extract_1st_forecast_day(
        tmp_forecast_results_archive, run_date, model, config
    ):
        pass

    monkeypatch.setattr(
        update_forecast_datasets,
        "_extract_1st_forecast_day",
        mock_extract_1st_forecast_day,
    )


@patch("nowcast.workers.update_forecast_datasets._symlink_results", autospec=True)
class TestAddPastDaysResults:
    """Unit test for _add_past_days_results() function."""

    @pytest.mark.parametrize(
        "model, run_type, run_date, days_from_past, first_date",
        [
            ("nemo", "forecast", arrow.get("2017-11-11"), 5, arrow.get("2017-11-06")),
            ("nemo", "forecast2", arrow.get("2018-01-24"), 5, arrow.get("2018-01-20")),
        ],
    )
    def test_symlink_nemo_nowcast_days(
        self,
        m_symlink_results,
        mock_extract_1st_forecast_day,
        model,
        run_type,
        run_date,
        days_from_past,
        first_date,
        config,
        tmpdir,
    ):
        new_forecast_dir = Path(
            str(tmpdir.ensure_dir(f"rolling-forecasts/{model}_new"))
        )
        update_forecast_datasets._add_past_days_results(
            run_date, days_from_past, new_forecast_dir, model, run_type, config
        )
        expected = [
            call(
                Path("results/nowcast-blue/"),
                day,
                new_forecast_dir,
                day,
                model,
                run_type,
            )
            for day in arrow.Arrow.range("day", first_date, run_date)
        ]
        assert m_symlink_results.call_args_list == expected

    @pytest.mark.parametrize(
        "model, run_type, run_date, days_from_past, first_date, last_date",
        [
            (
                "wwatch3",
                "forecast",
                arrow.get("2020-04-15"),
                5,
                arrow.get("2020-04-10"),
                arrow.get("2020-04-15"),
            ),
            (
                "wwatch3",
                "forecast2",
                arrow.get("2020-04-15"),
                5,
                arrow.get("2020-04-11"),
                arrow.get("2020-04-14"),
            ),
        ],
    )
    def test_symlink_wwatch3_forecast_days(
        self,
        m_symlink_results,
        mock_extract_1st_forecast_day,
        model,
        run_type,
        run_date,
        days_from_past,
        first_date,
        last_date,
        config,
        tmpdir,
    ):
        new_forecast_dir = Path(
            str(tmpdir.ensure_dir(f"rolling-forecasts/{model}_new"))
        )
        update_forecast_datasets._add_past_days_results(
            run_date, days_from_past, new_forecast_dir, model, run_type, config
        )
        expected = [
            call(
                Path("opp/wwatch3/nowcast"), day, new_forecast_dir, day, model, run_type
            )
            for day in arrow.Arrow.range("day", first_date, last_date)
        ]
        assert m_symlink_results.call_args_list == expected


@patch("nowcast.workers.update_forecast_datasets._symlink_results")
class TestAddForecastResults:
    """Unit tests for _add_forecast_results() function."""

    @pytest.mark.parametrize(
        "run_date, model, run_type, results_archive, forecast_date",
        [
            (
                arrow.get("2017-11-11"),
                "nemo",
                "forecast",
                Path(f"results/forecast/"),
                arrow.get("2017-11-12"),
            ),
            (
                arrow.get("2018-04-12"),
                "wwatch3",
                "forecast",
                Path(f"opp/wwatch3/forecast/"),
                arrow.get("2018-04-13"),
            ),
        ],
    )
    def test_symlink_forecast_run(
        self,
        m_symlink_results,
        mock_extract_1st_forecast_day,
        run_date,
        model,
        run_type,
        results_archive,
        forecast_date,
        config,
        tmpdir,
    ):
        new_forecast_dir = Path(str(tmpdir.ensure_dir(f"rolling-forecasts/nemo_new")))
        update_forecast_datasets._add_forecast_results(
            run_date,
            new_forecast_dir,
            Path(f"/tmp/{model}_forecast"),
            model,
            run_type,
            config,
        )
        m_symlink_results.assert_called_once_with(
            results_archive, run_date, new_forecast_dir, forecast_date, model, run_type
        )

    def test_wwatch3_symlink_forecast2_run(
        self, m_symlink_results, mock_extract_1st_forecast_day, config, tmpdir
    ):
        run_date = arrow.get("2018-01-24")
        model = "wwatch3"
        run_type = "forecast2"
        new_forecast_dir = Path(
            str(tmpdir.ensure_dir(f"rolling-forecasts/{model}_new"))
        )
        update_forecast_datasets._add_forecast_results(
            run_date,
            new_forecast_dir,
            Path(f"/tmp/{model}_forecast"),
            model,
            run_type,
            config,
        )
        expected = [
            call(
                Path(f"/tmp/{model}_forecast"),
                run_date,
                new_forecast_dir,
                run_date,
                model,
                run_type,
            ),
            call(
                Path(f"opp/wwatch3/{run_type}"),
                run_date,
                new_forecast_dir,
                run_date.shift(days=+1),
                model,
                run_type,
            ),
        ]
        m_symlink_results.assert_has_calls(expected)

    @patch(
        "nowcast.workers.update_forecast_datasets._extract_1st_forecast_day",
        autospec=True,
    )
    def test_nemo_forecast2_extract_1st_forecast_day(
        self, m_ex_1st_fcst_day, m_symlink_results, config, tmpdir
    ):
        new_forecast_dir = Path(str(tmpdir.ensure_dir(f"rolling-forecasts/nemo_new")))
        run_date = arrow.get("2018-01-24")
        model = "nemo"
        run_type = "forecast2"
        update_forecast_datasets._add_forecast_results(
            run_date,
            new_forecast_dir,
            Path(f"/tmp/{model}_forecast"),
            "nemo",
            run_type,
            config,
        )
        m_ex_1st_fcst_day.assert_called_once_with(
            Path("/tmp/nemo_forecast"), run_date, model, config
        )

    def test_nemo_symlink_forecast2_run(
        self, m_symlink_results, mock_extract_1st_forecast_day, config, tmpdir
    ):
        new_forecast_dir = Path(str(tmpdir.ensure_dir(f"rolling-forecasts/nemo_new")))
        run_date = arrow.get("2018-01-24")
        model = "nemo"
        run_type = "forecast2"
        update_forecast_datasets._add_forecast_results(
            run_date,
            new_forecast_dir,
            Path(f"/tmp/{model}_forecast"),
            model,
            run_type,
            config,
        )
        assert m_symlink_results.call_args_list == [
            call(
                Path(f"/tmp/nemo_forecast"),
                run_date.shift(days=+1),
                new_forecast_dir,
                run_date.shift(days=+1),
                model,
                run_type,
            ),
            call(
                Path(f"results/{run_type}/"),
                run_date,
                new_forecast_dir,
                run_date.shift(days=+2),
                model,
                run_type,
            ),
        ]


class TestExtract1stForecastDay:
    """Unit tests for _extract_1st_forecast_day() function."""

    def test_create_tmp_forecast_results_archive(self, config, caplog, tmpdir):
        tmp_forecast_results_archive = tmpdir.ensure_dir("tmp_nemo_forecast")
        run_date = arrow.get("2018-01-24")
        model = "nemo"
        update_forecast_datasets._extract_1st_forecast_day(
            Path(str(tmp_forecast_results_archive)), run_date, model, config
        )
        assert Path(str(tmp_forecast_results_archive), "25jan18").exists()

    @patch("nowcast.workers.update_forecast_datasets.subprocess.run", autospec=True)
    def test_nemo_ncks_subprocess(self, m_run, config, caplog, tmpdir, monkeypatch):
        def mock_glob(path, pattern):
            return [
                # A 10min file that we want to operate on
                Path("results/forecast/24jan18/CampbellRiver.nc"),
                # A 1hr file that we want to operate on
                Path(
                    "results/forecast/24jan18/"
                    "SalishSea_1h_20180124_20180125_grid_T.nc"
                ),
                # Files that we don't want to operate on
                Path("results/forecast/24jan18/SalishSea_02702160_restart.nc"),
                Path(
                    "results/forecast/24jan18/"
                    "SalishSea_1d_20180124_20180125_grid_T.nc"
                ),
            ]

        monkeypatch.setattr(update_forecast_datasets.Path, "glob", mock_glob)

        model = "nemo"
        tmp_forecast_results_archive = tmpdir.ensure_dir(f"tmp_{model}_forecast")
        run_date = arrow.get("2018-01-24")
        update_forecast_datasets._extract_1st_forecast_day(
            Path(str(tmp_forecast_results_archive)), run_date, model, config
        )
        assert m_run.call_args_list == [
            call(
                shlex.split(
                    f"/usr/bin/ncks -d time_counter,0,143 "
                    f"results/forecast/24jan18/CampbellRiver.nc "
                    f"{tmp_forecast_results_archive}/25jan18/CampbellRiver.nc"
                )
            ),
            call(
                shlex.split(
                    f"/usr/bin/ncks -d time_counter,0,23 "
                    f"results/forecast/24jan18/"
                    f"SalishSea_1h_20180124_20180125_grid_T.nc "
                    f"{tmp_forecast_results_archive}/25jan18/"
                    f"SalishSea_1h_20180124_20180125_grid_T.nc"
                )
            ),
        ]

    @patch("nowcast.workers.update_forecast_datasets.subprocess.run", autospec=True)
    def test_issue112(self, m_run, config, caplog, tmpdir, monkeypatch):
        """Reproduce issue #112 re: Present day missing from ERDDAP depth-averaged currents dataset."""

        def mock_glob(path, pattern):
            return [
                # A 1hr file that we want to operate on
                Path("results/forecast/04oct22/CHS_currents.nc"),
            ]

        monkeypatch.setattr(update_forecast_datasets.Path, "glob", mock_glob)

        model = "nemo"
        tmp_forecast_results_archive = tmpdir.ensure_dir(f"tmp_{model}_forecast")
        run_date = arrow.get("2022-10-04")
        update_forecast_datasets._extract_1st_forecast_day(
            Path(str(tmp_forecast_results_archive)), run_date, model, config
        )
        assert m_run.call_args_list == [
            call(
                shlex.split(
                    f"/usr/bin/ncks -d time_counter,0,23 "
                    f"results/forecast/04oct22/CHS_currents.nc "
                    f"{tmp_forecast_results_archive}/05oct22/CHS_currents.nc"
                )
            ),
        ]

    @patch("nowcast.workers.update_forecast_datasets.subprocess.run", autospec=True)
    def test_exclude_VENUS_node_files(self, m_run, config, caplog, tmpdir, monkeypatch):
        def mock_glob(path, pattern):
            return [
                # A 1hr file that we want to operate on
                Path("results/forecast/04oct22/CHS_currents.nc"),
                # ONC VENUS node files that we want to exclude
                Path("results/forecast/04oct22/VENUS_central_gridded.nc"),
                Path("results/forecast/04oct22/VENUS_delta_gridded.nc"),
                Path("results/forecast/04oct22/VENUS_east_gridded.nc"),
            ]

        monkeypatch.setattr(update_forecast_datasets.Path, "glob", mock_glob)

        model = "nemo"
        tmp_forecast_results_archive = tmpdir.ensure_dir(f"tmp_{model}_forecast")
        run_date = arrow.get("2022-10-04")
        update_forecast_datasets._extract_1st_forecast_day(
            Path(str(tmp_forecast_results_archive)), run_date, model, config
        )
        assert m_run.call_args_list == [
            call(
                shlex.split(
                    f"/usr/bin/ncks -d time_counter,0,23 "
                    f"results/forecast/04oct22/CHS_currents.nc "
                    f"{tmp_forecast_results_archive}/05oct22/CHS_currents.nc"
                )
            ),
        ]

    @patch("nowcast.workers.update_forecast_datasets.subprocess.run", autospec=True)
    def test_wwatch3_ncks_subprocess(self, m_run, config, caplog, tmpdir, monkeypatch):
        def mock_glob(path, pattern):
            return [
                Path(
                    "opp/wwatch3/forecast/11apr18/"
                    "SoG_ww3_fields_20180410_20180412.nc"
                ),
                Path(
                    "opp/wwatch3/forecast/11apr18/"
                    "SoG_ww3_points_20180410_20180412.nc"
                ),
            ]

        monkeypatch.setattr(update_forecast_datasets.Path, "glob", mock_glob)

        model = "wwatch3"
        tmp_forecast_results_archive = tmpdir.ensure_dir(f"tmp_{model}_forecast")
        run_date = arrow.get("2018-04-11")
        update_forecast_datasets._extract_1st_forecast_day(
            Path(str(tmp_forecast_results_archive)), run_date, model, config
        )
        assert m_run.call_args_list == [
            call(
                shlex.split(
                    f"/usr/bin/ncks -d time,0,47 "
                    f"opp/wwatch3/forecast/11apr18/"
                    f"SoG_ww3_fields_20180410_20180412.nc "
                    f"{tmp_forecast_results_archive}/11apr18/"
                    f"SoG_ww3_fields_20180410_20180412.nc"
                )
            ),
            call(
                shlex.split(
                    f"/usr/bin/ncks -d time,0,143 "
                    f"opp/wwatch3/forecast/11apr18/"
                    f"SoG_ww3_points_20180410_20180412.nc "
                    f"{tmp_forecast_results_archive}/11apr18/"
                    f"SoG_ww3_points_20180410_20180412.nc"
                )
            ),
        ]


@pytest.mark.parametrize(
    "model, run_type", [("nemo", "forecast"), ("nemo", "forecast2")]
)
class TestSymlinkResults:
    """Unit tests for _symlink_results() function."""

    def test_create_dest_dir(self, model, run_type, caplog, tmpdir):
        forecast_day = arrow.get("2017-11-11")
        forecast_dir = tmpdir.ensure_dir(f"rolling-forecasts/{model}_new")
        update_forecast_datasets._symlink_results(
            Path(f"results/{run_type}/"),
            arrow.get("2017-11-10"),
            Path(str(forecast_dir)),
            forecast_day,
            model,
            run_type,
        )
        assert forecast_dir.join("11nov17").check(dir=True)

    def test_symlink(self, model, run_type, caplog, tmpdir):
        results_day = arrow.get("2017-11-10")
        results_archive = tmpdir.ensure_dir(f"results/{run_type}/")
        results_archive.ensure("10nov17/PointAtkinson.nc")
        forecast_day = arrow.get("2017-11-11")
        forecast_dir = tmpdir.ensure_dir(f"rolling-forecasts/{model}_new")
        update_forecast_datasets._symlink_results(
            Path(str(results_archive)),
            results_day,
            Path(str(forecast_dir)),
            forecast_day,
            model,
            run_type,
        )
        assert forecast_dir.join("11nov17", "PointAtkinson.nc").check(link=True)

    @pytest.mark.parametrize(
        "excluded_file",
        (
            "VENUS_central_gridded.nc",
            "VENUS_delta_gridded.nc",
            "VENUS_east_gridded.nc",
            "SalishSea_1d_20221006_20221007_grid_U.nc",
            "SalishSea_09279360_restart.nc",
        ),
    )
    def test_symlink_exclusions(self, excluded_file, model, run_type, caplog, tmpdir):
        results_day = arrow.get("2022-10-04")
        results_archive = tmpdir.ensure_dir(f"results/{run_type}/")
        results_archive.ensure(f"04oct22/{excluded_file}")
        forecast_day = arrow.get("2022-10-05")
        forecast_dir = tmpdir.ensure_dir(f"rolling-forecasts/{model}_new")
        update_forecast_datasets._symlink_results(
            Path(str(results_archive)),
            results_day,
            Path(str(forecast_dir)),
            forecast_day,
            model,
            run_type,
        )
        assert not forecast_dir.join("05oct22", excluded_file).check(link=True)
