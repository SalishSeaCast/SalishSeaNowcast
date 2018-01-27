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
"""A collection of Python functions to produce model residual calculations and
visualizations.
"""
import datetime
import io

import arrow
import requests

from dateutil import tz
import pytz

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import netCDF4 as nc
import numpy as np
import pandas as pd

from salishsea_tools import (
    geo_tools,
    stormtools,
    tidetools,
    nc_tools,
)

from nowcast import analyze
from nowcast.figures import shared

# Module constants

paths = {
    'nowcast': '/results/SalishSea/nowcast/',
    'forecast': '/results/SalishSea/forecast/',
    'forecast2': '/results/SalishSea/forecast2/',
    'tides': '/data/nsoontie/MEOPAR/tools/SalishSeaNowcast/tidal_predictions/'
}

colours = {
    'nowcast': 'DodgerBlue',
    'forecast': 'ForestGreen',
    'forecast2': 'MediumVioletRed',
    'observed': 'Indigo',
    'predicted': 'ForestGreen',
    'model': 'blue',
    'residual': 'DimGray'
}

SITES = {
    # Constant with station information: mean sea level, latitude,
    # longitude, station number, historical extreme ssh, etc.
    # Extreme ssh from DFO website
    # Mean sea level from CHS tidal constiuents.
    # VENUS coordinates from the VENUS website. Depth is in meters.
    'Nanaimo': {
        'lat': 49.16,
        'lon': -123.93,
        'msl': 3.08,
        'extreme_ssh': 5.47
    },
    'Halibut Bank': {
        'lat': 49.34,
        'lon': -123.72
    },
    'Dungeness': {
        'lat': 48.15,
        'lon': -123.117
    },
    'La Perouse Bank': {
        'lat': 48.83,
        'lon': -126.0
    },
    'Point Atkinson': {
        'lat': 49.33,
        'lon': -123.25,
        'msl': 3.09,
        'stn_no': 7795,
        'extreme_ssh': 5.61
    },
    'Victoria': {
        'lat': 48.41,
        'lon': -123.36,
        'msl': 1.8810,
        'stn_no': 7120,
        'extreme_ssh': 3.76
    },
    'Campbell River': {
        'lat': 50.04,
        'lon': -125.24,
        'msl': 2.916,
        'stn_no': 8074,
        'extreme_ssh': 5.35
    },
    'Neah Bay': {
        'lat': 48.4,
        'lon': -124.6,
        'stn_no': 9443090
    },
    'Friday Harbor': {
        'lat': 48.55,
        'lon': -123.016667,
        'stn_no': 9449880
    },
    'Cherry Point': {
        'lat': 48.866667,
        'lon': -122.766667,
        'stn_no': 9449424,
        'msl': 3.543,
        'extreme_ssh': 5.846
    },
    'SandHeads': {
        'lat': 49.10,
        'lon': -123.30
    },
    'Tofino': {
        'lat': 49.15,
        'lon': -125.91,
        'stn_no': 8615
    },
    'Bamfield': {
        'lat': 48.84,
        'lon': -125.14,
        'stn_no': 8545
    },
    'VENUS': {
        'East': {
            'lat': 49.0419,
            'lon': -123.3176,
            'depth': 170
        },
        'Central': {
            'lat': 49.0401,
            'lon': -123.4261,
            'depth': 300
        }
    }
}

# Module functions


