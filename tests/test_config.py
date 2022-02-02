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
"""Unit tests for SalishSeaCast production config elements that are not likely to be
tested in worker unit test modules.
"""
import pytest


class TestConfig:
    """Unit tests for production YAML config file elements that are not worker-related."""

    def test_checklist_file(self, prod_config, tmpdir):
        # Config.load() transforms NOWCAST.ENV part of envvars
        assert (
            prod_config["checklist file"]
            == f"{tmpdir}/nowcast_logs/nowcast_checklist.yaml"
        )

    def test_python(self, prod_config, tmpdir):
        # Config.load() transforms NOWCAST.ENV part of envvars
        assert prod_config["python"] == f"{tmpdir}/nowcast-env/bin/python3"


class TestLoggingPublisher:
    """Unit tests for production YAML config file elements related to logging publishers
    (e.g. workers).
    """

    def test_logging_config(self, prod_config):
        publisher_logging = prod_config["logging"]["publisher"]
        assert publisher_logging["version"] == 1
        assert not publisher_logging["disable_existing_loggers"]

    def test_formatters(self, prod_config):
        formatters = prod_config["logging"]["publisher"]["formatters"]
        assert list(formatters.keys()) == ["simple"]
        assert (
            formatters["simple"]["format"]
            == "%(asctime)s %(levelname)s [%(name)s] %(message)s"
        )

    def test_handlers(self, prod_config):
        handlers = prod_config["logging"]["publisher"]["handlers"]
        assert list(handlers.keys()) == [
            "console",
            "zmq_pub",
            "wgrib2_text",
            "hindcast_info",
            "hindcast_debug",
            "checklist",
        ]

    def test_console_handler(self, prod_config):
        console_handler = prod_config["logging"]["publisher"]["handlers"]["console"]
        assert console_handler["class"] == "logging.StreamHandler"
        assert console_handler["level"] == 100
        assert console_handler["formatter"] == "simple"
        assert console_handler["stream"] == "ext://sys.stdout"

    def test_zmq_pub_handler(self, prod_config):
        zmq_pub_handler = prod_config["logging"]["publisher"]["handlers"]["zmq_pub"]
        assert zmq_pub_handler["class"] == "zmq.log.handlers.PUBHandler"
        assert zmq_pub_handler["level"] == "DEBUG"
        assert zmq_pub_handler["formatter"] == "simple"

    def test_wgrib2_text_handler(self, prod_config, tmpdir):
        wgrib2_text_handler = prod_config["logging"]["publisher"]["handlers"][
            "wgrib2_text"
        ]
        assert wgrib2_text_handler["class"] == "logging.FileHandler"
        assert wgrib2_text_handler["level"] == "DEBUG"
        assert wgrib2_text_handler["formatter"] == "simple"
        # Config.load() transforms NOWCAST.ENV part of envvars
        assert wgrib2_text_handler["filename"] == f"{tmpdir}/nowcast_logs/wgrib2.log"
        assert wgrib2_text_handler["mode"] == "w"

    def test_hindcast_info_handler(self, prod_config, tmpdir):
        hindcast_info_handler = prod_config["logging"]["publisher"]["handlers"][
            "hindcast_info"
        ]
        assert hindcast_info_handler["class"] == "logging.handlers.RotatingFileHandler"
        assert hindcast_info_handler["level"] == "INFO"
        assert hindcast_info_handler["formatter"] == "simple"
        # Config.load() transforms NOWCAST.ENV part of envvars
        assert (
            hindcast_info_handler["filename"] == f"{tmpdir}/nowcast_logs/hindcast.log"
        )
        assert hindcast_info_handler["backupCount"] == 7

    def test_hindcast_debug_handler(self, prod_config, tmpdir):
        hindcast_debug_handler = prod_config["logging"]["publisher"]["handlers"][
            "hindcast_debug"
        ]
        assert hindcast_debug_handler["class"] == "logging.handlers.RotatingFileHandler"
        assert hindcast_debug_handler["level"] == "DEBUG"
        assert hindcast_debug_handler["formatter"] == "simple"
        # Config.load() transforms NOWCAST.ENV part of envvars
        assert (
            hindcast_debug_handler["filename"]
            == f"{tmpdir}/nowcast_logs/hindcast.debug.log"
        )
        assert hindcast_debug_handler["backupCount"] == 7

    def test_checklist_handler(self, prod_config, tmpdir):
        checklist_handler = prod_config["logging"]["publisher"]["handlers"]["checklist"]
        assert checklist_handler["class"] == "logging.handlers.RotatingFileHandler"
        assert checklist_handler["level"] == "INFO"
        assert checklist_handler["formatter"] == "simple"
        # Config.load() transforms NOWCAST.ENV part of envvars
        assert checklist_handler["filename"] == f"{tmpdir}/nowcast_logs/checklist.log"
        assert checklist_handler["backupCount"] == 7

    def test_loggers(self, prod_config, tmpdir):
        loggers = prod_config["logging"]["publisher"]["loggers"]
        assert list(loggers.keys()) == [
            "wgrib2",
            "run_NEMO_hindcast",
            "watch_NEMO_hindcast",
            "checklist",
            "matplotlib",
            "PIL",
            "paramiko",
            "watchdog",
        ]

    def test_wgrib2_logger(self, prod_config):
        logger = prod_config["logging"]["publisher"]["loggers"]["wgrib2"]
        assert logger["qualname"] == "wgrib2"
        assert logger["level"] == "DEBUG"
        assert not logger["propagate"]
        assert logger["handlers"] == ["wgrib2_text"]

    def test_run_NEMO_hindcast_logger(self, prod_config):
        logger = prod_config["logging"]["publisher"]["loggers"]["run_NEMO_hindcast"]
        assert logger["qualname"] == "run_NEMO_hindcast"
        assert logger["level"] == "DEBUG"
        assert not logger["propagate"]
        assert logger["handlers"] == ["hindcast_info", "hindcast_debug"]

    def test_watch_NEMO_hindcast_logger(self, prod_config):
        logger = prod_config["logging"]["publisher"]["loggers"]["watch_NEMO_hindcast"]
        assert logger["qualname"] == "watch_NEMO_hindcast"
        assert logger["level"] == "DEBUG"
        assert not logger["propagate"]
        assert logger["handlers"] == ["hindcast_info", "hindcast_debug"]

    def test_checklist_logger(self, prod_config):
        logger = prod_config["logging"]["publisher"]["loggers"]["checklist"]
        assert logger["qualname"] == "checklist"
        assert logger["level"] == "INFO"
        assert not logger["propagate"]
        assert logger["handlers"] == ["checklist"]

    @pytest.mark.parametrize(
        "package",
        ("matplotlib", "PIL", "paramiko", "watchdog"),
    )
    def test_warning_loggers(self, package, prod_config, tmpdir):
        logger = prod_config["logging"]["publisher"]["loggers"][package]
        assert logger["qualname"] == package
        assert logger["level"] == "WARNING"
        assert logger["formatter"] == "simple"

    def test_root_logger(self, prod_config):
        logger = prod_config["logging"]["publisher"]["root"]
        assert logger["level"] == "DEBUG"
        assert not logger["propagate"]
        assert logger["handlers"] == ["console", "zmq_pub"]


