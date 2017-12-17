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
import datetime as dt
import logging
import os
from pathlib import Path

import arrow
import netCDF4 as nc
import numpy as np
import pandas as pd
import pytz

from nemo_nowcast import NowcastWorker

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
        '--run-date',
        default=arrow.now().floor('day'),
        help='Date of the run to produce turbidity file for.'
    )
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
        extra={
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ')
        }
    )
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
        extra={
            'date': parsed_args.run_date.format('YYYY-MM-DD HH:mm:ss ZZ')
        }
    )
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

    # Pick time as 19:00, which means selected times will begin with 19:10
    # on prev day and go to 18:10
    idatedt = dt.datetime(
        run_date.year, run_date.month, run_date.day, 19, 0, 0
    )
    idateDD = _dateTimeToDecDay(idatedt)

    # Read most recent 24 hours data + extra for itnerpolation from
    # turbidity_csv, mthresh is max number of missing data points to
    # interpolate over (number of hours) + 1.01 to account for difference
    # between last and next hour (1) and rounding errors (.01)
    mthresh = 5.01
    try:
        tdf = _loadturb(idateDD, turbidity_csv, mthresh, ymd)
    except ValueError:
        return None

    # Interpolate and average data and write netcdf file to nc_filepath
    try:
        itdf = _interpTurb(tdf, idateDD, mthresh)
    except ValueError:
        return None
    try:
        iTurb = _calcAvgT(itdf, mthresh, ymd)
    except ValueError:
        return None
    dest_dir = Path(config['rivers']['turbidity']['forcing dir'])
    file_tmpl = config['rivers']['turbidity']['file template']
    nc_filepath = os.fspath(dest_dir / file_tmpl.format(run_date.date()))
    _writeTFile(nc_filepath, iTurb)
    logger.debug(f'stored Fraser River turbidity forcing file: {nc_filepath}')
    checklist = nc_filepath
    return checklist


def _loadturb(idate, turbidity_csv, mthresh, ymd):
    # Read file into pandas dataframe
    tdf = pd.read_csv(turbidity_csv, header=0)
    tdf['dtdate'] = pd.to_datetime(
        tdf['# date'] + ' ' + tdf['time'], format='%Y-%m-%d %H:%M:%S'
    )
    tdf['DD'] = [
        _dateTimeToDecDay(jj) for jj in _pacToUTC(tdf['dtdate'].values)
    ]
    # Select current 24 hr period + extra for interpolation
    # this will break if np.datetime64 string format changes
    tdf2 = (
        tdf.loc[(tdf['DD'] > (idate - 1.0 - mthresh / 24))
                & (tdf['DD'] <= (idate + mthresh / 24))].sort_values('DD')
        .copy()
    )
    tdf2.drop_duplicates(inplace=True)
    tdf2.index = range(len(tdf2))
    if len(tdf2) < 5:
        # data read can't satisfy coverage criteria
        msg = (
            f'Insufficient data to proceed to turbidity interpolation; '
            f'cannot create Fraser River turbidity file '
            f'for {ymd}'
        )
        logger.warning(msg)
        raise ValueError(msg)
    logger.debug(f'read turbidity data from {turbidity_csv}')
    return tdf2


def _interpTurb(tdf2, idate, mthresh):
    dfout = pd.DataFrame(
        index=range(int(mthresh) * 2 + 24), columns=('hDD', 'turbidity')
    )
    dfout['hDD'] = [
        idate - 1 + (ind - int(mthresh)) / 24.0 for ind in range(len(dfout))
    ]
    pd.set_option('precision', 9)
    iout = 0
    for ind, row in tdf2.iterrows():
        if ind == 0:
            ddlast = row['DD']
        if (dfout.loc[iout]['hDD'] - ddlast) < 0:
            # insert NaNs if no data at beginning of cycle
            nint = int(np.round((ddlast - dfout.loc[iout]['hDD']) * 24))
            for ii in range(0, nint):
                iout += 1
        if ((row['DD'] - ddlast) < mthresh / 24.0) & ((row['DD'] - ddlast) >
                                                      1.5 / 24.0):
            # if a break consists of 4 missing data points or less, linearly
            # interpolate through
            tlast = tdf2.loc[ind - 1]['turbidity']
            tnext = row['turbidity']
            ddnext = row['DD']
            nint = int(np.round((ddnext - ddlast) * 24) - 1)
            for ii in range(1, nint + 1):
                dd0 = ddlast + ii / 24.0
                tur0 = (
                    tlast + (dd0 - ddlast) / (ddnext - ddlast) *
                    (tnext - tlast)
                )
                if (dfout.loc[iout]['hDD'] - dd0) < .5 / 24.0:
                    dfout.loc[iout, 'turbidity'] = tur0
                    iout += 1
                else:
                    logger.error(
                        f'ERROR 2: {dfout.loc[iout]["hDD"]} {dd0} '
                        f'{dfout.loc[iout]["hDD"] - dd0}'
                    )
                    raise ValueError
        elif (row['DD'] - ddlast) >= mthresh / 24.0:
            # insert NaNs in larger holes
            nint = int(np.round((row['DD'] - ddlast) * 24) - 1)
            for ii in range(1, nint + 1):
                dd0 = ddlast + ii / 24.0
                if (dfout.loc[iout]['hDD'] - dd0) < .5 / 24.0:
                    iout += 1
                else:
                    logger.error('ERROR 4:')
                    raise ValueError
        # always append current tdf2 row's value
        if np.abs(dfout.loc[iout]['hDD'] - row['DD']) < .5 / 24.0:
            dfout.loc[iout, 'turbidity'] = row['turbidity']
        else:
            logger.error(
                f'ERROR 1: iout={iout} ind={ind} {dfout.loc[iout]["hDD"]} '
                f'{row["DD"]}'
            )
            raise ValueError
        iout += 1
        ddlast = row['DD']
    logger.debug('interpolated turbidity data')
    return dfout