def plot_residual_forcing(ax, runs_list, t_orig):
    """ Plots the observed water level residual at Neah Bay against
    forced residuals from existing ssh*.txt files for Neah Bay.
    Function may produce none, any, or all (nowcast, forecast, forecast 2)
    forced residuals depending on availability for specified date (runs_list).

    :arg ax: The axis where the residuals are plotted.
    :type ax: axis object

    :arg runs_list: Runs that are verified as complete.
    :type runs_list: list

    :arg t_orig: Date being considered.
    :type t_orig: datetime object

    """

    # truncation times
    sdt = t_orig.replace(tzinfo=tz.tzutc())
    edt = sdt + datetime.timedelta(days=1)

    # retrieve observations, tides and residual
    tides = shared.get_tides('Neah Bay', path=paths['tides'])
    res_obs, obs = obs_residual_ssh_NOAA('Neah Bay', tides, sdt, sdt)
    # truncate and plot
    res_obs_trun, time_trun = analyze.truncate_data(
        np.array(res_obs), np.array(obs.time), sdt, edt
    )
    ax.plot(
        time_trun, res_obs_trun, colours['observed'], label='observed', lw=2.5
    )

    # plot forcing for each simulation
    for mode in runs_list:
        filename_NB, run_date = analyze.create_path(mode, t_orig, 'ssh*.txt')
        if filename_NB:
            dates, surge, fflag = NeahBay_forcing_anom(
                filename_NB, run_date, paths['tides']
            )
            surge_t, dates_t = analyze.truncate_data(
                np.array(surge), np.array(dates), sdt, edt
            )
            ax.plot(dates_t, surge_t, label=mode, lw=2.5, color=colours[mode])
    ax.set_title(
        'Comparison of observed and forced sea surface'
        ' height residuals at Neah Bay:'
        '{t_forcing:%d-%b-%Y}'.format(t_forcing=t_orig)
    )


def plot_residual_model(axs, names, runs_list, grid_B, t_orig):
    """ Plots the observed sea surface height residual against the
    sea surface height model residual (calculate_residual) at
    specified stations. Function may produce none, any, or all
    (nowcast, forecast, forecast 2) model residuals depending on
    availability for specified date (runs_list).

    :arg ax: The axis where the residuals are plotted.
    :type ax: list of axes

    :arg names: Names of station.
    :type names: list of names

    :arg runs_list: Runs that have been verified as complete.
    :type runs_list: list

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg t_orig: Date being considered.
    :type t_orig: datetime object

    """

    bathy, X, Y = tidetools.get_bathy_data(grid_B)
    t_orig_obs = t_orig + datetime.timedelta(days=-1)
    t_final_obs = t_orig + datetime.timedelta(days=1)

    # truncation times
    sdt = t_orig.replace(tzinfo=tz.tzutc())
    edt = sdt + datetime.timedelta(days=1)

    for ax, name in zip(axs, names):
        # Identify model grid point
        lat = SITES[name]['lat']
        lon = SITES[name]['lon']
        j, i = geo_tools.find_closest_model_point(
            lon, lat, X, Y, land_mask=bathy.mask
        )
        # Observed residuals and wlevs and tides
        ttide = shared.get_tides(name, path=paths['tides'])
        res_obs, wlev_meas = obs_residual_ssh(
            name, ttide, t_orig_obs, t_final_obs
        )
        # truncate and plot
        res_obs_trun, time_obs_trun = analyze.truncate_data(
            np.array(res_obs), np.array(wlev_meas.time), sdt, edt
        )
        ax.plot(
            time_obs_trun,
            res_obs_trun,
            c=colours['observed'],
            lw=2.5,
            label='observed'
        )

        for mode in runs_list:
            filename, run_date = analyze.create_path(
                mode, t_orig, 'SalishSea_1h_*_grid_T.nc'
            )
            grid_T = nc.Dataset(filename)
            res_mod, t_model, ssh_corr, ssh_mod = model_residual_ssh(
                grid_T, j, i, ttide
            )
            # truncate and plot
            res_mod_trun, t_mod_trun = analyze.truncate_data(
                res_mod, t_model, sdt, edt
            )
            ax.plot(
                t_mod_trun, res_mod_trun, label=mode, c=colours[mode], lw=2.5
            )

        ax.set_title(
            'Comparison of modelled sea surface height residuals at'
            ' {station}: {t:%d-%b-%Y}'.format(station=name, t=t_orig)
        )


