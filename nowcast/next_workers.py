# Copyright 2013-2018 The Salish Sea MEOPAR contributors
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
            NextWorker('nowcast.workers.make_runoff_file')
        )
        for stn in config['observations']['ctd data']['stations']:
            next_workers['success 06'].append(
                NextWorker('nowcast.workers.get_onc_ctd', args=[stn])
            )
        for ferry in config['observations']['ferry data']['ferries']:
            next_workers['success 06'].append(
                NextWorker('nowcast.workers.get_onc_ferry', args=[ferry])
            )
        if 'forecast2' in config['run types']:
            next_workers['success 06'].extend([
                NextWorker(
                    'nowcast.workers.get_NeahBay_ssh', args=['forecast2']
                ),
                NextWorker(
                    'nowcast.workers.grib_to_netcdf', args=['forecast2']
                ),
            ])
    if msg.type.endswith('12'):
        next_workers['success 12'].extend([
            NextWorker('nowcast.workers.get_NeahBay_ssh', args=['nowcast']),
            NextWorker('nowcast.workers.grib_to_netcdf', args=['nowcast+']),
            NextWorker('nowcast.workers.download_live_ocean'),
        ])
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
                and not enabled_host_config['shared storage']
            )
            if upload_forcing_ssh:
                next_workers['success forecast'].append(
                    NextWorker(
                        'nowcast.workers.upload_forcing', args=[host, 'ssh']
                    )
                )
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
                'nowcast.workers.ping_erddap', args=['download_weather']
            )
        )
    for host in config['run']['enabled hosts']:
        if not config['run']['enabled hosts'][host]['shared storage']:
            for msg_suffix, run_type in msg_run_type_mapping.items():
                if run_type in config['run types']:
                    next_workers[f'success {msg_suffix}'].append(
                        NextWorker(
                            'nowcast.workers.upload_forcing',
                            args=[host, msg_suffix]
                        ),
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
        'success USDDL': [],
    }
    if msg.type.startswith('success'):
        ctd_stn = msg.type.split()[1]
        next_workers[msg.type].append(
            NextWorker('nowcast.workers.ping_erddap', args=[f'{ctd_stn}-CTD'])
        )
    return next_workers[msg.type]


def after_get_onc_ferry(msg, config, checklist):
    """Calculate the list of workers to launch after the get_onc_ferry
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
        'success TWDP': [],
    }
    if msg.type.startswith('success'):
        ferry_platform = msg.type.split()[1]
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.ping_erddap',
                args=[f'{ferry_platform}-ferry']
            )
        )
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
                    list(checklist['Live Ocean products'].keys())[0]
                ],
                host=config['temperature salinity']['matlab host']
            )
        )
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


def after_make_turbidity_file(msg, config, checklist):
    """Calculate the list of workers to launch after the make_turbidity_file
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
        for host in config['run']['enabled hosts']:
            shared_storage = (
                config['run']['enabled hosts'][host]['shared storage']
            )
            host_run_types = config['run']['enabled hosts'][host]['run types']
            if 'nowcast-green' in host_run_types and not shared_storage:
                next_workers['success'].append(
                    NextWorker(
                        'nowcast.workers.upload_forcing',
                        args=[host, 'turbidity']
                    )
                )
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
        'failure turbidity': [],
        'success nowcast+': [],
        'success forecast2': [],
        'success ssh': [],
        'success turbidity': [],
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
        ('nowcast-green', 'turbidity'),
    ]
    for run_type, links_run_type in run_types:
        if run_type in config['run types']:
            next_workers[f'success {links_run_type}'] = [
                NextWorker(
                    'nowcast.workers.make_forcing_links',
                    args=[host_name, links_run_type]
                ),
            ]
            if links_run_type == 'turbidity':
                next_workers[f'success {links_run_type}'] = [
                    NextWorker(
                        'nowcast.workers.make_forcing_links',
                        args=[host_name, 'nowcast-green']
                    ),
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
                                checklist['forcing links'][host]['run date']
                            ],
                            host=host
                        ),
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
    if msg.type.startswith('success'):
        run_type = msg.type.split()[1]
        host = msg.payload[run_type]['host']
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.watch_NEMO', args=[host, run_type], host=host
            )
        )
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
            config['wave forecasts']['run when'].split('after ')[1]
        )
        if run_type == 'nowcast':
            next_workers['success nowcast'].extend([
                NextWorker(
                    'nowcast.workers.get_NeahBay_ssh', args=['forecast']
                ),
                NextWorker(
                    'nowcast.workers.make_fvcom_boundary',
                    args=[(config['vhfr fvcom runs']['host']), 'nowcast'],
                    host=(config['vhfr fvcom runs']['host'])
                ),
            ])
        if run_type == 'forecast':
            if wave_forecast_after == 'forecast':
                host_name = config['wave forecasts']['host']
                next_workers['success forecast'].extend([
                    NextWorker(
                        'nowcast.workers.make_ww3_wind_file',
                        args=[host_name, 'forecast'],
                        host=host_name
                    ),
                    NextWorker(
                        'nowcast.workers.make_ww3_current_file',
                        args=[host_name, 'forecast'],
                        host=host_name
                    ),
                ])
            else:
                next_workers['success forecast'].append(
                    NextWorker(
                        'nowcast.workers.make_turbidity_file',
                        args=['--run-date', msg.payload[run_type]['run date']]
                    )
                )
        if run_type == 'nowcast-green':
            if wave_forecast_after == 'nowcast-green':
                host_name = config['wave forecasts']['host']
                next_workers['success nowcast-green'].extend([
                    NextWorker(
                        'nowcast.workers.make_ww3_wind_file',
                        args=[host_name, 'forecast'],
                        host=host_name
                    ),
                    NextWorker(
                        'nowcast.workers.make_ww3_current_file',
                        args=[host_name, 'forecast'],
                        host=host_name
                    ),
                ])
            for host in config['run']['enabled hosts']:
                run_types = config['run']['enabled hosts'][host]['run types']
                if 'nowcast-dev' in run_types:
                    next_workers['success nowcast-green'].append(
                        NextWorker(
                            'nowcast.workers.make_forcing_links',
                            args=[host, 'nowcast+', '--shared-storage']
                        )
                    )
        if run_type == 'forecast2':
            host_name = config['wave forecasts']['host']
            next_workers['success forecast2'].extend([
                NextWorker(
                    'nowcast.workers.make_ww3_wind_file',
                    args=[host_name, 'forecast2'],
                    host=host_name
                ),
                NextWorker(
                    'nowcast.workers.make_ww3_current_file',
                    args=[host_name, 'forecast2'],
                    host=host_name
                ),
            ])
        enabled_host_config = (
            config['run']['enabled hosts'][msg.payload[run_type]['host']]
        )
        if not enabled_host_config['shared storage']:
            next_workers[msg.type].append(
                NextWorker(
                    'nowcast.workers.download_results',
                    args=[
                        msg.payload[run_type]['host'], run_type, '--run-date',
                        msg.payload[run_type]['run date']
                    ]
                )
            )
    return next_workers[msg.type]


