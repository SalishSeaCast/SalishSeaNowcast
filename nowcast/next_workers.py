# Copyright 2013-2017 The Salish Sea MEOPAR contributors
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
import arrow
from nemo_nowcast import NextWorker


def after_download_weather(msg, config, checklist):
    """Calculate the list of workers to launch after the download_weather worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

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
    if msg.type.startswith('success') and msg.type.endswith('06'):
        next_workers['success 06'].append(
            NextWorker('nowcast.workers.make_runoff_file'))
        for stn in config['observations']['ctd data']['stations']:
            next_workers['success 06'].append(
                NextWorker('nowcast.workers.get_onc_ctd', args=[stn]))
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


def after_make_runoff_file(msg, config, checklist):
    """Calculate the list of workers to launch after the make_runoff_file
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure': [],
        'success': [],
    }
    return next_workers[msg.type]


def after_get_NeahBay_ssh(msg, config, checklist):
    """Calculate the list of workers to launch after the get_NeahBay_ssh worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

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


def after_grib_to_netcdf(msg, config, checklist):
    """Calculate the list of workers to launch after the grib_to_netcdf worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

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
    if msg.type.startswith('success') and msg.type.endswith('nowcast+'):
        next_workers['success nowcast+'].append(
            NextWorker(
                'nowcast.workers.ping_erddap', args=['download_weather']))
    for host in config['run']['enabled hosts']:
        if not config['run']['enabled hosts'][host]['shared storage']:
            for msg_suffix, run_type in msg_run_type_mapping.items():
                if run_type in config['run types']:
                    next_workers[f'success {msg_suffix}'].append(
                        NextWorker(
                            'nowcast.workers.upload_forcing',
                            args=[host, msg_suffix]),
                    )
        if 'nowcast-dev' in config['run']['enabled hosts'][host]['run types']:
            next_workers['success nowcast+'].append(
                NextWorker(
                    'nowcast.workers.make_forcing_links',
                    args=[host, 'nowcast+', '--shared-storage'])
            )
    return next_workers[msg.type]


def after_get_onc_ctd(msg, config, checklist):
    """Calculate the list of workers to launch after the get_onc_ctd
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure': [],
        'success SCVIP': [],
        'success SEVIP': [],
        'success LSBBL': [],
        'success USDDL': [],
    }
    if msg.type.startswith('success'):
        ctd_stn = msg.type.split()[1]
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.ping_erddap',
                args=[f'{ctd_stn}-CTD']))
    return next_workers[msg.type]


def after_download_live_ocean(msg, config, checklist):
    """Calculate the list of workers to launch after the download_live_ocean
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure': [],
        'success': [],
    }
    if msg.type == 'success':
        next_workers['success'].append(
            NextWorker(
                'nowcast.workers.make_live_ocean_files',
                args=[
                    '--run-date',
                    list(checklist['Live Ocean products'].keys())[0]],
                host=config['temperature salinity']['matlab host']))
    return next_workers[msg.type]


def after_make_live_ocean_files(msg, config, checklist):
    """Calculate the list of workers to launch after the make_live_ocean_files
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure': [],
        'success': [],
    }
    return next_workers[msg.type]


def after_upload_forcing(msg, config, checklist):
    """Calculate the list of workers to launch after the upload_forcing worker
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

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
            next_workers[f'success {links_run_type}'] = [
                NextWorker(
                    'nowcast.workers.make_forcing_links',
                    args=[host_name, links_run_type]),
            ]
    return next_workers[msg.type]


