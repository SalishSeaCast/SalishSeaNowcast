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


"""Unit tests for SalishSeaCast run_NEMO_hindcast worker."""
import logging
import textwrap
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import arrow
import nemo_nowcast
import pytest

import nowcast.ssh_sftp
from nowcast.workers import run_NEMO_hindcast


@pytest.fixture
def config(base_config):
    """:py:class:`nemo_nowcast.Config` instance from YAML fragment to use as config for unit tests."""
    config_file = Path(base_config.file)
    with config_file.open("at") as f:
        f.write(
            textwrap.dedent(
                """\
            run:
                hindcast hosts:
                    cedar:
                        ssh key: SalishSeaNEMO-nowcast_id_rsa
                        queue info cmd: /opt/software/slurm/bin/squeue
                        users: allen,dlatorne
                        scratch dir: scratch/
                        run prep dir: runs/
                        salishsea cmd:
                            executable: bin/salishsea
                            run options: --deflate --max-deflate-jobs 48
                            envvars:

                    optimum:
                        ssh key: SalishSeaNEMO-nowcast_id_rsa
                        queue info cmd: /usr/bin/qstat
                        users: sallen,dlatorne
                        scratch dir: scratch/
                        run prep dir: runs/
                        salishsea cmd:
                            executable: bin/salishsea
                            run options:
                            envvars:
                                PATH: $PATH:$HOME/bin
                                FORCING: /shared
                                PROJECT: /home
                                SUSANPROJECT: /home

            """
            )
        )
    config_ = nemo_nowcast.Config()
    config_.load(config_file)
    return config_


@pytest.fixture
def mock_worker(mock_nowcast_worker, monkeypatch):
    monkeypatch.setattr(run_NEMO_hindcast, "NowcastWorker", mock_nowcast_worker)


class TestMain:
    """Unit tests for main() function."""

    def test_instantiate_worker(self, mock_worker):
        worker = run_NEMO_hindcast.main()
        assert worker.name == "run_NEMO_hindcast"
        assert worker.description.startswith(
            "SalishSeaCast worker that prepares the YAML run description file"
        )

    def test_add_host_name_arg(self, mock_worker):
        worker = run_NEMO_hindcast.main()
        assert worker.cli.parser._actions[3].dest == "host_name"
        assert worker.cli.parser._actions[3].help

    def test_add_full_month_option(self, mock_worker):
        worker = run_NEMO_hindcast.main()
        assert worker.cli.parser._actions[4].dest == "full_month"
        assert worker.cli.parser._actions[4].default is False
        assert worker.cli.parser._actions[4].help

    def test_add_prev_run_date_option(self, mock_worker):
        worker = run_NEMO_hindcast.main()
        assert worker.cli.parser._actions[5].dest == "prev_run_date"
        assert worker.cli.parser._actions[5].help

    def test_add_walltime_option(self, mock_worker):
        worker = run_NEMO_hindcast.main()
        assert worker.cli.parser._actions[6].dest == "walltime"
        assert worker.cli.parser._actions[6].default is None
        assert worker.cli.parser._actions[6].help


class TestConfig:
    """Unit tests for production YAML config file elements related to worker."""

    def test_message_registry(self, prod_config):
        assert "run_NEMO_hindcast" in prod_config["message registry"]["workers"]
        msg_registry = prod_config["message registry"]["workers"]["run_NEMO_hindcast"]
        assert msg_registry["checklist key"] == "NEMO run"

    @pytest.mark.parametrize("msg", ("success", "failure", "crash"))
    def test_message_types(self, msg, prod_config):
        msg_registry = prod_config["message registry"]["workers"]["run_NEMO_hindcast"]
        assert msg in msg_registry

    def test_optimum_hindcast_section(self, prod_config):
        optimum_hindcast = prod_config["run"]["hindcast hosts"]["optimum-hindcast"]
        assert optimum_hindcast["ssh key"] == "SalishSeaNEMO-nowcast_id_rsa"
        assert optimum_hindcast["queue info cmd"] == "/usr/bin/qstat"
        assert optimum_hindcast["users"] == "sallen,dlatorne"
        assert optimum_hindcast["scratch dir"] == "/scratch/sallen/dlatorne/oxygen/"
        assert (
            optimum_hindcast["run prep dir"]
            == "/home/sallen/dlatorne/SalishSeaCast/hindcast-sys/runs"
        )
        assert (
            optimum_hindcast["salishsea cmd"]["executable"]
            == "/home/sallen/dlatorne/.conda/envs/salishseacast/bin/salishsea"
        )
        assert optimum_hindcast["salishsea cmd"]["run options"] is None
        assert optimum_hindcast["salishsea cmd"]["envvars"] == {
            "PATH": "$PATH:$HOME/bin",
            "FORCING": "/data/sallen/shared",
            "PROJECT": "/home/sallen/dlatorne",
            "SUSANPROJECT": "/home/sallen/sallen",
        }


