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

"""Salish Sea NEMO nowcast worker that produces daily average Fraser River
turbidity file from hourly real-time turbidity data collected from Environment
and Climate Change Canada Fraser River water quality buoy.
"""
import logging
import os
from pathlib import Path

import arrow
import xarray

import pandas as pd
import datetime as dt
import numpy as np
import pytz

from nemo_nowcast import NowcastWorker, WorkerError

NAME = 'make_turbidity_file'
logger = logging.getLogger(NAME)


def main():
    """Set up and run the worker.

    For command-line usage see:

    :command:`python -m nowcast.workers.make_turbidity_file --help`
    """
    worker = NowcastWorker(NAME, description=__doc__)
    worker.init_cli()
    worker.cli.add_date_option(
        '--run-date', default=arrow.now().floor('day'),
        help='Date of the run to produce turbidity file for.')
    worker.run(make_turbidity_file, success, failure)


def success(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.info(
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'Fraser River turbidity file creation complete',
        extra={'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ')})
    return 'success'


def failure(parsed_args):
    """
    :param :py:class:`argparse.Namespace` parsed_args:

    :return: Nowcast system message type
    :rtype: str
    """
    logger.critical(
        f'{parsed_args.run_date.format("YYYY-MM-DD")} '
        f'Fraser River turbidity file creation failed',
        extra={'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ')})
    return 'failure'


def make_turbidity_file(parsed_args, config, *args):
    """Create a daily average Fraser River turbidity file from hourly real-time
    turbidity data.

    :param :py:class:`argparse.Namespace` parsed_args:
    :param :py:class:`nemo_nowcast.Config` config:

    :return: Nowcast system checklist item
    :rtype: str
    """
    run_date = parsed_args.run_date
    ymd = run_date.format("YYYY-MM-DD")
    logger.info(f'Creating Fraser River turbidity forcing file for {ymd}')
    turbidity_csv = config['rivers']['turbidity']['ECget Fraser turbidity']

    # Read most recent 24 hours data from turbidity_csv,
    # or 24 hours for run_date
    _loadturb24(run_date,turbidity_csv)
    print('turbidity_csv ',turbidity_csv)
    print('run_date ',run_date.date)
    print('type(run_date) ',type(run_date.date))
    # If data read doesn't satisfy coverage criteria
    #     msg = (
    #         f'Insufficient data to create Fraser River turbidity file '
    #         f'for {ymd}')
    #     logger.warning(msg)
    #     raise WorkerError(msg)

    dest_dir = Path(config['rivers']['turbidity']['forcing dir'])
    file_tmpl = config['rivers']['turbidity']['file template']
    nc_filepath = os.fspath(dest_dir / file_tmpl.format(run_date.date()))

    # Average data and write netcdf file to nc_filepath

    logger.debug(f'stored Fraser River turbidity forcing file: {nc_filepath}')
    checklist = nc_filepath
    return checklist


# Add private functions called by make_turbidity_file() here

def _loadturb24(run_date,turbidity_csv):
    tdf=pd.read_csv(turbidity_csv,header=0)
    tdf['dtdate']=pd.to_datetime(tdf['# date']+' '+tdf['time'],format='%Y-%m-%d %H:%M:%S')
    print("type(tdf['dtdate'][0]    ",type(tdf['dtdate'].values[0]))
    print(str(tdf['dtdate'].values[0]))
    tdf['DD']=_dateTimeToDecDay(_pacToUTC(tdf['dtdate'].values[0]))
    print(tdf[['# date','dtdate','time','DD','turbidity']].head())
    #idate=run_date.date
    #idd=dateTimeToDecDay(idate)
    #print('idd       ', idd)
    return

def _dateTimeToDecDay(dtin):
    tdif=dtin-dt.datetime(1900,1,1)
    dd=tdif.days+tdif.seconds/(3600*24)
    return dd

def _pacToUTC(pactime0):
    # input datetime object without tzinfo in Pacific Time and 
    # output datetime object (or np array of them) without tzinfo in UTC
    print('type(pactime0)    ',type(pactime0))
    pactime=np.array(pactime0,ndmin=1)
    if pactime.ndim>1:
        raise Exception('Error: ndim>1')
    # handle case where array of numpy.datetime64 is input:
    if isinstance(pactime[0],np.datetime64):
        pactime2=[dt.datetime.strptime(str(d)[:19],"%Y-%m-%dT%H:%M:%S") for d in pactime]
        pactime=np.array(pactime2)
    out=np.empty(pactime.shape,dtype=object)
    pac=pytz.timezone('Canada/Pacific')
    utc=pytz.utc
    for ii in range(0,len(pactime)):
        itime=pactime[ii]
        loc_t=pac.localize(itime)
        utc_t=loc_t.astimezone(utc)
        out[ii]=utc_t.replace(tzinfo=None)
    return (out[0] if np.isscalar(pactime0) else out)


if __name__ == '__main__':
    main()  # pragma: no cover