def get_error_model(names, runs_list, grid_B, t_orig):
    """ Sets up the calculation for the model residual error.

    :arg names: Names of station.
    :type names: list of strings

    :arg runs_list: Runs that have been verified as complete.
    :type runs_list: list

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg t_orig: Date being considered.
    :type t_orig: datetime object

    :returns: error_mod_dict, t_mod_dict, t_orig_dict
    """

    bathy, X, Y = tidetools.get_bathy_data(grid_B)
    t_orig_obs = t_orig + datetime.timedelta(days=-1)
    t_final_obs = t_orig + datetime.timedelta(days=1)

    # truncation times
    sdt = t_orig.replace(tzinfo=tz.tzutc())
    edt = sdt + datetime.timedelta(days=1)

    error_mod_dict = {}
    t_mod_dict = {}
    for name in names:
        error_mod_dict[name] = {}
        t_mod_dict[name] = {}
        # Look up model grid
        lat = SITES[name]['lat']
        lon = SITES[name]['lon']
        j, i = geo_tools.find_closest_model_point(
            lon, lat, X, Y, land_mask=bathy.mask
        )
        # Observed residuals and wlevs and tides
        ttide = shared.get_tides(name, path=paths['tides'])
        res_obs, wlev_meas = obs_residual_ssh(
            name, ttide, t_orig_obs, t_final_obs
        )
        res_obs_trun, time_obs_trun = analyze.truncate_data(
            np.array(res_obs), np.array(wlev_meas.time), sdt, edt
        )

        for mode in runs_list:
            filename, run_date = analyze.create_path(
                mode, t_orig, 'SalishSea_1h_*_grid_T.nc'
            )
            grid_T = nc.Dataset(filename)
            res_mod, t_model, ssh_corr, ssh_mod = model_residual_ssh(
                grid_T, j, i, ttide
            )
            # Truncate
            res_mod_trun, t_mod_trun = analyze.truncate_data(
                res_mod, t_model, sdt, edt
            )
            # Error
            error_mod = analyze.calculate_error(
                res_mod_trun, t_mod_trun, res_obs_trun, time_obs_trun
            )
            error_mod_dict[name][mode] = error_mod
            t_mod_dict[name][mode] = t_mod_trun

    return error_mod_dict, t_mod_dict


def get_error_forcing(runs_list, t_orig):
    """ Sets up the calculation for the forcing residual error.

    :arg runs_list: Runs that have been verified as complete.
    :type runs_list: list

    :arg t_orig: Date being considered.
    :type t_orig: datetime object

    :returns: error_frc_dict, t_frc_dict
    """

    # truncation times
    sdt = t_orig.replace(tzinfo=tz.tzutc())
    edt = sdt + datetime.timedelta(days=1)

    # retrieve observed residual
    tides = shared.get_tides('Neah Bay', path=paths['tides'])
    res_obs, obs = obs_residual_ssh_NOAA('Neah Bay', tides, sdt, sdt)
    res_obs_trun, time_trun = analyze.truncate_data(
        np.array(res_obs), np.array(obs.time), sdt, edt
    )

    # calculate forcing error
    error_frc_dict = {}
    t_frc_dict = {}
    for mode in runs_list:
        filename_NB, run_date = analyze.create_path(mode, t_orig, 'ssh*.txt')
        if filename_NB:
            dates, surge, fflag = NeahBay_forcing_anom(
                filename_NB, run_date, paths['tides']
            )
            surge_t, dates_t = analyze.truncate_data(
                np.array(surge), np.array(dates), sdt, edt
            )
            error_frc = analyze.calculate_error(
                surge_t, dates_t, res_obs_trun, obs.time
            )
            error_frc_dict[mode] = error_frc
            t_frc_dict[mode] = dates_t

    return error_frc_dict, t_frc_dict


def plot_error_model(axs, names, runs_list, grid_B, t_orig):
    """ Plots the model residual error.

    :arg axs: The axis where the residual errors are plotted.
    :type axs: list of axes

    :arg names: Names of station.
    :type names: list of strings

    :arg runs_list: Runs that have been verified as complete.
    :type runs_list: list of strings

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg t_orig: Date being considered.
    :type t_orig: datetime object

    """

    error_mod_dict, t_mod_dict = get_error_model(
        names, runs_list, grid_B, t_orig
    )

    for ax, name in zip(axs, names):
        ax.set_title(
            'Comparison of modelled residual errors at {station}:'
            ' {t:%d-%b-%Y}'.format(station=name, t=t_orig)
        )
        for mode in runs_list:
            ax.plot(
                t_mod_dict[name][mode],
                error_mod_dict[name][mode],
                label=mode,
                c=colours[mode],
                lw=2.5
            )


