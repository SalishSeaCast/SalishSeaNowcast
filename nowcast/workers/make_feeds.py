# Copyright 2013-2015 The Salish Sea MEOPAR contributors
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
from feedgen.feed import FeedGenerator
import netCDF4 as nc
import numpy as np

from salishsea_tools import (
    nc_tools,
    stormtools,
)
from salishsea_tools.places import PLACES

from nowcast import (
    figures,
    lib,
)
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
        'ATOM feeds for {0.run_date} {0.run_type} run completed'
        .format(parsed_args), extra={
            'run_type': parsed_args.run_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'success {.run_type}'.format(parsed_args)
    return msg_type


def failure(parsed_args):
    logger.critical(
        'ATOM feeds for {0.run_date} {0.run_type} run failed'
        .format(parsed_args), extra={
            'run_type': parsed_args.run_type,
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ'),
        })
    msg_type = 'failure {.run_type}'.format(parsed_args)
    return msg_type


def make_feeds(parsed_args, config):
    run_date = parsed_args.run_date
    run_type = parsed_args.run_type
    web_config = config['web']
    for feed in web_config['feeds']:
        fg = _generate_feed(feed, web_config)
        max_ssh_info = _calc_max_ssh_risk(feed, run_date, run_type, config)
        if max_ssh_info['risk_level'] is not None:
            _generate_feed_entry(fg, max_ssh_info)
    return checklist


def _generate_feed(feed, web_config):
    utcnow = arrow.utcnow()
    fg = FeedGenerator()
    fg.title(web_config['feeds'][feed]['title'])
    fg.id(_build_tag_uri('2015-12-12', feed, utcnow, web_config))
    fg.language('en-ca')
    fg.author(
        name='Salish Sea MEOPAR Project',
        uri='http://{0[domain]}/'.format(web_config))
    fg.rights(
        'Copyright {this_year}, '
        'Salish Sea MEOPAR Project Contributors and '
        'The University of British Columbia'
        .format(this_year=utcnow.year))
    fg.link(
        href=(
            'http://{0[domain]}/{0[atom_path]}/{feed}'
            .format(web_config, feed=feed)),
        rel='self', type='application/atom+xml')
    fg.link(
        href='http://{0[domain]}/storm-surge/forecast.html'.format(web_config),
        rel='related', type='text/html')
    return fg


def _build_tag_uri(tag_date, feed, now, web_config):
    return (
        'tag:{0[domain]},{tag_date}:/{0[atom_path]}/{feed}/{now}'
        .format(
            web_config,
            tag_date=tag_date,
            feed=os.path.splitext(feed)[0],
            now=now.format('YYYYMMDDHHmmss')))


def _calc_max_ssh_risk(feed, run_date, run_type, config):
    feed_config = config['web']['feeds'][feed]
    ttide = stormtools.load_tidal_predictions(
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
    ssh_model, t_model = nc_tools.ssh_timeseries(grid_T_15m, datetimes=True)
    ssh_corr = figures.correct_model_ssh(ssh_model, t_model, ttide)
    max_ssh = np.max(ssh_corr) + PLACES[tide_gauge_stn]['mean sea lvl']
    max_ssh_time = t_model[np.argmax(ssh_corr)]
    return max_ssh, max_ssh_time