def after_make_forcing_links(msg, config, checklist):
    """Calculate the list of workers to launch after the make_forcing_links
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure nowcast+': [],
        'failure nowcast-green': [],
        'failure nowcast-dev': [],
        'failure forecast2': [],
        'failure ssh': [],
        'success nowcast+': [],
        'success nowcast-green': [],
        'success nowcast-dev': [],
        'success forecast2': [],
        'success ssh': [],
    }
    if msg.type.startswith('success'):
        run_types = {
            'nowcast+': ('nowcast', 'nowcast-dev'),
            'nowcast-green': ('nowcast-green',),
            'ssh': ('forecast',),
            'forecast2': ('forecast2',),
        }[msg.type.split()[1]]
        for host in msg.payload:
            host_run_types = config['run']['enabled hosts'][host]['run types']
            for run_type in run_types:
                if run_type in host_run_types:
                    next_workers[msg.type] = [
                        NextWorker(
                            'nowcast.workers.run_NEMO',
                            args=[
                                host, run_type, '--run-date',
                                checklist['forcing links'][host]['run date']],
                            host=host),
                    ]
    return next_workers[msg.type]


def after_run_NEMO(msg, config, checklist):
    """Calculate the list of workers to launch after the run_NEMO worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure nowcast': [],
        'failure nowcast-green': [],
        'failure nowcast-dev': [],
        'failure forecast': [],
        'failure forecast2': [],
        'success nowcast': [],
        'success nowcast-green': [],
        'success nowcast-dev': [],
        'success forecast': [],
        'success forecast2': [],
    }
    return next_workers[msg.type]


def after_watch_NEMO(msg, config, checklist):
    """Calculate the list of workers to launch after the watch_NEMO worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure nowcast': [],
        'failure nowcast-green': [],
        'failure nowcast-dev': [],
        'failure forecast': [],
        'failure forecast2': [],
        'success nowcast': [],
        'success nowcast-green': [],
        'success nowcast-dev': [],
        'success forecast': [],
        'success forecast2': [],
    }
    if msg.type.startswith('success'):
        run_type = msg.type.split()[1]
        wave_forecast_after = (
            config['wave forecasts']['run when'].split('after ')[1])
        if run_type == 'nowcast':
            next_workers['success nowcast'].append(
                NextWorker(
                    'nowcast.workers.get_NeahBay_ssh', args=['forecast']))
        if run_type == 'forecast':
            if wave_forecast_after == 'forecast':
                host_name = config['wave forecasts']['host']
                next_workers['success forecast'].extend(
                    [NextWorker(
                        'nowcast.workers.make_ww3_wind_file',
                        args=[host_name, 'forecast'], host=host_name),
                        NextWorker(
                            'nowcast.workers.make_ww3_current_file',
                            args=[host_name, 'forecast'], host=host_name)
                    ],
                )
            else:
                next_workers['success forecast'].append(
                    NextWorker(
                        'nowcast.workers.make_forcing_links',
                        args=[msg.payload[run_type]['host'], 'nowcast-green']))
        if run_type == 'nowcast-green':
            if wave_forecast_after == 'nowcast-green':
                host_name = config['wave forecasts']['host']
                next_workers['success nowcast-green'].extend(
                    [NextWorker(
                        'nowcast.workers.make_ww3_wind_file',
                        args=[host_name, 'forecast'], host=host_name),
                        NextWorker(
                            'nowcast.workers.make_ww3_current_file',
                            args=[host_name, 'forecast'], host=host_name)
                    ],
                )
        if run_type == 'forecast2':
            host_name = config['wave forecasts']['host']
            next_workers['success forecast2'].extend(
                [NextWorker(
                    'nowcast.workers.make_ww3_wind_file',
                    args=[host_name, 'forecast2'], host=host_name),
                    NextWorker(
                        'nowcast.workers.make_ww3_current_file',
                        args=[host_name, 'forecast2'], host=host_name)
                ],
            )
        enabled_host_config = (
            config['run']['enabled hosts'][msg.payload[run_type]['host']])
        if not enabled_host_config['shared storage']:
            next_workers[msg.type].append(
                NextWorker(
                    'nowcast.workers.download_results',
                    args=[
                        msg.payload[run_type]['host'], run_type,
                        '--run-date', msg.payload[run_type]['run date']]))
    return next_workers[msg.type]


def after_make_ww3_wind_file(msg, config, checklist):
    """Calculate the list of workers to launch after the 
    after_make_ww3_wind_file worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    return []


def after_make_ww3_current_file(msg, config, checklist):
    """Calculate the list of workers to launch after the 
    after_make_ww3_current_file worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure forecast2': [],
        'failure forecast': [],
        'success forecast2': [],
        'success forecast': [],
    }
    if msg.type.startswith('success'):
        host_name = config['wave forecasts']['host']
        run_type = msg.type.split()[1]
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.run_ww3',
                args=[host_name, run_type], host=host_name
            )
        )
    return next_workers[msg.type]


def after_run_ww3(msg, config, checklist):
    """Calculate the list of workers to launch after the after_run_ww3 worker 
    ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    return []