def plot_error_forcing(ax, runs_list, t_orig):
    """ Plots the forcing residual error.

    :arg ax: The axis where the residual errors are plotted.
    :type ax: axis object

    :arg runs_list: Runs that have been verified as complete.
    :type runs_list: list

    :arg t_orig: Date being considered.
    :type t_orig: datetime object

    """

    error_frc_dict, t_frc_dict = get_error_forcing(runs_list, t_orig)

    for mode in runs_list:
        ax.plot(
            t_frc_dict[mode],
            error_frc_dict[mode],
            label=mode,
            c=colours[mode],
            lw=2.5
        )
        ax.set_title(
            'Comparison of observed and forced residual errors at '
            'Neah Bay: {t_forcing:%d-%b-%Y}'.format(t_forcing=t_orig)
        )


def plot_residual_error_all(subject, grid_B, t_orig, figsize=(20, 16)):
    """ Sets up and combines the plots produced by plot_residual_forcing
    and plot_residual_model or plot_error_forcing and plot_error_model.
    This function specifies the stations for which the nested functions
    apply. Figure formatting except x-axis limits and titles are included.

    :arg subject: Subject of figure, either 'residual' or 'error'.
    :type subject: string

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg t_orig: Date being considered.
    :type t_orig: datetime object

    :arg figsize: Figure size (width, height) in inches.
    :type figsize: 2-tuple

    :returns: fig
    """
    # set up axis limits - based on full 24 hour period 0000 to 2400
    sax = t_orig
    eax = t_orig + datetime.timedelta(days=1)

    runs_list = analyze.verified_runs(t_orig)

    fig, axes = plt.subplots(4, 1, figsize=figsize)
    axs_mod = [axes[1], axes[2], axes[3]]
    names = ['Point Atkinson', 'Victoria', 'Campbell River']

    if subject == 'residual':
        plot_residual_forcing(axes[0], runs_list, t_orig)
        plot_residual_model(axs_mod, names, runs_list, grid_B, t_orig)
    elif subject == 'error':
        plot_error_forcing(axes[0], runs_list, t_orig)
        plot_error_model(axs_mod, names, runs_list, grid_B, t_orig)

    for ax in axes:
        ax.set_ylim([-0.4, 0.4])
        ax.set_xlabel('[hrs UTC]')
        ax.set_ylabel('[m]')
        hfmt = mdates.DateFormatter('%m/%d %H:%M')
        ax.xaxis.set_major_formatter(hfmt)
        ax.legend(loc=2, ncol=4)
        ax.grid()
        ax.set_xlim([sax, eax])

    return fig


def combine_errors(name, mode, dates, grid_B):
    """Combine model and forcing errors for a simulaion mode over several days.
    returns time series of both model and forcing error and daily means.
    Treats each simulation over 24 hours.

    :arg name: name of station for model calculation
    :type name: string, example 'Point Atkinson', 'Victoria'

    :arg mode: simulation mode: nowcast, forecast, or forecast2
    :type mode: string

    :arg dates: list of dates to combine
    :type dates: list of datetime objects

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset

    :returns: force, model, time, daily_time.
    model and force are dictionaries with keys 'error' and 'daily'.
    Each key corresponds to array of error time series and daily means.
    time is an array of times correspinding to error caclulations
    daily_time is an array of timea corresponding to daily means
    """

    model = {'error': np.array([]), 'daily': np.array([])}
    force = {'error': np.array([]), 'daily': np.array([])}
    time = np.array([])
    daily_time = np.array([])

    for t_sim in dates:
        # check if the run happened
        if mode in analyze.verified_runs(t_sim):
            # retrieve forcing and model error
            e_frc_tmp, t_frc_tmp = get_error_forcing([mode], t_sim)
            e_mod_tmp, t_mod_tmp = get_error_model([name], [mode], grid_B,
                                                   t_sim)
            e_frc_tmp = shared.interp_to_model_time(
                t_mod_tmp[name][mode], e_frc_tmp[mode], t_frc_tmp[mode]
            )
            # append to larger array
            force['error'] = np.append(force['error'], e_frc_tmp)
            model['error'] = np.append(model['error'], e_mod_tmp[name][mode])
            time = np.append(time, t_mod_tmp[name][mode])
            # append daily mean error
            force['daily'] = np.append(force['daily'], np.nanmean(e_frc_tmp))
            model['daily'] = np.append(
                model['daily'], np.nanmean(e_mod_tmp[name][mode])
            )
            daily_time = np.append(
                daily_time, t_sim + datetime.timedelta(hours=12)
            )
        else:
            print('{} simulation for {} did not occur'.format(mode, t_sim))

    return force, model, time, daily_time


