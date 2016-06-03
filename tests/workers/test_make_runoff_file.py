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

"""Unit tests for Salish Sea NEMO nowcast make_runoff_file worker.
"""
from unittest.mock import (
    Mock,
    patch,
)

import arrow

import nowcast.lib
from nowcast.workers import make_runoff_file


@patch('nowcast.workers.make_runoff_file.NowcastWorker')
class TestMain:
    """Unit tests for main() function.
    """
    @patch('nowcast.workers.make_runoff_file.worker_name')
    def test_instantiate_worker(self, m_name, m_worker):
        make_runoff_file.main()
        args, kwargs = m_worker.call_args
        assert args == (m_name,)
        assert list(kwargs.keys()) == ['description']

    def test_add_run_date_arg(self, m_worker):
        make_runoff_file.main()
        args, kwargs = m_worker().arg_parser.add_argument.call_args_list[0]
        assert args == ('--run-date',)
        assert kwargs['type'] == nowcast.lib.arrow_date
        assert kwargs['default'] == arrow.now('Canada/Pacific').floor('day')
        assert 'help' in kwargs

    def test_run_worker(self, m_worker):
        make_runoff_file.main()
        args, kwargs = m_worker().run.call_args
        assert args == (
            make_runoff_file.make_runoff_file,
            make_runoff_file.success,
            make_runoff_file.failure,
        )


def test_success():
    parsed_args = Mock()
    msg_typ = make_runoff_file.success(parsed_args)
    assert msg_typ == 'success'


def test_failure():
    parsed_args = Mock()
    msg_typ = make_runoff_file.failure(parsed_args)
    assert msg_typ == 'failure'