def after_watch_NEMO_hindcast(msg, config, checklist):
    """Calculate the list of workers to launch after the watch_NEMO_handcast
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
        next_workers[msg.type].extend([
            NextWorker(
                'nowcast.workers.download_results',
                args=[
                    msg.payload['hindcast']['host'], 'hindcast', '--run-date',
                    msg.payload['hindcast']['run date']
                ]
            ),
            NextWorker(
                'nowcast.workers.watch_NEMO_hindcast',
                args=[msg.payload['hindcast']['host']]
            ),
        ])
    return next_workers[msg.type]


def after_run_NEMO_hindcast(msg, config, checklist):
    """Calculate the list of workers to launch after the run_NEMO_hindcast
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


def after_make_fvcom_boundary(msg, config, checklist):
    """Calculate the list of workers to launch after the
    after_make_fvcom_boundary worker ends.

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
        'success nowcast': [],
        'success forecast': [],
    }
    if msg.type == 'success nowcast':
        host_name = config['vhfr fvcom runs']['host']
        run_type = msg.type.split()[1]
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.run_fvcom',
                args=[host_name, run_type],
                host=host_name
            )
        )
    return next_workers[msg.type]


def after_run_fvcom(msg, config, checklist):
    """Calculate the list of workers to launch after the after_run_fvcom worker
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
        'success nowcast': [],
        'success forecast': [],
    }
    if msg.type.startswith('success'):
        run_type = msg.type.split()[1]
        host = msg.payload[run_type]['host']
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.watch_fvcom',
                args=[host, run_type],
                host=host
            )
        )
    return next_workers[msg.type]


