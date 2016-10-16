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
            next_workers['success 06'].extend([
                NextWorker(
                    'nowcast.workers.get_NeahBay_ssh', args=['forecast2']),
                NextWorker(
                    'nowcast.workers.grib_to_netcdf', args=['forecast2']),
                ])
    if msg.type.endswith('12') and 'nowcast' in config['run types']:
        next_workers['success 12'] = [
            NextWorker('nowcast.workers.get_NeahBay_ssh', args=['nowcast']),
            NextWorker('nowcast.workers.grib_to_netcdf', args=['nowcast+']),
        ]
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


def after_get_NeahBay_ssh(msg, config):
    """Calculate the list of workers to launch after the get_NeahBay_ssh worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure nowcast': [],
        'failure forecast': [],
        'failure forecast2': [],
        'success nowcast': [],
        'success forecast2': [],
        'success forecast': [],
    }
    if msg.type == 'success forecast':
        for host in config['run']['enabled hosts']:
            enabled_host_config = config['run']['enabled hosts'][host]
            upload_forcing_ssh = (
                'forecast' in enabled_host_config['run types']
                and not enabled_host_config['shared storage'])
            if upload_forcing_ssh:
                next_workers['success forecast'].append(
                    NextWorker(
                        'nowcast.workers.upload_forcing',
                        args=[host, 'ssh']))
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
    msg_run_type_mapping = {
        'nowcast+': 'nowcast',
        'forecast2': 'forecast2',
    }
    for host in config['run']['remote hosts']:
        if host in config['run']:
            for msg_suffix, run_type in msg_run_type_mapping.items():
                if run_type in config['run types']:
                    next_workers['success {}'.format(msg_suffix)].append(
                        NextWorker(
                            'nowcast.workers.upload_forcing',
                            args=[config['run'][host], msg_suffix]),
                    )
    if all(
        ('nowcast-green host' in config['run'],
         'nowcast-green' in config['run types'])):
        next_workers['success nowcast+'].append(
            NextWorker(
                'nowcast.workers.make_forcing_links',
                args=[
                    config['run']['nowcast-green host'], 'nowcast-green',
                    '--shared-storage'])
        )
    return next_workers[msg.type]


def after_upload_forcing(msg, config):
    """Calculate the list of workers to launch after the upload_forcing worker
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
        'failure ssh': [],
        'success nowcast+': [],
        'success forecast2': [],
        'success ssh': [],
    }
    try:
        host_name = list(msg.payload.keys())[0]
    except (AttributeError, IndexError):
        # Malformed payload - no host name in payload;
        # upload_forcing worker probably crashed
        return []
    run_types = [
        # (run_type, make_forcing_links)
        ('nowcast', 'nowcast+'),
        ('forecast', 'ssh'),
        ('forecast2', 'forecast2'),
    ]
    for run_type, links_run_type in run_types:
        if run_type in config['run types']:
            next_workers['success {}'.format(links_run_type)] = [
                NextWorker(
                    'nowcast.workers.make_forcing_links',
                    args=[host_name, links_run_type]),
            ]
    return next_workers[msg.type]


def after_make_forcing_links(msg, config):
    """Calculate the list of workers to launch after the make_forcing_links
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure nowcast+': [],
        'failure nowcast-green': [],
        'failure forecast2': [],
        'failure ssh': [],
        'success nowcast+': [],
        'success nowcast-green': [],
        'success forecast2': [],
        'success ssh': [],
    }
    if msg.type.startswith('success'):
        run_type = {
            'nowcast+': 'nowcast',
            'nowcast-green': 'nowcast-green',
            'ssh': 'forecast',
            'forecast2': 'forecast2',
        }[msg.type.split()[1]]
        host_name = config['run']['cloud host']
        if 'cloud host' in config['run'] and host_name in msg.payload:
            next_workers[msg.type] = [
                NextWorker(
                    'nowcast.workers.run_NEMO',
                    args=[host_name, run_type], host=host_name),
            ]
        host_name = config['run']['nowcast-green host']
        if 'nowcast-green host' in config['run'] and host_name in msg.payload:
            next_workers[msg.type] = [
                NextWorker(
                    'nowcast.workers.run_NEMO',
                    args=[host_name, run_type, '--shared-storage'],
                    host=host_name),
            ]
    return next_workers[msg.type]


def after_run_NEMO(msg, config):
    """Calculate the list of workers to launch after the run_NEMO worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure nowcast': [],
        'failure nowcast-green': [],
        'failure forecast': [],
        'failure forecast2': [],
        'success nowcast': [],
        'success nowcast-green': [],
        'success forecast': [],
        'success forecast2': [],
    }
    return next_workers[msg.type]


def after_watch_NEMO(msg, config):
    """Calculate the list of workers to launch after the watch_NEMO worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure nowcast': [],
        'failure nowcast-green': [],
        'failure forecast': [],
        'failure forecast2': [],
        'success nowcast': [],
        'success nowcast-green': [],
        'success forecast': [],
        'success forecast2': [],
    }
    if msg.type.startswith('success'):
        run_type = msg.type.split()[1]
        if run_type == 'nowcast':
            next_workers['success nowcast'].append(
                NextWorker(
                    'nowcast.workers.get_NeahBay_ssh', args=['forecast']))
        enabled_host_config = (
            config['run']['enabled hosts'][msg.payload['host']])
        if not enabled_host_config['shared storage']:
            next_workers[msg.type].append(
                NextWorker(
                    'nowcast.workers.download_results',
                    args=[
                        msg.payload['host'], run_type,
                        '--run-date', msg.payload['run date']]))
    return next_workers[msg.type]


def after_download_results(msg, config):
    """Calculate the list of workers to launch after the download_results
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure nowcast': [],
        'failure nowcast-green': [],
        'failure forecast': [],
        'failure forecast2': [],
        'success nowcast': [],
        'success nowcast-green': [],
        'success forecast': [],
        'success forecast2': [],
    }
    return next_workers[msg.type]
