#  Copyright 2013-2019 The Salish Sea MEOPAR contributors
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


class TestConfig:
    """Unit tests for production YAML config file elements that are not worker-related.
    """

    def test_checklist_file(self, prod_config, tmpdir):
        # Config.load() transforms envvars
        assert (
            prod_config["checklist file"]
            == f"{tmpdir}/nowcast_logs/nowcast_checklist.yaml"
        )

    def test_python(self, prod_config, tmpdir):
        # Config.load() transforms envvars
        assert prod_config["python"] == f"{tmpdir}/nowcast-env/bin/python"


class TestSlackNotifications:
    """Unit tests for production YAML config file elements related to slack notifications.
    """

    def test_daily_progress_channel_envvar(self, prod_config):
        slack_notifications = prod_config["slack notifications"]
        assert "SLACK_SSC_DAILY_PROGRESS" in slack_notifications

    def test_daily_progress_channel_workers(self, prod_config):
        slack_notifications = prod_config["slack notifications"]
        expected = [
            "collect_weather",
            "download_live_ocean",
            "watch_NEMO",
            "watch_NEMO_hindcast",
            "watch_NEMO_agrif",
            "watch_fvcom",
            "watch_ww3",
        ]
        assert slack_notifications["SLACK_SSC_DAILY_PROGRESS"] == expected

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
    """Unit tests for production YAML config file elements related to 0mq message system.
    """

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
            ],
            "run_NEMO": ["salish.eos.ubc.ca:5556", "206.12.48.112:5556"],
            "watch_NEMO": ["salish.eos.ubc.ca:5557", "206.12.48.112:5557"],
            "make_ww3_wind_file": "206.12.48.112:5570",
            "make_ww3_current_file": "206.12.48.112:5571",
            "run_ww3": "206.12.48.112:5572",
            "watch_ww3": "206.12.48.112:5573",
            "make_fvcom_boundary": "206.12.48.112:5580",
            "make_fvcom_rivers_forcing": "206.12.48.112:5581",
            "run_fvcom": "206.12.48.112:5582",
            "watch_fvcom": "206.12.48.112:5583",
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
