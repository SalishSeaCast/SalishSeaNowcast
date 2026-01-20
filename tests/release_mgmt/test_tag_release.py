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


"""Unit tests for SalishSeaCast tag_release script."""

import logging
from unittest.mock import Mock, patch

import hglib
import pytest

from release_mgmt import tag_release


@patch("release_mgmt.tag_release.Path.exists", return_value=True, autospec=True)
@patch("release_mgmt.tag_release.hglib.open", autospec=True)
class TestTagRepo:
    """Unit tests for _rag_repo() function."""

    def test_repo_not_exists(self, m_hg_open, m_exists, caplog):
        m_exists.return_value = False
        caplog.set_level(logging.DEBUG)

        with pytest.raises(SystemExit):
            tag_release._tag_repo("NEMO-3.6-code", "PROD-hindcast-201806-v2-2017")

        assert caplog.records[1].levelname == "ERROR"
        expected = "repo does not exist: NEMO-3.6-code"
        assert caplog.records[1].message == expected

    def test_no_repo_root(self, m_hg_open, m_exists, caplog):
        m_hg_open.side_effect = hglib.error.ServerError
        caplog.set_level(logging.DEBUG)

        with pytest.raises(SystemExit):
            tag_release._tag_repo("NEMO-3.6-code", "PROD-hindcast-201806-v2-2017")

        assert caplog.records[1].levelname == "ERROR"
        expected = "unable to find Mercurial repo root in: NEMO-3.6-code"
        assert caplog.records[1].message == expected

    def test_uncommitted_changes(self, m_hg_open, m_exists, caplog):
        m_hg_open().__enter__ = Mock(name="hg_client")
        m_hg_open().__enter__.status.return_value = None
        caplog.set_level(logging.DEBUG)

        with pytest.raises(SystemExit):
            tag_release._tag_repo("NEMO-3.6-code", "PROD-hindcast-201806-v2-2017")

        assert caplog.records[1].levelname == "ERROR"
        expected = "uncommitted changes in repo: NEMO-3.6-code"
        assert caplog.records[1].message == expected

    def test_incoming_changes(self, m_hg_open, m_exists, caplog):
        m_hg_open().__enter__ = Mock(name="hg_client")
        m_hg_open().__enter__().status.return_value = None
        m_hg_open().__enter__().incoming.return_value = ["changesets"]
        caplog.set_level(logging.DEBUG)

        with pytest.raises(SystemExit):
            tag_release._tag_repo("NEMO-3.6-code", "PROD-hindcast-201806-v2-2017")

        assert caplog.records[1].levelname == "WARNING"
        expected = (
            "found incoming changes from Bitbucket that you need to deal "
            "with in repo: NEMO-3.6-code"
        )
        assert caplog.records[1].message == expected

    def test_hg_tag(self, m_hg_open, m_exists, caplog):
        m_hg_client = m_hg_open().__enter__ = Mock(name="hg_client")
        m_hg_client().status.return_value = None
        m_hg_client().incoming.return_value = []
        m_hg_client().tags.return_value = [(b"tip", 9, b"ff71fb7feaa6", False)]
        m_hg_client().config.return_value = [
            (b"ui", b"username", b"Tom Dickson <tom@example.com>")
        ]
        caplog.set_level(logging.DEBUG)

        tag_release._tag_repo("NEMO-3.6-code", "PROD-hindcast-201806-v2-2017")

        expected = "PROD-hindcast-201806-v2-2017".encode()
        assert m_hg_client().tag.call_args_list[0][0][0] == expected
        expected = {
            "message": "Tag production release PROD-hindcast-201806-v2-2017.",
            "user": "SalishSeaNowcast.release_mgmt.tag_release for Tom Dickson <tom@example.com>",
        }
        assert m_hg_client().tag.call_args_list[0][1] == expected
        assert caplog.records[1].levelname == "INFO"
        expected = "added PROD-hindcast-201806-v2-2017 to repo: NEMO-3.6-code"
        assert caplog.records[1].message == expected

    def test_duplicate_tag(self, m_hg_open, m_exists, caplog):
        m_hg_client = m_hg_open().__enter__ = Mock(name="hg_client")
        m_hg_client().status.return_value = None
        m_hg_client().incoming.return_value = []
        m_hg_client().tags.return_value = [
            (b"tip", 9, b"ff71fb7feaa6", False),
            (b"PROD-hindcast-201806-v2-2017", 7, b"3541bdb39959", False),
        ]
        caplog.set_level(logging.DEBUG)

        tag_release._tag_repo("NEMO-3.6-code", "PROD-hindcast-201806-v2-2017")

        assert caplog.records[1].levelname == "WARNING"
        expected = (
            "tag 'PROD-hindcast-201806-v2-2017' already exists in repo: NEMO-3.6-code"
        )
        assert caplog.records[1].message == expected
        assert not m_hg_client.push.called

    def test_tip_is_tagging_commit(self, m_hg_open, m_exists, caplog):
        m_hg_client = m_hg_open().__enter__ = Mock(name="hg_client")
        m_hg_client().status.return_value = None
        m_hg_client().incoming.return_value = []
        m_hg_client().tags.return_value = [
            (b"tip", 9, b"ff71fb7feaa6", False),
            (b"PROD-hindcast-201806-v2-2017", 7, b"3541bdb39959", False),
        ]
        m_hg_client().config.return_value = [
            (b"ui", b"username", b"Tom Dickson <tom@example.com>")
        ]
        m_hg_client().tip().author = b"SalishSeaNowcast.release_mgmt.tag_release"
        m_hg_client().tip().desc = (
            b"Tag production release PROD-hindcast-201806-v2-2017."
        )
        caplog.set_level(logging.DEBUG)

        tag_release._tag_repo("NEMO-3.6-code", "PROD-hindcast-201806-v3-2017")

        expected = "PROD-hindcast-201806-v3-2017".encode()
        assert m_hg_client().tag.call_args_list[0][0][0] == expected
        expected = {
            "rev": "PROD-hindcast-201806-v2-2017",
            "message": "Tag production release PROD-hindcast-201806-v3-2017.",
            "user": "SalishSeaNowcast.release_mgmt.tag_release for Tom Dickson <tom@example.com>",
        }
        assert m_hg_client().tag.call_args_list[0][1] == expected
        assert caplog.records[1].levelname == "INFO"
        expected = "added PROD-hindcast-201806-v3-2017 to repo: NEMO-3.6-code"
        assert caplog.records[1].message == expected

    def test_hg_tag_error(self, m_hg_open, m_exists, caplog):
        m_hg_client = m_hg_open().__enter__ = Mock(name="hg_client")
        m_hg_client().status.return_value = None
        m_hg_client().incoming.return_value = []
        m_hg_client().tags.return_value = [(b"tip", 9, b"ff71fb7feaa6", False)]
        m_hg_client().config.return_value = [
            (b"ui", b"username", b"Tom Dickson <tom@example.com>")
        ]
        m_hg_client().tag.side_effect = hglib.error.CommandError(
            ("args",), "ret", "out", b"err"
        )
        caplog.set_level(logging.DEBUG)

        with pytest.raises(hglib.error.CommandError):
            tag_release._tag_repo("NEMO-3.6-code", "PROD-hindcast-201806-v2-2017")
        assert not m_hg_client.push.called

    def test_hg_push(self, m_hg_open, m_exists, caplog):
        m_hg_client = m_hg_open().__enter__ = Mock(name="hg_client")
        m_hg_client().status.return_value = None
        m_hg_client().incoming.return_value = []
        m_hg_client().tags.return_value = [(b"tip", 9, b"ff71fb7feaa6", False)]
        m_hg_client().config.return_value = [
            (b"ui", b"username", b"Tom Dickson <tom@example.com>")
        ]
        caplog.set_level(logging.DEBUG)

        tag_release._tag_repo("NEMO-3.6-code", "PROD-hindcast-201806-v2-2017")

        m_hg_client().push.assert_called_once_with()
        assert caplog.records[2].levelname == "INFO"
        expected = "pushed PROD-hindcast-201806-v2-2017 tag to Bitbucket from repo: NEMO-3.6-code"
        assert caplog.records[2].message == expected
