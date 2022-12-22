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
"""SalishSeaCast worker that produces ATOM feeds from forecast
and forecast2 run results.
"""
import logging
import os

import arrow
import docutils.core
import mako.template
import netCDF4 as nc
import numpy as np
import salishsea_tools.unit_conversions as converters
from feedgen.entry import FeedEntry
from feedgen.feed import FeedGenerator
from nemo_nowcast import NowcastWorker, WorkerError
from salishsea_tools import nc_tools, stormtools, wind_tools
from salishsea_tools.places import PLACES

import nowcast.figures.shared

NAME = "make_feeds"
logger = logging.getLogger(NAME)


def main():
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_argument(
        "run_type",
        choices={"forecast", "forecast2"},
        help="""
        Type of run to create feeds for:
        'forecast' means updated forecast run,
        'forecast2' means preliminary forecast run,
        """,
    )
    worker.cli.add_date_option(
        "--run-date",
        default=arrow.now().floor("day"),
        help="Date of the run to create feeds for.",
    )
    worker.run(make_feeds, success, failure)


def success(parsed_args):
    logger.info(
        f'ATOM feeds for {parsed_args.run_date.format("YYYY-MM-DD")} '
        f"{parsed_args.run_type} run completed"
    )
    msg_type = f"success {parsed_args.run_type}"
    return msg_type


def failure(parsed_args):
    logger.critical(
        f'ATOM feeds for {parsed_args.run_date.format("YYYY-MM-DD")} '
        f"{parsed_args.run_type} run failed"
    )
    msg_type = f"failure {parsed_args.run_type}"
    return msg_type


def make_feeds(parsed_args, config, *args):
    run_date = parsed_args.run_date
    run_type = parsed_args.run_type
    figs_path = config["figures"]["storage path"]
    storm_surge_path = config["figures"]["storm surge info portal path"]
    atom_path = config["storm surge feeds"]["storage path"]
    feeds_path = os.path.join(figs_path, storm_surge_path, atom_path)
    checklist_key = f'{run_type} {run_date.format("YYYY-MM-DD")}'
    checklist = {checklist_key: []}
    for feed in config["storm surge feeds"]["feeds"]:
        fg = _generate_feed(
            feed, config["storm surge feeds"], os.path.join(storm_surge_path, atom_path)
        )
        max_ssh_info = _calc_max_ssh_risk(feed, run_date, run_type, config)
        if max_ssh_info["risk_level"] is not None:
            fe = _generate_feed_entry(feed, max_ssh_info, config, atom_path)
            fg.add_entry(fe)
        fg.atom_file(os.path.join(feeds_path, feed), pretty=True)
        checklist[checklist_key].append(os.path.join(feeds_path, feed))
    return checklist


def _generate_feed(feed, feeds_config, atom_path):
    utcnow = arrow.utcnow()
    fg = FeedGenerator()
    fg.title(feeds_config["feeds"][feed]["title"])
    fg.id(_build_tag_uri("2015-12-12", feed, utcnow, feeds_config, atom_path))
    fg.language("en-ca")
    fg.author(name="SalishSeaCast Project", uri=f'https://{feeds_config["domain"]}/')
    fg.rights(
        f"Copyright 2015 - present by the SalishSeaCast Project "
        f"Contributors and The University of British Columbia"
    )
    fg.link(
        href=(f'https://{feeds_config["domain"]}/{atom_path}/{feed}'),
        rel="self",
        type="application/atom+xml",
    )
    fg.link(
        href=f'https://{feeds_config["domain"]}/storm-surge/forecast.html',
        rel="related",
        type="text/html",
    )
    return fg


def _generate_feed_entry(feed, max_ssh_info, config, atom_path):
    now = arrow.now()
    fe = FeedEntry()
    fe.title(
        "Storm Surge Alert for {[tide gauge stn]}".format(
            config["storm surge feeds"]["feeds"][feed]
        )
    )
    fe.id(
        _build_tag_uri(
            now.format("YYYY-MM-DD"), feed, now, config["storm surge feeds"], atom_path
        )
    )
    fe.author(
        name="SalishSeaCast Project",
        uri=f'https://{config["storm surge feeds"]["domain"]}/',
    )
    fe.content(_render_entry_content(feed, max_ssh_info, config), type="html")
    fe.link(
        rel="alternate",
        type="text/html",
        href=f'https://{config["storm surge feeds"]["domain"]}/'
        f"storm-surge/forecast.html",
    )
    return fe