def compare_errors(name, mode, start, end, grid_B, figsize=(20, 12)):
    """ compares the model and forcing error at a station
     between dates start and end for a simulation mode."""

    # array of dates for iteration
    numdays = (end - start).days
    dates = [
        start + datetime.timedelta(days=num) for num in range(0, numdays + 1)
    ]
    dates.sort()

    # intiialize figure and arrays
    fig, axs = plt.subplots(3, 1, figsize=figsize)

    force, model, time, daily_time = combine_errors(name, mode, dates, grid_B)
    ttide = shared.get_tides(name, path=paths['tides'])

    # Plotting time series
    ax = axs[0]
    ax.plot(time, force['error'], 'b', label='Forcing error', lw=2)
    ax.plot(time, model['error'], 'g', lw=2, label='Model error')
    ax.set_title(
        'Comparison of {mode} error at'
        ' {name}'.format(mode=mode, name=name)
    )
    ax.set_ylim([-.4, .4])
    hfmt = mdates.DateFormatter('%m/%d %H:%M')

    # Plotting daily mean
    ax = axs[1]
    ax.plot(
        daily_time,
        force['daily'],
        'b',
        label='Forcing daily mean error',
        lw=2
    )
    ax.plot([time[0], time[-1]],
            [np.nanmean(force['error']),
             np.nanmean(force['error'])],
            '--b',
            label='Mean forcing error',
            lw=2)
    ax.plot(
        daily_time, model['daily'], 'g', lw=2, label='Model daily mean error'
    )
    ax.plot([time[0], time[-1]],
            [np.nanmean(model['error']),
             np.nanmean(model['error'])],
            '--g',
            label='Mean model error',
            lw=2)
    ax.set_title(
        'Comparison of {mode} daily mean error at'
        ' {name}'.format(mode=mode, name=name)
    )
    ax.set_ylim([-.4, .4])

    # Plot tides
    ax = axs[2]
    ax.plot(ttide.time, ttide.pred_all, 'k', lw=2, label='tides')
    ax.set_title('Tidal predictions')
    ax.set_ylim([-3, 3])

    # format axes
    hfmt = mdates.DateFormatter('%m/%d %H:%M')
    for ax in axs:
        ax.xaxis.set_major_formatter(hfmt)
        ax.legend(loc=2, ncol=4)
        ax.grid()
        ax.set_xlim([start, end + datetime.timedelta(days=1)])
        ax.set_ylabel('[m]')

    return fig


def model_residual_ssh(grid_T, j, i, tides):
    """Calcuates the model residual at coordinate j, i.

    :arg grid_T: hourly model results file
    :type grid_T: netCDF file

    :arg j: model y-index
    :type j: integer 0<=j<898

    :arg i: model i-index
    :type i: integer 0<=i<398

    :arg tides: tidal predictions at grid point
    :type tides: pandas DataFrame

    :returns: res_mod, t_model, ssh_corr, ssh_mod
    The model residual, model times, model corrected ssh, and
    unmodified model ssh"""
    ssh_mod = grid_T.variables['sossheig'][:, j, i]
    t_s, t_f, t_model = get_model_time_variables(grid_T)
    ssh_corr = shared.correct_model_ssh(ssh_mod, t_model, tides)
    res_mod = compute_residual(ssh_corr, t_model, tides)
    return res_mod, t_model, ssh_corr, ssh_mod


def obs_residual_ssh(name, tides, sdt, edt):
    """Calculates the observed residual at Point Atkinson, Campbell River,
    or Victoria.

    :arg name: Name of station.
    :type name: string

    :arg sdt: The beginning of the date range of interest.
    :type sdt: datetime object

    :arg edt: The end of the date range of interest.
    :type edt: datetime object

    :returns: residual (calculated residual), obs (observed water levels),
              tides (predicted tides)"""
    msl = SITES[name]['msl']
    obs = load_archived_observations(
        name, sdt.strftime('%d-%b-%Y'), edt.strftime('%d-%b-%Y')
    )
    residual = compute_residual(obs.wlev - msl, obs.time, tides)

    return residual, obs