def after_watch_fvcom(msg, config, checklist):
    """Calculate the list of workers to launch after the after_watch_fvcom worker
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
        'success nowcast': [],
    }
    if msg.type.startswith('success'):
        run_type = msg.type.split()[1]
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.download_fvcom_results',
                args=[
                    msg.payload[run_type]['host'], run_type, '--run-date',
                    msg.payload[run_type]['run date']
                ]
            )
        )
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
                args=[host_name, run_type],
                host=host_name
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
    next_workers = {
        'crash': [],
        'failure forecast2': [],
        'failure forecast': [],
        'success forecast2': [],
        'success forecast': [],
    }
    if msg.type.startswith('success'):
        run_type = msg.type.split()[1]
        host = msg.payload[run_type]['host']
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.watch_ww3', args=[host, run_type], host=host
            )
        )
    return next_workers[msg.type]


def after_watch_ww3(msg, config, checklist):
    """Calculate the list of workers to launch after the watch_ww3 worker ends.

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
        run_type = msg.type.split()[1]
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.download_wwatch3_results',
                args=[
                    msg.payload[run_type]['host'], run_type, '--run-date',
                    msg.payload[run_type]['run date']
                ]
            )
        )
    return next_workers[msg.type]


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
        run_type = msg.type.split()[1]
        if run_type == 'hindcast':
            run_date = arrow.get(
                checklist['NEMO run']['hindcast']['run id'][:7], 'DDMMMYY'
            )
            next_workers[msg.type].append(
                NextWorker(
                    'nowcast.workers.split_results',
                    args=[run_type, run_date.format('YYYY-MM-DD')]
                )
            )
            return next_workers[msg.type]
        run_date = checklist['NEMO run'][run_type]['run date']
        if run_type.startswith('nowcast'):
            next_workers[msg.type].append(
                NextWorker(
                    'nowcast.workers.make_plots',
                    args=[
                        'nemo', run_type, 'research', '--run-date', run_date
                    ]
                )
            )
            if run_type == 'nowcast':
                run_date = (
                    arrow.get(run_date).replace(days=-1).format('YYYY-MM-DD')
                )
                next_workers[msg.type].append(
                    NextWorker(
                        'nowcast.workers.make_plots',
                        args=[
                            'nemo', run_type, 'comparison', '--run-date',
                            run_date
                        ]
                    )
                )
            if run_type == 'nowcast-green':
                next_workers[msg.type].append(
                    NextWorker(
                        'nowcast.workers.ping_erddap', args=['nowcast-green']
                    )
                )
                return next_workers[msg.type]
        if run_type.startswith('forecast'):
            next_workers[msg.type].append(
                NextWorker(
                    'nowcast.workers.update_forecast_datasets',
                    args=['nemo', run_type, '--run-date', run_date]
                )
            )
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


def after_download_wwatch3_results(msg, config, checklist):
    """Calculate the list of workers to launch after the
    download_wwatch3_results worker ends.

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
        'success forecast2': [],
    }
    return next_workers[msg.type]


def after_download_fvcom_results(msg, config, checklist):
    """Calculate the list of workers to launch after the
    download_fvcom_results worker ends.

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
        'success nowcast': [],
    }
    if msg.type.startswith('success'):
        run_type = msg.type.split()[1]
        run_date = checklist['FVCOM run'][run_type]['run date']
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.make_plots',
                args=['fvcom', run_type, 'publish', '--run-date', run_date]
            )
        )
    return next_workers[msg.type]


def after_update_forecast_datasets(msg, config, checklist):
    """Calculate the list of workers to launch after the
    update_forecast_datasets worker ends.

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
        'failure nemo forecast': [],
        'failure nemo forecast2': [],
        'success nemo forecast': [],
        'success nemo forecast2': [],
    }
    if msg.type.startswith('success nemo forecast'):
        run_type = msg.type.split()[2]
        run_date = checklist['NEMO run'][run_type]['run date']
        next_workers[msg.type].extend([
            NextWorker('nowcast.workers.ping_erddap', args=['nemo-forecast']),
            NextWorker(
                'nowcast.workers.make_plots',
                args=['nemo', run_type, 'publish', '--run-date', run_date]
            ),
        ])
    return next_workers[msg.type]


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
        'failure nemo nowcast research': [],
        'failure nemo nowcast comparison': [],
        'failure nemo nowcast publish': [],
        'failure nemo nowcast-green research': [],
        'failure nemo forecast publish': [],
        'failure nemo forecast2 publish': [],
        'failure fvcom nowcast publish': [],
        'success nemo nowcast research': [],
        'success nemo nowcast comparison': [],
        'success nemo nowcast publish': [],
        'success nemo nowcast-green research': [],
        'success nemo forecast publish': [],
        'success nemo forecast2 publish': [],
        'success fvcom nowcast publish': [],
    }
    if msg.type.startswith('success nemo') and 'forecast' in msg.type:
        _, _, run_type, _ = msg.type.split()
        next_workers[msg.type].append(
            NextWorker(
                'nowcast.workers.make_feeds',
                args=[
                    run_type, '--run-date',
                    checklist['NEMO run'][run_type]['run date']
                ]
            )
        )
    return next_workers[msg.type]


def after_make_surface_current_tiles(msg, config, checklist):
    """Calculate the list of workers to launch after the
    make_surface_current_tiles worker ends.

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
            NextWorker('nemo_nowcast.workers.clear_checklist')
        ],
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