def _calcAvgT(dfout, mthresh, ymd):
    i0 = int(mthresh)
    i1 = i0 + 23
    dfdata = dfout.loc[i0:i1]
    if len(dfdata.loc[dfdata['turbidity'] > 0].values) > 19:
        dfdata2 = dfdata.loc[dfdata['turbidity'] > 0]
        iTurb = np.mean(dfdata2['turbidity'].values)
    else:
        # data read doesn't satisfy coverage criteria
        msg = (
            f'Insufficient data after interpolation to create Fraser River '
            f'turbidity file '
            f'for {ymd}'
        )
        logger.warning(msg)
        raise ValueError(msg)
    return iTurb


def _writeTFile(
    fname,
    iTurb,
    dimTemplate='/results/forcing/rivers/RLonFraCElse_y2016m01d23.nc'
):
    f = nc.Dataset(dimTemplate)  # example for dims
    new = nc.Dataset(fname, 'w')

    # Copy dimensions
    for dname, the_dim in f.dimensions.items():
        new.createDimension(
            dname,
            len(the_dim) if not the_dim.isunlimited() else None
        )
    # create dimension variables:
    new_x = new.createVariable('nav_lat', np.float32, ('y', 'x'), zlib=True)
    new_x[:] = f.variables['nav_lat'][:, :]
    new_y = new.createVariable('nav_lon', np.float32, ('y', 'x'), zlib=True)
    new_y[:] = f.variables['nav_lon'][:, :]
    new_tc = new.createVariable(
        'time_counter', np.float32, 'time_counter', zlib=True
    )
    new_tc[:] = f.variables['time_counter']
    new_run = new.createVariable(
        'turb', float, ('time_counter', 'y', 'x'), zlib=True
    )
    new_run[:, :, :] = -999.99  # most cells are masked with negative numbers
    new_run[:, 400:448, 338:380] = iTurb  # set turbidity to daily average

    new.close()
    logger.debug(f'wrote file to {fname}')
    return


def _dateTimeToDecDay(dtin):
    tdif = dtin - dt.datetime(1900, 1, 1)
    dd = tdif.days + tdif.seconds / (3600 * 24)
    return dd


def _pacToUTC(pactime0):
    # input datetime object without tzinfo in Pacific Time and
    # output datetime object (or np array of them) without tzinfo in UTC
    pactime = np.array(pactime0, ndmin=1)
    if pactime.ndim > 1:
        raise Exception('Error: ndim>1')
    # handle case where array of numpy.datetime64 is input:
    # this will break if np.datetime64 string format changes
    if isinstance(pactime[0], np.datetime64):
        pactime2 = [
            dt.datetime.strptime(str(d)[:19], "%Y-%m-%dT%H:%M:%S")
            for d in pactime
        ]
        pactime = np.array(pactime2)
    out = np.empty(pactime.shape, dtype=object)
    pac = pytz.timezone('Canada/Pacific')
    utc = pytz.utc
    for ii in range(0, len(pactime)):
        itime = pactime[ii]
        loc_t = pac.localize(itime)
        utc_t = loc_t.astimezone(utc)
        out[ii] = utc_t.replace(tzinfo=None)
    return out[0] if np.isscalar(pactime0) else out


if __name__ == '__main__':
    main()  # pragma: no cover