def obs_residual_ssh_NOAA(name, tides, sdt, edt, product='hourly_height'):
    """ Calculates the residual of the observed water levels with respect
    to the predicted tides at a specific NOAA station and for a date range.

    :arg name: Name of station.
    :type name: string

    :arg sdt: The beginning of the date range of interest.
    :type sdt: datetime object

    :arg edt: The end of the date range of interest.
    :type edt: datetime object

    :arg product: defines frequency of observed water levels
    'hourly_height' for hourly or 'water_levels' for 6 min
    :type product: string

    :returns: residual (calculated residual), obs (observed water levels),
              tides (predicted tides)
    """
    sites = SITES
    start_date = sdt.strftime('%d-%b-%Y')
    end_date = edt.strftime('%d-%b-%Y')
    obs = get_NOAA_wlevels(
        sites[name]['stn_no'], start_date, end_date, product=product
    )

    # Prepare to find residual
    residual = compute_residual(obs.wlev, obs.time, tides)

    return residual, obs


def plot_wlev_residual_NOAA(t_orig, elements, figsize=(20, 6)):
    """ Plots the water level residual as calculated by the function
    calculate_wlev_residual_NOAA and has the option to also plot the
    observed water levels and predicted tides over the course of one day.

    :arg t_orig: The beginning of the date range of interest.
    :type t_orig: datetime object

    :arg elements: Elements included in figure.
                   'residual' for residual only and 'all' for residual,
                   observed water level, and predicted tides.
    :type elements: string

    :arg figsize: Figure size (width, height) in inches.
    :type figsize: 2-tuple

    :returns: fig
    """
    tides = shared.get_tides('Neah Bay', path=paths['tides'])
    residual, obs = obs_residual_ssh_NOAA('Neah Bay', tides, t_orig, t_orig)

    # Figure
    fig, ax = plt.subplots(1, 1, figsize=figsize)

    # Plot
    ax.plot(
        obs.time,
        residual,
        colours['residual'],
        label='Observed Residual',
        linewidth=2.5
    )
    if elements == 'all':
        ax.plot(
            obs.time,
            obs.wlev,
            colours['observed'],
            label='Observed Water Level',
            lw=2.5
        )
        ax.plot(
            tides.time,
            tides.pred[tides.time == obs.time],
            colours['predicted'],
            label='Tidal Predictions',
            linewidth=2.5
        )
    if elements == 'residual':
        pass
    ax.set_title(
        'Residual of the observed water levels at'
        ' Neah Bay: {t:%d-%b-%Y}'.format(t=t_orig)
    )
    ax.set_ylim([-3.0, 3.0])
    ax.set_xlabel('[hrs]')
    hfmt = mdates.DateFormatter('%m/%d %H:%M')
    ax.xaxis.set_major_formatter(hfmt)
    ax.legend(loc=2, ncol=3)
    ax.grid()

    return fig


def NeahBay_forcing_anom(textfile, run_date, tide_file):
    """Calculate the Neah Bay forcing anomaly for the data stored in textfile.

    :arg textfile: the textfile containing forecast/observations
    :type textfile: string

    :arg run_date: date of the simulation
    :type run_date: datetime object

    :arg tide_file: path and name for the tide file
    :type tide_file: string

    :returns: dates, surge, forecast_flag
    The dates, surges and a flag specifying if each point was a forecast
    """

    data = _load_surge_data(textfile)
    dates = np.array(data.date.values)
    # Check if today is Jan or Dec
    isDec, isJan = False, False
    if run_date.month == 1:
        isJan = True
    if run_date.month == 12:
        isDec = True
    for i in range(dates.shape[0]):
        dates[i] = _to_datetime(dates[i], run_date.year, isDec, isJan)
    surge, forecast_flag = _calculate_forcing_surge(data, dates, tide_file)
    return dates, surge, forecast_flag


def _load_surge_data(filename):
    """Load the storm surge observations & predictions table from filename
    and return is as a Pandas DataFrame.
    """
    col_names = 'date surge tide obs fcst anom comment'.split()
    data = pd.read_csv(filename, skiprows=3, names=col_names, comment='#')
    data = data.dropna(how='all')
    return data


