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

"""Functions to calculate lists of workers to launch after previous workers
end their work.

Function names **must** be of the form :py:func:`after_worker_name`.
"""
from nemo_nowcast import NextWorker


def after_download_weather(msg, config):
    """Calculate the list of workers to launch after the download_weather worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure 00': [],
        'failure 06': [],
        'failure 12': [],
        'failure 18': [],
        'success 00': [],
        'success 06': [],
        'success 12': [],
        'success 18': [],
    }
    if msg.type.endswith('06'):
        next_workers['success 06'] = [
            NextWorker('nowcast.workers.make_runoff_file')]
        if 'forecast2' in config['run types']:
            next_workers['success 06'].append(
                NextWorker(
                    'nowcast.workers.grib_to_netcdf', args=['forecast2']))
    if msg.type.endswith('12') and 'nowcast' in config['run types']:
        next_workers['success 12'] = [
            NextWorker('nowcast.workers.grib_to_netcdf', args=['nowcast+'])]
    return next_workers[msg.type]


def after_make_runoff_file(msg, config):
    """Calculate the list of workers to launch after the make_runoff_file
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure': [],
        'success': [],
    }
    return next_workers[msg.type]


def after_grib_to_netcdf(msg, config):
    """Calculate the list of workers to launch after the grib_to_netcdf worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure nowcast+': [],
        'failure forecast2': [],
        'success nowcast+': [],
        'success forecast2': [],
    }
    return next_workers[msg.type]