@pytest.mark.parametrize("host_name", ("cedar", "optimum"))
class TestSuccess:
    """Unit test for success() function."""

    def test_success(self, host_name, caplog):
        parsed_args = SimpleNamespace(host_name=host_name)
        caplog.set_level(logging.DEBUG)

        msg_type = run_NEMO_hindcast.success(parsed_args)

        assert caplog.records[0].levelname == "INFO"
        expected = f"NEMO hindcast run queued on {host_name}"
        assert caplog.records[0].message == expected
        assert msg_type == "success"


@pytest.mark.parametrize("host_name", ("cedar", "optimum"))
class TestFailure:
    """Unit test for failure() function."""

    def test_failure(self, host_name, caplog):
        parsed_args = SimpleNamespace(host_name=host_name)
        caplog.set_level(logging.DEBUG)

        msg_type = run_NEMO_hindcast.failure(parsed_args)

        assert caplog.records[0].levelname == "CRITICAL"
        expected = f"NEMO hindcast run failed to queue on {host_name}"
        assert caplog.records[0].message == expected
        assert msg_type == "failure"


@pytest.mark.parametrize("host_name", ("cedar", "optimum"))
@patch(
    "nowcast.workers.watch_NEMO_agrif.ssh_sftp.sftp",
    return_value=(Mock(name="ssh_client"), Mock(name="sftp_client")),
)
@patch(
    "nowcast.workers.run_NEMO_hindcast._get_prev_run_queue_info",
    autospec=True,
    return_value=(arrow.get("2018-01-01"), 12_345_678),
)
@patch("nowcast.workers.run_NEMO_hindcast._get_prev_run_namelist_info")
@patch("nowcast.workers.run_NEMO_hindcast._edit_namelist_time", autospec=True)
@patch("nowcast.workers.run_NEMO_hindcast._edit_run_desc", autospec=True)
@patch("nowcast.workers.run_NEMO_hindcast._launch_run", autospec=True)
class TestRunNEMO_Hindcast:
    """Unit tests for run_NEMO_hindcast() function."""

    def test_checklist_full_month_run_date_in_future(
        self,
        m_launch_run,
        m_edit_run_desc,
        m_edit_namelist_time,
        m_get_prev_run_namelist_info,
        m_get_prev_run_queue_info,
        m_sftp,
        host_name,
        config,
        caplog,
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name, full_month=True, prev_run_date=arrow.get("2019-01-11")
        )
        caplog.set_level(logging.DEBUG)

        with patch("nowcast.workers.run_NEMO_hindcast.arrow.now") as m_now:
            m_now.return_value = arrow.get("2019-01-30")
            checklist = run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, config)

            assert not m_launch_run.called
            expected = {"hindcast": {"host": host_name, "run id": "None"}}
            assert checklist == expected

    def test_checklist_not_full_month_run_date_in_future(
        self,
        m_launch_run,
        m_edit_run_desc,
        m_edit_namelist_time,
        m_get_prev_run_namelist_info,
        m_get_prev_run_queue_info,
        m_sftp,
        host_name,
        config,
        caplog,
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            full_month=False,
            prev_run_date=arrow.get("2019-08-06"),
            walltime=None,
        )
        caplog.set_level(logging.DEBUG)

        with patch("nowcast.workers.run_NEMO_hindcast.arrow.now") as m_now:
            m_now.return_value = arrow.get("2019-08-15")
            checklist = run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, config)

            assert m_launch_run.called
            expected = {"hindcast": {"host": host_name, "run id": "11aug19hindcast"}}
            assert checklist == expected

    @pytest.mark.parametrize(
        "full_month, prev_run_date, expected_run_id",
        [
            (True, arrow.get("2018-01-01"), "01feb18hindcast"),
            (False, arrow.get("2019-07-01"), "06jul19hindcast"),
            (False, arrow.get("2019-07-06"), "11jul19hindcast"),
            (False, arrow.get("2019-07-11"), "16jul19hindcast"),
            (False, arrow.get("2019-07-16"), "21jul19hindcast"),
            (False, arrow.get("2019-07-26"), "01aug19hindcast"),  # 31 day mo
            (False, arrow.get("2019-06-26"), "01jul19hindcast"),  # 30 day mo
            (False, arrow.get("2019-02-26"), "01mar19hindcast"),  # feb
            (False, arrow.get("2016-02-26"), "01mar16hindcast"),  # leap year
            (False, arrow.get("2017-12-26"), "01jan18hindcast"),  # year end
        ],
    )
    def test_checklist_with_prev_run_date(
        self,
        m_launch_run,
        m_edit_run_desc,
        m_edit_namelist_time,
        m_get_prev_run_namelist_info,
        m_get_prev_run_queue_info,
        m_sftp,
        host_name,
        full_month,
        prev_run_date,
        expected_run_id,
        config,
        caplog,
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            full_month=full_month,
            prev_run_date=prev_run_date,
            walltime=None,
        )
        caplog.set_level(logging.DEBUG)

        checklist = run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, config)

        expected = {"hindcast": {"host": host_name, "run id": expected_run_id}}
        assert checklist == expected

    @pytest.mark.parametrize(
        "full_month, prev_run_date, expected_run_id",
        [
            (True, arrow.get("2018-01-01"), "01feb18hindcast"),
            (False, arrow.get("2019-07-01"), "06jul19hindcast"),
            (False, arrow.get("2019-07-06"), "11jul19hindcast"),
            (False, arrow.get("2019-07-11"), "16jul19hindcast"),
            (False, arrow.get("2019-07-16"), "21jul19hindcast"),
            (False, arrow.get("2019-07-26"), "01aug19hindcast"),  # 31 day mo
            (False, arrow.get("2019-06-26"), "01jul19hindcast"),  # 30 day mo
            (False, arrow.get("2019-02-26"), "01mar19hindcast"),  # feb
            (False, arrow.get("2016-02-26"), "01mar16hindcast"),  # leap year
            (False, arrow.get("2017-12-26"), "01jan18hindcast"),  # year end
        ],
    )
    def test_checklist_without_prev_run_date(
        self,
        m_launch_run,
        m_edit_run_desc,
        m_edit_namelist_time,
        m_get_prev_run_namelist_info,
        m_get_prev_run_queue_info,
        m_sftp,
        host_name,
        full_month,
        prev_run_date,
        expected_run_id,
        config,
        caplog,
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            full_month=full_month,
            prev_run_date=None,
            walltime=None,
        )
        m_get_prev_run_queue_info.return_value = (prev_run_date, 12_345_678)
        caplog.set_level(logging.DEBUG)

        checklist = run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, config)

        expected = {"hindcast": {"host": host_name, "run id": expected_run_id}}
        assert checklist == expected

    @pytest.mark.parametrize(
        "full_month, prev_run_date, expected_run_date, expected_run_days",
        [
            (True, arrow.get("2018-01-01"), arrow.get("2018-02-01"), 28),  # 28d run
            (True, arrow.get("2016-01-01"), arrow.get("2016-02-01"), 29),  # 29d run
            (True, arrow.get("2018-02-01"), arrow.get("2018-03-01"), 31),  # 31d run
            (True, arrow.get("2018-03-01"), arrow.get("2018-04-01"), 30),  # 30d run
            (False, arrow.get("2019-07-01"), arrow.get("2019-07-06"), 5),  # 5d run
            (False, arrow.get("2019-07-21"), arrow.get("2019-07-26"), 6),  # 6d run
            (False, arrow.get("2019-02-21"), arrow.get("2019-02-26"), 3),  # 3d run
            (False, arrow.get("2016-02-21"), arrow.get("2016-02-26"), 4),  # 4d run
            (False, arrow.get("2019-07-26"), arrow.get("2019-08-01"), 5),  # 31 day mo
            (False, arrow.get("2019-06-26"), arrow.get("2019-07-01"), 5),  # 30 day mo
            (False, arrow.get("2019-02-26"), arrow.get("2019-03-01"), 5),  # feb
            (False, arrow.get("2016-02-26"), arrow.get("2016-03-01"), 5),  # leap year
            (False, arrow.get("2017-12-26"), arrow.get("2018-01-01"), 5),  # year end
        ],
    )
    def test_edit_namelist_time_run_date(
        self,
        m_launch_run,
        m_edit_run_desc,
        m_edit_namelist_time,
        m_get_prev_run_namelist_info,
        m_get_prev_run_queue_info,
        m_sftp,
        host_name,
        full_month,
        prev_run_date,
        expected_run_date,
        expected_run_days,
        config,
        caplog,
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            full_month=full_month,
            prev_run_date=prev_run_date,
            walltime=None,
        )
        caplog.set_level(logging.DEBUG)

        run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, config)

        m_edit_namelist_time.assert_called_once_with(
            m_sftp()[1],
            host_name,
            m_get_prev_run_namelist_info(),
            expected_run_date,
            expected_run_days,
            config,
        )

    @pytest.mark.parametrize(
        "full_month, prev_run_date, walltime, expected_run_date, expected_walltime",
        [
            (
                True,
                arrow.get("2018-07-01"),
                None,
                arrow.get("2018-08-01"),
                108_000,
            ),  # default
            (
                True,
                arrow.get("2018-07-01"),
                "15:00:00",
                arrow.get("2018-08-01"),
                "15:00:00",
            ),
            (
                False,
                arrow.get("2018-07-01"),
                None,
                arrow.get("2018-07-06"),
                "10:00:00",
            ),  # default
            (
                False,
                arrow.get("2018-07-01"),
                "09:00:00",
                arrow.get("2018-07-06"),
                "09:00:00",
            ),
            (False, arrow.get("2019-07-01"), 86400, arrow.get("2019-07-06"), 86400),
        ],
    )
    def test_edit_run_desc_walltime(
        self,
        m_launch_run,
        m_edit_run_desc,
        m_edit_namelist_time,
        m_get_prev_run_namelist_info,
        m_get_prev_run_queue_info,
        m_sftp,
        host_name,
        full_month,
        prev_run_date,
        walltime,
        expected_run_date,
        expected_walltime,
        config,
        caplog,
    ):
        parsed_args = SimpleNamespace(
            host_name=host_name,
            full_month=full_month,
            prev_run_date=prev_run_date,
            walltime=walltime,
        )
        caplog.set_level(logging.DEBUG)

        run_NEMO_hindcast.run_NEMO_hindcast(parsed_args, config)

        m_edit_run_desc.assert_called_once_with(
            m_sftp()[1],
            host_name,
            prev_run_date,
            m_get_prev_run_namelist_info(),
            expected_run_date,
            expected_walltime,
            config,
        )