def _calculate_forcing_surge(data, dates, tide_file):
    """Given Neah Bay water levels stored in data, calculate the sea surface
    height anomaly by removing tides.

    Return the surges in metres,and a flag indicating if each anomaly
    was a forecast.
    """
    # Initialize forecast flag and surge array
    forecast_flag = []
    surge = []
    # Load tides
    ttide, _ = stormtools.load_tidal_predictions(tide_file)
    for d in dates:
        # Convert datetime to string for comparing with times in data
        daystr = d.strftime('%m/%d %HZ')
        tide = ttide.pred_all[ttide.time == d].item()
        obs = data.obs[data.date == daystr].item()
        fcst = data.fcst[data.date == daystr].item()
        if obs == 99.90:
            # Fall daylight savings
            if fcst == 99.90:
                try:
                    # No new forecast value, so persist the previous value
                    surge.append(surge[-1])
                except IndexError:
                    # No values yet, so initialize with zero
                    surge = [0]
                forecast_flag.append(False)
            else:
                surge.append(_feet_to_metres(fcst) - tide)
                forecast_flag.append(True)
        else:
            surge.append(_feet_to_metres(obs) - tide)
            forecast_flag.append(False)
    return surge, forecast_flag


def _feet_to_metres(feet):
    metres = feet * 0.3048
    return metres


def _to_datetime(datestr, year, isDec, isJan):
    """Convert the string given by datestr to a datetime object.

    The year is an argument because the datestr in the NOAA data doesn't
    have a year.
    Times are in UTC/GMT.

    Return a datetime representation of datestr.
    """
    dt = datetime.datetime.strptime(
        '{year}/{datestr}'.format(year=year, datestr=datestr), '%Y/%m/%d %HZ'
    )
    # Dealing with year changes.
    if isDec and dt.month == 1:
        dt = dt.replace(year=year + 1)
    elif isJan and dt.month == 12:
        dt = dt.replace(year=year - 1)
    else:
        dt = dt.replace(year=year)
    dt = dt.replace(tzinfo=pytz.timezone('UTC'))
    return dt


def compute_residual(ssh, t_model, ttide):
    """Compute the difference between modelled ssh and tidal predictions for a
    range of dates.

    Both modelled ssh and tidal predictions use eight tidal constituents.

    :arg ssh: The model sea surface height with tidal constituents corrections
              applied.
    :type ssh: numpy array

    :arg t_model: model output times
    :type t_model: array of datetime objects

    :arg ttide: The tidal predictions.
    :type ttide: DateFrame object with columns time, pred_all and pred_8

    :returns: numpy array for residual (res).
    """

    # interpolate tides to model time
    tides_interp = shared.interp_to_model_time(
        t_model, ttide.pred_all, ttide.time
    )

    res = ssh - tides_interp

    return res


def dateparse_NOAA(s):
    """Parse the dates from the NOAA files."""

    unaware = datetime.datetime.strptime(s, '%Y-%m-%d %H:%M')
    aware = unaware.replace(tzinfo=tz.tzutc())

    return aware


def get_NOAA_wlevels(station_no, start_date, end_date, product='water_level'):
    """Retrieves recent NOAA water levels from a station in a given date range.

    NOAA water levels are at 6 minute intervals and are relative to
    mean sea level.
    See: http://tidesandcurrents.noaa.gov/stations.html?type=Water+Levels.

    :arg station_no: NOAA station number.
    :type station_no: int

    :arg start_date: The start of the date range; e.g. 01-Jan-2014.
    :type start_date: str

    :arg end_date: The end of the date range; e.g. 02-Jan-2014.
    :type end_date: str

    :arg product: Defines which NOAA product to use. Options are 'water_level'
                  for recent data, 'hourly_height' for archived
    :type product: str

    :returns: DataFrame object (obs) with time and wlev columns,
              among others that are irrelevant.
    """

    # Time range
    st_ar = arrow.Arrow.strptime(start_date, '%d-%b-%Y')
    end_ar = arrow.Arrow.strptime(end_date, '%d-%b-%Y')

    base_url = (
        'http://tidesandcurrents.noaa.gov/api/datagetter'
        '?product={}&application=NOS.COOPS.TAC.WL'.format(product)
    )
    params = {
        'begin_date': st_ar.format('YYYYMMDD'),
        'end_date': end_ar.format('YYYYMMDD'),
        'datum': 'MSL',
        'station': str(station_no),
        'time_zone': 'GMT',
        'units': 'metric',
        'format': 'csv',
    }
    response = requests.get(base_url, params=params)

    fakefile = io.StringIO(response.text)
    try:
        obs = pd.read_csv(
            fakefile, parse_dates=[0], date_parser=dateparse_NOAA
        )
    except ValueError:
        data = {'Date Time': st_ar.datetime, ' Water Level': float('NaN')}
        obs = pd.DataFrame(data=data, index=[0])
    obs = obs.rename(columns={'Date Time': 'time', ' Water Level': 'wlev'})
    return obs