def after_download_results(msg, config, checklist):
    """Calculate the list of workers to launch after the download_results
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure nowcast': [],
        'failure nowcast-green': [],
        'failure forecast': [],
        'failure forecast2': [],
        'failure hindcast': [],
        'success nowcast': [],
        'success nowcast-green': [],
        'success forecast': [],
        'success forecast2': [],
        'success hindcast': [],
    }
    if msg.type.startswith('success'):
        if msg.type.endswith('hindcast'):
            return next_workers[msg.type]
        run_type = msg.type.split()[1]
        run_date = checklist['NEMO run'][run_type]['run date']
        if run_type == 'nowcast-green':
            next_workers[msg.type].append(
                NextWorker(
                    'nowcast.workers.make_plots',
                    args=[run_type, 'research', '--run-date', run_date]))
            return next_workers[msg.type]
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.make_plots',
                args=[run_type, 'publish', '--run-date', run_date]))
        if run_type == 'nowcast':
            next_workers[msg.type].append(
                NextWorker(
                    'nowcast.workers.make_plots',
                    args=[run_type, 'research', '--run-date', run_date]))
            run_date = checklist['NEMO run']['nowcast']['run date']
            run_date = (
                arrow.get(run_date).replace(days=-1).format('YYYY-MM-DD'))
            next_workers[msg.type].append(
                NextWorker(
                    'nowcast.workers.make_plots',
                    args=[run_type, 'comparison', '--run-date', run_date]))
            next_workers[msg.type].append(
                NextWorker('nowcast.workers.ping_erddap', args=['nowcast']))
    return next_workers[msg.type]


def after_make_plots(msg, config, checklist):
    """Calculate the list of workers to launch after the make_plots
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure nowcast research': [],
        'failure nowcast comparison': [],
        'failure nowcast publish': [],
        'failure nowcast-green research': [],
        'failure forecast publish': [],
        'failure forecast2 publish': [],
        'success nowcast research': [],
        'success nowcast comparison': [],
        'success nowcast publish': [],
        'success nowcast-green research': [],
        'success forecast publish': [],
        'success forecast2 publish': [],
    }
    if msg.type.startswith('success') and 'forecast' in msg.type:
        _, run_type, _ = msg.type.split()
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.make_feeds',
                args=[
                    run_type,
                    '--run-date', checklist['NEMO run'][run_type]['run date']]))
    return next_workers[msg.type]


def after_split_results(msg, config, checklist):
    """Calculate the list of workers to launch after the split_results
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    return []


def after_ping_erddap(msg, config, checklist):
    """Calculate the list of workers to launch after the ping_erddap
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    return []


def after_make_feeds(msg, config, checklist):
    """Calculate the list of workers to launch after the make_feeds
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure forecast': [],
        'failure forecast2': [],
        'success forecast': [],
        'success forecast2': [
            NextWorker('nemo_nowcast.workers.clear_checklist')],
    }
    return next_workers[msg.type]


def after_clear_checklist(msg, config, checklist):
    """Calculate the list of workers to launch after the clear_checklist
    worker ends.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`nemo_nowcast.message.Message`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    next_workers = {
        'crash': [],
        'failure': [],
        'success': [NextWorker('nemo_nowcast.workers.rotate_logs')],
    }
    return next_workers[msg.type]


def after_rotate_logs(msg, config, checklist):
    """Calculate the list of workers to launch after the rotate_logs worker
    ends, but it is an empty list because rotate_logs is the last worker in
    the daily automation cycle.

    :arg msg: Nowcast system message.
    :type msg: :py:class:`collections.namedtuple`

    :arg config: :py:class:`dict`-like object that holds the nowcast system
                 configuration that is loaded from the system configuration
                 file.
    :type config: :py:class:`nemo_nowcast.config.Config`

    :arg dict checklist: System checklist: data structure containing the
                         present state of the nowcast system.

    :returns: Worker(s) to launch next
    :rtype: list
    """
    return []