def _build_tag_uri(tag_date, feed, now, feeds_config, atom_path):
    return (
        f'tag:{feeds_config["domain"]},{tag_date}:/{atom_path}/'
        f'{os.path.splitext(feed)[0]}/{now.format("YYYYMMDDHHmmss")}'
    )


def _render_entry_content(feed, max_ssh_info, config):
    max_ssh_time_local = arrow.get(max_ssh_info["max_ssh_time"]).to("local")
    feed_config = config["storm surge feeds"]["feeds"][feed]
    tide_gauge_stn = feed_config["tide gauge stn"]
    max_ssh_info.update(_calc_wind_4h_avg(feed, max_ssh_info["max_ssh_time"], config))
    values = {
        "city": feed_config["city"],
        "tide_gauge_stn": tide_gauge_stn,
        "conditions": {
            tide_gauge_stn: {
                "risk_level": max_ssh_info["risk_level"],
                "max_ssh_msl": max_ssh_info["max_ssh"],
                "wind_speed_4h_avg_kph": converters.mps_kph(
                    max_ssh_info["wind_speed_4h_avg"]
                ),
                "wind_speed_4h_avg_knots": converters.mps_knots(
                    max_ssh_info["wind_speed_4h_avg"]
                ),
                "wind_dir_4h_avg_heading": converters.bearing_heading(
                    converters.wind_to_from(max_ssh_info["wind_dir_4h_avg"])
                ),
                "wind_dir_4h_avg_bearing": converters.wind_to_from(
                    max_ssh_info["wind_dir_4h_avg"]
                ),
                "max_ssh_time": max_ssh_time_local,
                "max_ssh_time_tzname": max_ssh_time_local.tzinfo.tzname(
                    max_ssh_time_local.datetime
                ),
                "humanized_max_ssh_time": converters.humanize_time_of_day(
                    max_ssh_time_local
                ),
            }
        },
    }
    template = mako.template.Template(
        filename=os.path.join(
            os.path.dirname(__file__),
            config["storm surge feeds"]["feed entry template"],
        ),
        input_encoding="utf-8",
    )
    rendered_rst = template.render(**values)
    html = docutils.core.publish_parts(rendered_rst, writer_name="html")
    return html["body"]


def _calc_max_ssh_risk(feed, run_date, run_type, config):
    feed_config = config["storm surge feeds"]["feeds"][feed]
    ttide, _ = stormtools.load_tidal_predictions(
        os.path.join(
            config["ssh"]["tidal predictions"], feed_config["tidal predictions"]
        )
    )
    max_ssh, max_ssh_time = _calc_max_ssh(feed, ttide, run_date, run_type, config)
    risk_level = stormtools.storm_surge_risk_level(
        feed_config["tide gauge stn"], max_ssh, ttide
    )
    return {"max_ssh": max_ssh, "max_ssh_time": max_ssh_time, "risk_level": risk_level}


def _calc_max_ssh(feed, ttide, run_date, run_type, config):
    results_path = config["results archive"][run_type]
    tide_gauge_stn = config["storm surge feeds"]["feeds"][feed]["tide gauge stn"]
    grid_T_15m = nc.Dataset(
        os.path.join(
            results_path,
            run_date.format("DDMMMYY").lower(),
            f'{tide_gauge_stn.replace(" ", "")}.nc',
        )
    )
    ssh_ts = nc_tools.ssh_timeseries_at_point(grid_T_15m, 0, 0, datetimes=True)
    max_ssh, max_ssh_time = nowcast.figures.shared.find_ssh_max(
        tide_gauge_stn, ssh_ts, ttide
    )
    if np.isnan(max_ssh):
        logger.critical(
            f"no {tide_gauge_stn} feed generated: max sea surface height is "
            f"NaN at {max_ssh_time}"
        )
        raise WorkerError
    return max_ssh, max_ssh_time


def _calc_wind_4h_avg(feed, max_ssh_time, config):
    weather_path = config["weather"]["ops dir"]
    tide_gauge_stn = config["storm surge feeds"]["feeds"][feed]["tide gauge stn"]
    wind_avg = wind_tools.calc_wind_avg_at_point(
        arrow.get(max_ssh_time),
        weather_path,
        PLACES[tide_gauge_stn]["wind grid ji"],
        avg_hrs=-4,
    )
    wind_vector = wind_tools.wind_speed_dir(wind_avg.u, wind_avg.v)
    return {
        "wind_speed_4h_avg": wind_vector.speed.item(),
        "wind_dir_4h_avg": wind_vector.dir.item(),
    }


if __name__ == "__main__":
    main()  # pragma: no cover