def load_archived_observations(name, start_date, end_date):
    """
    Loads tidal observations from the DFO archive website.
    Note: only archived observations can be loaded. This usually means
    at least one month old. If data is not available, a DataFrame with
    one NaN recording is returned.

    :arg name: a string representing the location for observations
    :type name: a string from the following - Point Atkinson, Victoria,
     Campbell River

    :arg start_date: a string representing the starting date of the
     observations.
    :type start_date: string in format %d-%b-%Y

    :arg end: a string representing the end date of the observations.
    :type end: string in format %d-%b-%Y

    :returns: wlev_meas: a dict object with the water level measurements
     reference to Chart Datum. Columns are time and wlev. Time is in UTC.
    """

    station_no = SITES[name]['stn_no']
    base_url = 'http://www.meds-sdmm.dfo-mpo.gc.ca/isdm-gdsi/twl-mne/inventory-inventaire/'
    form_handler = (
        'data-donnees-eng.asp?user=isdm-gdsi&region=PAC&tst=1&no=' +
        str(station_no)
    )
    sitedata = {
        'start_period': start_date,
        'end_period': end_date,
        'resolution': 'h',
        'time_zone': 'l',
    }
    data_provider = (
        'download-telecharger.asp'
        '?File=E:%5Ciusr_tmpfiles%5CTWL%5C' + str(station_no) + '-' +
        start_date + '_slev.csv'
        '&Name=' + str(station_no) + '-' + start_date + '_slev.csv'
    )
    # Go get the data from the DFO site
    with requests.Session() as s:
        s.post(base_url + form_handler, data=sitedata)
        r = s.get(base_url + data_provider)
    # Write the data to a fake file
    fakefile = io.StringIO(r.text)
    # Read the fake file
    try:
        wlev_meas = pd.read_csv(
            fakefile,
            skiprows=7,
            parse_dates=[0],
            date_parser=dateparse_archive_obs
        )
    except pd.parser.CParserError:
        data = {
            'Obs_date': datetime.datetime.strptime(start_date, '%d-%b-%Y'),
            'SLEV(metres)': float('NaN')
        }
        wlev_meas = pd.DataFrame(data=data, index=[0])

    wlev_meas = wlev_meas.rename(
        columns={
            'Obs_date': 'time',
            'SLEV(metres)': 'wlev'
        }
    )

    return wlev_meas


def dateparse_archive_obs(s):
    """Function to make datetime object aware of time zone
    e.g. date_parser=dateParserMeasured('2014/05/31 11:42')

    :arg s: string of date and time
    :type s: str

    :returns: datetime object that is timezone aware
    """
    PST_tz = tz.tzoffset("PST", -28800)
    # Convert the string to a datetime object
    unaware = datetime.datetime.strptime(s, "%Y/%m/%d %H:%M")
    # Add in the local time zone (Canada/Pacific)
    aware = unaware.replace(tzinfo=PST_tz)
    # Convert to UTC
    return aware.astimezone(tz.tzutc())


def get_model_time_variables(grid_T):
    """Return start time, end time, and the time counter values from a
    NEMO tracer results dataset.

    :arg grid_T: Tracer results dataset from NEMO.
    :type grid_T: :py:class:`netCDF4.Dataset`

    :returns: dataset start time, dataset end time,
              and array of output times all as datetime objects.
    """
    time = nc_tools.timestamp(
        grid_T, range(grid_T.variables['time_counter'].size)
    )
    time = np.array([t.datetime for t in time])
    return time[0], time[-1], time
