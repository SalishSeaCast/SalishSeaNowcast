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

"""Salish Sea NEMO nowcast worker that produces ATOM feeds from forecast
and forecast2 run results.
"""
import logging
import os

import arrow
import docutils.core
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
import mako.template
import netCDF4 as nc
import numpy as np

from salishsea_tools import (
    nc_tools,
    stormtools,
    wind_tools,
)
from salishsea_tools.places import PLACES
import salishsea_tools.unit_conversions as converters

from nowcast import lib
import nowcast.figures.shared
from nowcast.nowcast_worker import NowcastWorker


worker_name = lib.get_module_name()
logger = logging.getLogger(worker_name)


def main():
    worker = NowcastWorker(worker_name, description=__doc__)
    worker.arg_parser.add_argument(
        'run_type', choices={'forecast', 'forecast2'},
        help='''
        Type of run to create feeds for:
        'forecast' means updated forecast run,
        'forecast2' means preliminary forecast run,
        ''',
    )
    salishsea_today = arrow.now('Canada/Pacific').floor('day')
    worker.arg_parser.add_argument(
        '--run-date', type=lib.arrow_date,
        default=salishsea_today,
        help='''
        Date of the run to create feeds for; use YYYY-MM-DD format.
        Defaults to {}.
        '''.format(salishsea_today.format('YYYY-MM-DD')),
    )
    worker.run(make_feeds, success, failure)