@patch("nowcast.workers.run_NEMO_hindcast._get_qstat_queue_info", autospec=True)
@patch("nowcast.workers.run_NEMO_hindcast._get_squeue_queue_info", autospec=True)
class TestGetPrevRunQueueInfo:
    """Unit tests for _get_prev_run_queue_info() function."""

    def test_found_prev_hindcast_job_squeue(
        self, m_squeue_info, m_qstat_info, config, caplog
    ):
        m_squeue_info.return_value = ["12345678 01may18hindcast"]
        m_ssh_client = Mock(name="ssh_client")
        caplog.set_level(logging.DEBUG)

        prev_run_date, job_id = run_NEMO_hindcast._get_prev_run_queue_info(
            m_ssh_client, "cedar", config
        )

        assert prev_run_date == arrow.get("2018-05-01")
        assert job_id == "12345678"
        assert caplog.records[0].levelname == "INFO"
        expected = "using 01may18hindcast job 12345678 on cedar as previous run"
        assert caplog.messages[0] == expected

    def test_found_prev_hindcast_job_qstat(
        self, m_squeue_info, m_qstat_info, config, caplog
    ):
        m_qstat_info.return_value = ["12345678.admin 01may18hindcast"]
        m_ssh_client = Mock(name="ssh_client")
        caplog.set_level(logging.DEBUG)

        prev_run_date, job_id = run_NEMO_hindcast._get_prev_run_queue_info(
            m_ssh_client, "optimum", config
        )

        assert prev_run_date == arrow.get("2018-05-01")
        assert job_id == "12345678.admin"
        assert caplog.records[0].levelname == "INFO"
        expected = "using 01may18hindcast job 12345678.admin on optimum as previous run"
        assert caplog.messages[0] == expected

    @pytest.mark.parametrize("host_name", ("cedar", "optimum"))
    def test_no_prev_hindcast_job_found(
        self, m_squeue_info, m_qstat_info, host_name, config, caplog
    ):
        m_qstat_info.return_value = ["12345678.admin 07may18nowcast-agrif"]
        m_squeue_info.return_value = ["12345678 07may18nowcast-agrif"]
        m_ssh_client = Mock(name="ssh_client")
        caplog.set_level(logging.DEBUG)

        with pytest.raises(nemo_nowcast.WorkerError):
            run_NEMO_hindcast._get_prev_run_queue_info(m_ssh_client, host_name, config)

            assert caplog.records[0].levelname == "ERROR"
            expected = f"no hindcast jobs found on {host_name} queue"
            assert caplog.messages[0] == expected