class TestSlackNotifications:
    """Unit tests for production YAML config file elements related to slack notifications."""

    def test_daily_progress_channel_envvar(self, prod_config):
        slack_notifications = prod_config["slack notifications"]
        assert list(slack_notifications.keys()) == [
            "SLACK_SSC_DAILY_PROGRESS",
            "SLACK_SSC_HINDCAST_PROGRESS",
            "website log url",
            "website checklist url",
        ]

    def test_daily_progress_channel_workers(self, prod_config):
        slack_notifications = prod_config["slack notifications"]
        expected = [
            "collect_weather",
            "download_weather",
            "download_live_ocean",
            "watch_NEMO",
            "watch_NEMO_agrif",
            "watch_fvcom",
            "watch_ww3",
        ]
        assert slack_notifications["SLACK_SSC_DAILY_PROGRESS"] == expected

    def test_hindcast_progress_channel_workers(self, prod_config):
        slack_notifications = prod_config["slack notifications"]
        expected = ["watch_NEMO_hindcast"]
        assert slack_notifications["SLACK_SSC_HINDCAST_PROGRESS"] == expected

    def test_website_log_url(self, prod_config):
        slack_notifications = prod_config["slack notifications"]
        assert (
            slack_notifications["website log url"]
            == "https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast.log"
        )

    def test_website_checklist_url(self, prod_config):
        slack_notifications = prod_config["slack notifications"]
        assert (
            slack_notifications["website checklist url"]
            == "https://salishsea.eos.ubc.ca/nemo/nowcast/logs/nowcast_checklist.yaml"
        )


class Test0mqMessageSystem:
    """Unit tests for production YAML config file elements related to 0mq message system."""

    def test_host(self, prod_config):
        zmq = prod_config["zmq"]
        assert zmq["host"] == "skookum.eos.ubc.ca"

    def test_msg_broker_manager_port(self, prod_config):
        ports = prod_config["zmq"]["ports"]
        assert ports["manager"] == 5554

    def test_msg_broker_worker_port(self, prod_config):
        ports = prod_config["zmq"]["ports"]
        assert ports["workers"] == 5555

    def test_log_aggregator_ports(self, prod_config):
        ports = prod_config["zmq"]["ports"]
        assert ports["logging"] == {
            "message_broker": 5560,
            "manager": 5561,
            "workers": [
                5562,
                5563,
                5564,
                5565,
                5566,
                5567,
                5568,
                5569,
                5570,
                5571,
                5572,
                5573,
                5574,
                5575,
                5576,
                5577,
                5578,
                5579,
                5590,
                5591,
                5592,
                5593,
                5594,
            ],
            "run_NEMO": ["salish.eos.ubc.ca:5556", "206.12.90.239:5556"],
            "watch_NEMO": ["salish.eos.ubc.ca:5557", "206.12.90.239:5557"],
            "make_ww3_wind_file": "206.12.90.239:5570",
            "make_ww3_current_file": "206.12.90.239:5571",
            "run_ww3": "206.12.90.239:5572",
            "watch_ww3": "206.12.90.239:5573",
            "make_fvcom_boundary": ["206.12.90.239:5580", "206.12.90.239:5581"],
            "make_fvcom_rivers_forcing": ["206.12.90.239:5582", "206.12.90.239:5583"],
            "run_fvcom": ["206.12.90.239:5584", "206.12.90.239:5585"],
            "watch_fvcom": ["206.12.90.239:5586", "206.12.90.239:5587"],
        }


class TestMessageRegistry:
    """Unit tests for production YAML config file elements related to the non-worker
    configuration of the message registry.
    """

    def test_manager_msg_types(self, prod_config):
        msg_registry = prod_config["message registry"]
        assert msg_registry["manager"] == {
            "ack": "message acknowledged",
            "checklist cleared": "system checklist cleared",
            "unregistered worker": "ERROR - message received from unregistered worker",
            "unregistered message type": "ERROR - unregistered message type received from worker",
            "no after_worker function": "ERROR - after_worker function not found in next_workers module",
        }

    def test_next_workers_module(self, prod_config):
        msg_registry = prod_config["message registry"]
        assert msg_registry["next workers module"] == "nowcast.next_workers"