def success(parsed_args):
    logger.info(
        'ATOM feeds for {run_date} {0.run_type} run completed'
        .format(
            parsed_args, run_date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
            'run_type': parsed_args.run_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'success {.run_type}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical(
        'ATOM feeds for {run_date} {0.run_type} run failed'
        .format(
            parsed_args, run_date=parsed_args.run_date.format('YYYY-MM-DD')),
        extra={
            'run_type': parsed_args.run_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'failure {.run_type}'.format(parsed_args)
    return msg_type


def make_feeds(parsed_args, config, *args):
    run_date = parsed_args.run_date
    run_type = parsed_args.run_type
    web_config = config['web']
    feeds_path = os.path.join(
        web_config['www_path'], web_config['site_repo_url'].rsplit('/')[-1],
        'site', '_build', 'html', web_config['atom_path'],
    )
    checklist = {}
    for feed in web_config['feeds']:
        fg = _generate_feed(feed, web_config)
        max_ssh_info = _calc_max_ssh_risk(feed, run_date, run_type, config)
        if max_ssh_info['risk_level'] is not None:
            fe = _generate_feed_entry(feed, max_ssh_info, config)
            fg.add_entry(fe)
        fg.atom_file(os.path.join(feeds_path, feed), pretty=True)
    return checklist


def _generate_feed(feed, web_config):
    utcnow = arrow.utcnow()
    fg = FeedGenerator()
    fg.title(web_config['feeds'][feed]['title'])
    fg.id(_build_tag_uri('2015-12-12', feed, utcnow, web_config))
    fg.language('en-ca')
    fg.author(
        name='Salish Sea MEOPAR Project',
        uri='https://{0[domain]}/'.format(web_config))
    fg.rights(
        'Copyright 2015-{this_year}, '
        'Salish Sea MEOPAR Project Contributors and '
        'The University of British Columbia'
        .format(this_year=utcnow.year))
    fg.link(
        href=(
            'https://{0[domain]}/{0[atom_path]}/{feed}'
            .format(web_config, feed=feed)),
        rel='self', type='application/atom+xml')
    fg.link(
        href='https://{0[domain]}/storm-surge/forecast.html'.format(web_config),
        rel='related', type='text/html')
    return fg


def _generate_feed_entry(feed, max_ssh_info, config):
    now = arrow.now()
    fe = FeedEntry()
    fe.title(
        'Storm Surge Alert for {[tide_gauge_stn]}'
        .format(config['web']['feeds'][feed]))
    fe.id(_build_tag_uri(now.format('YYYY-MM-DD'), feed, now, config['web']))
    fe.author(
        name='Salish Sea MEOPAR Project',
        uri='https://{0[domain]}/'.format(config['web']))
    fe.content(
        _render_entry_content(feed, max_ssh_info, config),
        type='html')
    fe.link(
        rel='alternate', type='text/html',
        href='https://{[domain]}/storm-surge/forecast.html'
        .format(config['web'])
    )
    return fe


def _build_tag_uri(tag_date, feed, now, web_config):
    return (
        'tag:{0[domain]},{tag_date}:/{0[atom_path]}/{feed}/{now}'
        .format(
            web_config,
            tag_date=tag_date,
            feed=os.path.splitext(feed)[0],
            now=now.format('YYYYMMDDHHmmss')))


def _render_entry_content(feed, max_ssh_info, config):
    max_ssh_time_local = arrow.get(max_ssh_info['max_ssh_time']).to('local')
    tide_gauge_stn = config['web']['feeds'][feed]['tide_gauge_stn']
    max_ssh_info.update(_calc_wind_4h_avg(
        feed, max_ssh_info['max_ssh_time'], config))
    values = {
        'city': config['web']['feeds'][feed]['city'],
        'tide_gauge_stn': tide_gauge_stn,
        'conditions': {
            tide_gauge_stn: {
                'risk_level': max_ssh_info['risk_level'],
                'max_ssh_msl': max_ssh_info['max_ssh'],
                'wind_speed_4h_avg_kph':
                    converters.mps_kph(max_ssh_info['wind_speed_4h_avg']),
                'wind_speed_4h_avg_knots':
                    converters.mps_knots(max_ssh_info['wind_speed_4h_avg']),
                'wind_dir_4h_avg_heading':
                    converters.bearing_heading(
                        converters.wind_to_from(
                            max_ssh_info['wind_dir_4h_avg'])),
                'wind_dir_4h_avg_bearing':
                    converters.wind_to_from(max_ssh_info['wind_dir_4h_avg']),
                'max_ssh_time': max_ssh_time_local,
                'max_ssh_time_tzname': max_ssh_time_local.tzinfo.tzname(
                    max_ssh_time_local.datetime),
                'humanized_max_ssh_time':
                    converters.humanize_time_of_day(max_ssh_time_local),
            }}
    }
    template = mako.template.Template(
        filename=os.path.join(
            config['web']['templates_path'],
            config['web']['feed_entry_template']),
        input_encoding='utf-8')
    rendered_rst = template.render(**values)
    html = docutils.core.publish_parts(rendered_rst, writer_name='html')
    return html['body']


def _calc_max_ssh_risk(feed, run_date, run_type, config):
    feed_config = config['web']['feeds'][feed]
    ttide, _ = stormtools.load_tidal_predictions(
        os.path.join(
            config['ssh']['tidal_predictions'],
            feed_config['tidal predictions']))
    max_ssh, max_ssh_time = _calc_max_ssh(
        feed, ttide, run_date, run_type, config)
    risk_level = stormtools.storm_surge_risk_level(
        feed_config['tide_gauge_stn'], max_ssh, ttide)
    return {
        'max_ssh': max_ssh,
        'max_ssh_time': max_ssh_time,
        'risk_level': risk_level,
    }


def _calc_max_ssh(feed, ttide, run_date, run_type, config):
    results_path = config['run']['results archive'][run_type]
    tide_gauge_stn = config['web']['feeds'][feed]['tide_gauge_stn']
    grid_T_15m = nc.Dataset(
        os.path.join(
            results_path,
            run_date.format('DDMMMYY').lower(),
            '{tide_gauge_stn}.nc'
            .format(
                tide_gauge_stn=tide_gauge_stn.replace(' ', ''))))
    ssh_ts = nc_tools.ssh_timeseries_at_point(grid_T_15m, 0, 0, datetimes=True)
    ssh_corr = nowcast.figures.shared.correct_model_ssh(
        ssh_ts.ssh, ssh_ts.time, ttide)
    max_ssh = np.max(ssh_corr) + PLACES[tide_gauge_stn]['mean sea lvl']
    max_ssh_time = ssh_ts.time[np.argmax(ssh_corr)]
    return max_ssh, max_ssh_time


def _calc_wind_4h_avg(feed, max_ssh_time, config):
    weather_path = config['weather']['ops_dir']
    tide_gauge_stn = config['web']['feeds'][feed]['tide_gauge_stn']
    wind_avg = wind_tools.calc_wind_avg_at_point(
        arrow.get(max_ssh_time), weather_path,
        PLACES[tide_gauge_stn]['wind grid ji'], avg_hrs=-4)
    wind_vector = wind_tools.wind_speed_dir(wind_avg.u, wind_avg.v)
    return {
        'wind_speed_4h_avg': np.asscalar(wind_vector.speed),
        'wind_dir_4h_avg': np.asscalar(wind_vector.dir),
    }


if __name__ == '__main__':
    main()  # pragma: no cover