@patch("nowcast.workers.run_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True)
class TestGetQstatQueueInfo:
    """Unit tests for _get_qstat_queue_info() function."""

    def test_no_job_found_on_queue(self, m_ssh_exec_cmd, config, caplog):
        m_ssh_exec_cmd.return_value = "\n".join(f"header{i}" for i in range(5))
        m_ssh_client = Mock(name="ssh_client")
        caplog.set_level(logging.DEBUG)

        with pytest.raises(nemo_nowcast.WorkerError):
            run_NEMO_hindcast._get_qstat_queue_info(
                m_ssh_client, "optimum", "/usr/bin/qstat", "sallen,dlatorne"
            )

            assert caplog.records[0].levelname == "ERROR"
            expected = "no jobs found on optimum queue"
            assert caplog.messages[0] == expected

    def test_queue_info_lines(self, m_ssh_exec_cmd, config, caplog):
        qstat_return = "\n".join(f"header{i}" for i in range(5))
        qstat_return = (
            f"{qstat_return}\n"
            f"12345678.admin foo bar 15may19hindcast\n"
            f"12345679.admin foo bar 25may19hindcast\n"
        )
        m_ssh_exec_cmd.return_value = qstat_return
        m_ssh_client = Mock(name="ssh_client")
        caplog.set_level(logging.DEBUG)

        queue_info_lines = run_NEMO_hindcast._get_qstat_queue_info(
            m_ssh_client, "optimum", "/usr/bin/qstat", "sallen,dlatorne"
        )

        assert queue_info_lines == [
            "12345679 25may19hindcast",
            "12345678 15may19hindcast",
        ]


@patch("nowcast.workers.run_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True)
class TestGetSqueueQueueInfo:
    """Unit tests for _get_squeue_queue_info() function."""

    def test_no_job_found_on_queue(self, m_ssh_exec_cmd, config, caplog):
        m_ssh_exec_cmd.return_value = "header\n"
        m_ssh_client = Mock(name="ssh_client")
        caplog.set_level(logging.DEBUG)

        with pytest.raises(nemo_nowcast.WorkerError):
            run_NEMO_hindcast._get_squeue_queue_info(
                m_ssh_client,
                "optimum",
                "/opt/software/slurm/bin/squeue",
                "allen,dlatorne",
            )

            assert caplog.records[0].levelname == "ERROR"
            expected = "no jobs found on optimum queue"
            assert caplog.messages[0] == expected

    def test_queue_info_lines(self, m_ssh_exec_cmd, config, caplog):
        m_ssh_exec_cmd.return_value = (
            "header\n12345678 15may19hindcast\n12345679 25may19hindcast\n"
        )
        m_ssh_client = Mock(name="ssh_client")
        caplog.set_level(logging.DEBUG)

        queue_info_lines = run_NEMO_hindcast._get_squeue_queue_info(
            m_ssh_client, "optimum", "/opt/software/slurm/bin/squeue", "allen,dlatorne"
        )

        assert queue_info_lines == [
            "12345679 25may19hindcast",
            "12345678 15may19hindcast",
        ]


@pytest.mark.parametrize("host_name", ("cedar", "optimum"))
@patch("nowcast.workers.run_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True)
@patch("nowcast.workers.run_NEMO_hindcast.f90nml.read", autospec=True)
class TestGetPrevRunNamelistInfo:
    """Unit test for _get_prev_run_namelist_info() function."""

    def test_get_prev_run_namelist_info(
        self, m_f90nml_read, m_ssh_exec_cmd, host_name, config, caplog
    ):
        m_ssh_client = Mock(name="ssh_client")
        m_sftp_client = Mock(name="sftp_client")
        m_ssh_exec_cmd.return_value = "scratch/01may18hindcast_xxx/namelist_cfg\n"
        p_named_tmp_file = patch(
            "nowcast.workers.run_NEMO_hindcast.tempfile.NamedTemporaryFile",
            autospec=True,
        )
        m_f90nml_read.return_value = {
            "namrun": {"nn_itend": 2_717_280},
            "namdom": {"rn_rdt": 40.0},
        }
        caplog.set_level(logging.DEBUG)

        with p_named_tmp_file as m_named_tmp_file:
            prev_namelist_info = run_NEMO_hindcast._get_prev_run_namelist_info(
                m_ssh_client, m_sftp_client, host_name, arrow.get("2018-05-01"), config
            )

        m_ssh_exec_cmd.assert_called_once_with(
            m_ssh_client,
            "ls -d scratch/01may18*/namelist_cfg",
            host_name,
            run_NEMO_hindcast.logger,
        )
        m_sftp_client.get.assert_called_once_with(
            "scratch/01may18hindcast_xxx/namelist_cfg",
            m_named_tmp_file().__enter__().name,
        )
        assert caplog.records[0].levelname == "INFO"
        expected = f"found previous run namelist: {host_name}:scratch/01may18hindcast_xxx/namelist_cfg"
        assert caplog.messages[0] == expected
        assert prev_namelist_info == SimpleNamespace(itend=2_717_280, rdt=40.0)


@pytest.mark.parametrize("host_name", ("cedar", "optimum"))
@patch("nowcast.workers.run_NEMO_hindcast.f90nml.patch", autospec=True)
class TestEditNamelistTime:
    """Unit tests for _edit_namelist_time() function."""

    def test_download_namelist_time(self, m_patch, host_name, config, caplog):
        m_sftp_client = Mock(name="sftp_client")
        prev_namelist_info = SimpleNamespace(itend=2_717_280, rdt=40.0)
        caplog.set_level(logging.DEBUG)

        run_NEMO_hindcast._edit_namelist_time(
            m_sftp_client,
            host_name,
            prev_namelist_info,
            arrow.get("2018-02-01"),
            28,
            config,
        )

        m_sftp_client.get.assert_called_once_with(
            "runs/namelist.time", "/tmp/hindcast.namelist.time"
        )

    @pytest.mark.parametrize(
        "run_date, run_days, expected_itend, expected_stocklist",
        [
            (
                arrow.get("2018-03-01"),
                31,
                2_784_240,
                [2_738_880, 2_760_480, 2_784_240, 0, 0, 0, 0, 0, 0, 0],
            ),  # 31 day month
            (
                arrow.get("2018-02-01"),
                28,
                2_777_760,
                [2_738_880, 2_760_480, 2_777_760, 0, 0, 0, 0, 0, 0, 0],
            ),  # February
            (
                arrow.get("2016-02-01"),
                29,
                2_779_920,
                [2_738_880, 2_760_480, 2_779_920, 0, 0, 0, 0, 0, 0, 0],
            ),  # leap year
            (
                arrow.get("2018-04-01"),
                30,
                2_782_080,
                [2_738_880, 2_760_480, 2_782_080, 0, 0, 0, 0, 0, 0, 0],
            ),  # 30 day month
            (
                arrow.get("2018-04-01"),
                10,
                2_738_880,
                [2_738_880, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ),  # 10d run
            (
                arrow.get("2018-04-11"),
                10,
                2_738_880,
                [2_738_880, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ),  # 10d run
            (
                arrow.get("2018-02-21"),
                8,
                2_734_560,
                [2_734_560, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ),  # 8d run
            (
                arrow.get("2016-02-21"),
                9,
                2_736_720,
                [2_736_720, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ),  # 9d run
            (
                arrow.get("2018-03-21"),
                11,
                2_741_040,
                [2_741_040, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            ),  # 11d run
        ],
    )
    def test_patch_namelist_time(
        self,
        m_patch,
        host_name,
        run_date,
        run_days,
        expected_itend,
        expected_stocklist,
        config,
        caplog,
    ):
        sftp_client = Mock(name="sftp_client")
        prev_namelist_info = SimpleNamespace(itend=2_717_280, rdt=40.0)
        caplog.set_level(logging.DEBUG)

        run_NEMO_hindcast._edit_namelist_time(
            sftp_client, host_name, prev_namelist_info, run_date, run_days, config
        )

        m_patch.assert_called_once_with(
            "/tmp/hindcast.namelist.time",
            {
                "namrun": {
                    "nn_it000": 2_717_280 + 1,
                    "nn_itend": expected_itend,
                    "nn_date0": int(run_date.format("YYYYMMDD")),
                    "nn_stocklist": expected_stocklist,
                }
            },
            "/tmp/patched_hindcast.namelist.time",
        )

    def test_upload_namelist_time(self, m_patch, host_name, config, caplog):
        m_sftp_client = Mock(name="sftp_client")
        prev_namelist_info = SimpleNamespace(itend=2_717_280, rdt=40.0)
        caplog.set_level(logging.DEBUG)

        run_NEMO_hindcast._edit_namelist_time(
            m_sftp_client,
            host_name,
            prev_namelist_info,
            arrow.get("2018-02-01"),
            28,
            config,
        )

        m_sftp_client.put.assert_called_once_with(
            "/tmp/patched_hindcast.namelist.time", "runs/namelist.time"
        )


@pytest.mark.parametrize("host_name", ("cedar", "optimum"))
@patch(
    "nowcast.workers.run_NEMO_agrif.yaml.safe_load",
    return_value={
        "run_id": "",
        "restart": {"restart.nc": "", "restart_trc.nc": ""},
        "walltime": "06:00:00",
    },
    autospec=True,
)
class TestEditRunDesc:
    """Unit tests for _edit_run_desc() function."""

    def test_download_run_desc_template(
        self, m_safe_load, host_name, tmpdir, config, caplog
    ):
        m_sftp_client = Mock(name="sftp_client")
        prev_namelist_info = SimpleNamespace(itend=2_717_280, rdt=40.0)
        yaml_tmpl = tmpdir.ensure("hindcast_tmpl.yaml")
        caplog.set_level(logging.DEBUG)

        run_NEMO_hindcast._edit_run_desc(
            m_sftp_client,
            host_name,
            arrow.get("2018-01-01"),
            prev_namelist_info,
            arrow.get("2018-02-01"),
            "03:00:00",
            config,
            yaml_tmpl=Path(str(yaml_tmpl)),
        )

        m_sftp_client.get.assert_called_once_with(
            "runs/hindcast_template.yaml", yaml_tmpl
        )

    @pytest.mark.parametrize("walltime", ["03:00:00", "08:30:00", "12:00:00"])
    @patch("nowcast.workers.run_NEMO_hindcast.yaml.safe_dump", autospec=True)
    def test_edit_run_desc(
        self, m_safe_dump, m_safe_load, walltime, host_name, tmpdir, config, caplog
    ):
        m_sftp_client = Mock(name="sftp_client")
        prev_namelist_info = SimpleNamespace(itend=2_717_280, rdt=40.0)
        yaml_tmpl = tmpdir.ensure("hindcast_tmpl.yaml")
        caplog.set_level(logging.DEBUG)

        with patch("nowcast.workers.run_NEMO_hindcast.Path.open") as m_open:
            run_NEMO_hindcast._edit_run_desc(
                m_sftp_client,
                host_name,
                arrow.get("2018-05-01"),
                prev_namelist_info,
                arrow.get("2018-06-01"),
                walltime,
                config,
                yaml_tmpl=Path(str(yaml_tmpl)),
            )

        m_safe_dump.assert_called_once_with(
            {
                "run_id": "01jun18hindcast",
                "restart": {
                    "restart.nc": "scratch/01may18/SalishSea_02717280_restart.nc",
                    "restart_trc.nc": "scratch/01may18/SalishSea_02717280_restart_trc.nc",
                },
                "walltime": walltime,
            },
            m_open().__enter__(),
            default_flow_style=False,
        )

    def test_upload_run_desc(self, m_safe_load, host_name, tmpdir, config, caplog):
        m_sftp_client = Mock(name="sftp_client")
        prev_namelist_info = SimpleNamespace(itend=2_717_280, rdt=40.0)
        yaml_tmpl = tmpdir.ensure("hindcast_tmpl.yaml")
        caplog.set_level(logging.DEBUG)

        run_NEMO_hindcast._edit_run_desc(
            m_sftp_client,
            host_name,
            arrow.get("2018-01-01"),
            prev_namelist_info,
            arrow.get("2018-02-01"),
            "03:00:00",
            config,
            yaml_tmpl=Path(str(yaml_tmpl)),
        )

        m_sftp_client.put.assert_called_once_with(
            yaml_tmpl, "runs/01feb18hindcast.yaml"
        )


@pytest.mark.parametrize(
    "host_name, run_opts, envvars",
    (
        ("cedar", "--deflate --max-deflate-jobs 48", ""),
        (
            "optimum",
            "",
            "export PATH=$PATH:$HOME/bin; export FORCING=/shared; export PROJECT=/home; "
            "export SUSANPROJECT=/home; ",
        ),
    ),
)
@patch("nowcast.workers.run_NEMO_hindcast.ssh_sftp.ssh_exec_command", autospec=True)
class TestLaunchRun:
    """Unit tests for _launch_run() function."""

    def test_launch_run(
        self, m_ssh_exec_cmd, host_name, run_opts, envvars, config, caplog
    ):
        m_ssh_client = Mock(name="ssh_client")
        caplog.set_level(logging.DEBUG)

        run_NEMO_hindcast._launch_run(
            m_ssh_client, host_name, "01may18hindcast", prev_job_id=None, config=config
        )

        m_ssh_exec_cmd.assert_called_once_with(
            m_ssh_client,
            f"{envvars}bin/salishsea run runs/01may18hindcast.yaml scratch/01may18 "
            f"{run_opts}",
            host_name,
            run_NEMO_hindcast.logger,
        )

    def test_launch_run_with_prev_job_id(
        self, m_ssh_exec_cmd, host_name, run_opts, envvars, config, caplog
    ):
        m_ssh_client = Mock(name="ssh_client")
        caplog.set_level(logging.DEBUG)

        run_NEMO_hindcast._launch_run(
            m_ssh_client,
            host_name,
            "01may18hindcast",
            prev_job_id=12_345_678,
            config=config,
        )

        m_ssh_exec_cmd.assert_called_once_with(
            m_ssh_client,
            f"{envvars}bin/salishsea run runs/01may18hindcast.yaml scratch/01may18 "
            f"{run_opts} "
            f"--waitjob 12345678 --nocheck-initial-conditions",
            host_name,
            run_NEMO_hindcast.logger,
        )

    def test_ssh_error(
        self, m_ssh_exec_cmd, host_name, run_opts, envvars, config, caplog
    ):
        m_ssh_client = Mock(name="ssh_client")
        m_ssh_exec_cmd.side_effect = nowcast.ssh_sftp.SSHCommandError(
            "cmd", "stdout", "stderr"
        )
        caplog.set_level(logging.DEBUG)

        with pytest.raises(nemo_nowcast.WorkerError):
            run_NEMO_hindcast._launch_run(
                m_ssh_client,
                host_name,
                "01may18hindcast",
                prev_job_id=None,
                config=config,
            )

            assert caplog.records[0].levelname == "ERROR"
            assert caplog.messages[0] == "stderr"
