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


"""A collection of Python functions to produce model residual calculations and
visualizations.
"""
import datetime

from dateutil import tz

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import netCDF4 as nc
import numpy as np
import pandas as pd

from salishsea_tools import tidetools

from nowcast import (
    figures,
    analyze,
)

# Module constants

paths = {'nowcast': '/results/SalishSea/nowcast/',
         'forecast': '/results/SalishSea/forecast/',
         'forecast2': '/results/SalishSea/forecast2/'}

colours = {'nowcast': 'DodgerBlue',
           'forecast': 'ForestGreen',
           'forecast2': 'MediumVioletRed',
           'observed': 'Indigo',
           'predicted': 'ForestGreen',
           'model': 'blue',
           'residual': 'DimGray'}

# Module functions


def calculate_residual(ssh, time_ssh, tides, time_tides):
    """ Calculates the residual of the model sea surface height or
    observed water levels with respect to the predicted tides.

    :arg ssh: Sea surface height (observed or modelled).
    :type ssh: numpy array

    :arg time_ssh: Time component for sea surface height (observed or modelled)
    :type time_ssh: numpy array

    :arg tides: Predicted tides.
    :type tides: dataFrame object

    :arg time_tides: Time component for predicted tides.
    :type time_tides: dataFrame object

    :returns: res, the residual
    """

    tides_interp = figures.interp_to_model_time(time_ssh, tides, time_tides)
    res = ssh - tides_interp

    return res


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
    start_date = t_orig.strftime('%d-%b-%Y')
    end_date = start_date
    stn_no = figures.SITES['Neah Bay']['stn_no']
    obs = figures.get_NOAA_wlevels(stn_no, start_date, end_date)
    tides = figures.get_NOAA_tides(stn_no, start_date, end_date)
    res_obs = calculate_residual(obs.wlev, obs.time, tides.pred, tides.time)
    # truncate and plot
    res_obs_trun, time_trun = analyze.truncate_data(
        np.array(res_obs), np.array(obs.time), sdt, edt)
    ax.plot(time_trun, res_obs_trun, colours['observed'],
            label='observed', lw=2.5)

    # plot forcing for each simulation
    for mode in runs_list:
        filename_NB, run_date = analyze.create_path(mode, t_orig, 'ssh*.txt')
        if filename_NB:
            data = _load_surge_data(filename_NB)
            surge, dates = _retrieve_surge(data, run_date)
            surge_t, dates_t = analyze.truncate_data(np.array(surge),
                                                     np.array(dates), sdt, edt)
            ax.plot(dates_t, surge_t, label=mode, lw=2.5, color=colours[mode])
    ax.set_title('Comparison of observed and forced sea surface'
                 ' height residuals at Neah Bay:'
                 '{t_forcing:%d-%b-%Y}'.format(t_forcing=t_orig))


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
        lat = figures.SITES[name]['lat']
        lon = figures.SITES[name]['lon']
        msl = figures.SITES[name]['msl']
        j, i = tidetools.find_closest_model_point(
            lon, lat, X, Y, bathy, allow_land=False)
        ttide = figures.get_tides(name)
        wlev_meas = figures.load_archived_observations(
            name, t_orig_obs.strftime('%d-%b-%Y'),
            t_final_obs.strftime('%d-%b-%Y'))
        res_obs = calculate_residual(
            wlev_meas.wlev, wlev_meas.time,
            ttide.pred_all + msl, ttide.time)
        # truncate and plot
        res_obs_trun, time_obs_trun = analyze.truncate_data(
            np.array(res_obs), np.array(wlev_meas.time), sdt, edt)
        ax.plot(time_obs_trun, res_obs_trun, c=colours['observed'],
                lw=2.5, label='observed')

        for mode in runs_list:
            filename, run_date = analyze.create_path(
                mode, t_orig, 'SalishSea_1h_*_grid_T.nc')
            grid_T = nc.Dataset(filename)
            ssh_loc = grid_T.variables['sossheig'][:, j, i]
            t_s, t_f, t_model = figures.get_model_time_variables(grid_T)
            res_mod = calculate_residual(
                ssh_loc, t_model, ttide.pred_8, ttide.time)
            # truncate and plot
            res_mod_trun, t_mod_trun = analyze.truncate_data(
                res_mod, t_model, sdt, edt)
            ax.plot(t_mod_trun, res_mod_trun, label=mode,
                    c=colours[mode], lw=2.5)

        ax.set_title('Comparison of modelled sea surface height residuals at'
                     '{station}: {t:%d-%b-%Y}'.format(station=name, t=t_orig))


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
        lat = figures.SITES[name]['lat']
        lon = figures.SITES[name]['lon']
        msl = figures.SITES[name]['msl']
        j, i = tidetools.find_closest_model_point(
            lon, lat, X, Y, bathy, allow_land=False)
        ttide = figures.get_tides(name)
        wlev_meas = figures.load_archived_observations(
            name, t_orig_obs.strftime('%d-%b-%Y'),
            t_final_obs.strftime('%d-%b-%Y'))
        res_obs = calculate_residual(wlev_meas.wlev, wlev_meas.time,
                                     ttide.pred_all + msl, ttide.time)

        for mode in runs_list:
            filename, run_date = analyze.create_path(
                mode, t_orig, 'SalishSea_1h_*_grid_T.nc')
            grid_T = nc.Dataset(filename)
            ssh_loc = grid_T.variables['sossheig'][:, j, i]
            t_s, t_f, t_model = figures.get_model_time_variables(grid_T)
            res_mod = calculate_residual(ssh_loc, t_model,
                                         ttide.pred_8, ttide.time)
            # truncate
            res_mod_trun, t_mod_trun = analyze.truncate_data(
                res_mod, t_model, sdt, edt)
            error_mod = analyze.calculate_error(res_mod_trun, t_mod_trun,
                                                res_obs, wlev_meas.time)
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
    start_date = t_orig.strftime('%d-%b-%Y')
    end_date = start_date
    stn_no = figures.SITES['Neah Bay']['stn_no']
    obs = figures.get_NOAA_wlevels(stn_no, start_date, end_date)
    tides = figures.get_NOAA_tides(stn_no, start_date, end_date)
    res_obs_NB = calculate_residual(obs.wlev, obs.time, tides.pred, tides.time)

    # calculate forcing error
    error_frc_dict = {}
    t_frc_dict = {}
    for mode in runs_list:
        filename_NB, run_date = analyze.create_path(mode, t_orig, 'ssh*.txt')
        if filename_NB:
            data = _load_surge_data(filename_NB)
            surge, dates = _retrieve_surge(data, run_date)
            surge_t, dates_t = analyze.truncate_data(
                np.array(surge), np.array(dates), sdt, edt)
            error_frc = analyze.calculate_error(
                surge_t, dates_t, res_obs_NB, obs.time)
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
        names, runs_list, grid_B, t_orig)

    for ax, name in zip(axs, names):
        ax.set_title('Comparison of modelled residual errors at {station}:'
                     ' {t:%d-%b-%Y}'.format(station=name, t=t_orig))
        for mode in runs_list:
            ax.plot(t_mod_dict[name][mode], error_mod_dict[name][mode],
                    label=mode, c=colours[mode], lw=2.5)


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
        ax.plot(t_frc_dict[mode], error_frc_dict[mode],
                label=mode, c=colours[mode], lw=2.5)
        ax.set_title('Comparison of observed and forced residual errors at '
                     'Neah Bay: {t_forcing:%d-%b-%Y}'.format(t_forcing=t_orig))


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

    model = {'error': np.array([]),
             'daily': np.array([])}
    force = {'error': np.array([]),
             'daily': np.array([])}
    time = np.array([])
    daily_time = np.array([])

    for t_sim in dates:
        # check if the run happened
        if mode in analyze.verified_runs(t_sim):
            # retrieve forcing and model error
            e_frc_tmp, t_frc_tmp = get_error_forcing([mode], t_sim)
            e_mod_tmp, t_mod_tmp = get_error_model([name], [mode],
                                                   grid_B, t_sim)
            e_frc_tmp = figures.interp_to_model_time(
                t_mod_tmp[name][mode], e_frc_tmp[mode], t_frc_tmp[mode])
            # append to larger array
            force['error'] = np.append(force['error'], e_frc_tmp)
            model['error'] = np.append(model['error'], e_mod_tmp[name][mode])
            time = np.append(time, t_mod_tmp[name][mode])
            # append daily mean error
            force['daily'] = np.append(force['daily'], np.mean(e_frc_tmp))
            model['daily'] = np.append(model['daily'],
                                       np.mean(e_mod_tmp[name][mode]))
            daily_time = np.append(daily_time,
                                   t_sim + datetime.timedelta(hours=12))
        else:
            print('{} simulation for {} did not occur'.format(mode, t_sim))

    return force, model, time, daily_time


def compare_errors(name, mode, start, end, grid_B, figsize=(20, 12)):
    """ compares the model and forcing error at a station
     between dates start and end for a simulation mode."""

    # array of dates for iteration
    numdays = (end-start).days
    dates = [start + datetime.timedelta(days=num)
             for num in range(0, numdays+1)]
    dates.sort()

    # intiialize figure and arrays
    fig, axs = plt.subplots(3, 1, figsize=figsize)

    force, model, time, daily_time = combine_errors(name, mode, dates, grid_B)
    ttide = figures.get_tides(name)

    # Plotting time series
    ax = axs[0]
    ax.plot(time, force['error'], 'b', label='Forcing error', lw=2)
    ax.plot(time, model['error'], 'g', lw=2, label='Model error')
    ax.set_title('Comparison of {mode} error at'
                 ' {name}'.format(mode=mode, name=name))
    ax.set_ylim([-.4, .4])
    hfmt = mdates.DateFormatter('%m/%d %H:%M')

    # Plotting daily mean
    ax = axs[1]
    ax.plot(daily_time, force['daily'], 'b',
            label='Forcing daily mean error', lw=2)
    ax.plot([time[0], time[-1]],
            [np.mean(force['error']), np.mean(force['error'])],
            '--b', label='Mean forcing error', lw=2)
    ax.plot(daily_time, model['daily'], 'g', lw=2,
            label='Model daily mean error')
    ax.plot([time[0], time[-1]],
            [np.mean(model['error']), np.mean(model['error'])],
            '--g', label='Mean model error', lw=2)
    ax.set_title('Comparison of {mode} daily mean error at'
                 ' {name}'.format(mode=mode, name=name))
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
        ax.set_xlim([start, end+datetime.timedelta(days=1)])
        ax.set_ylabel('[m]')

    return fig


def _feet_to_metres(feet):
    """ Converts feet to metres.

    :returns: metres
    """

    metres = feet*0.3048
    return metres


def _load_surge_data(filename_NB):
    """Loads the textfile with surge predictions for Neah Bay.

    :arg filename_NB: Path to file of predicted water levels at Neah Bay.
    :type filename_NB: string

    :returns: data (data structure)
    """

    # Loading the data from that text file.
    data = pd.read_csv(filename_NB, skiprows=3,
                       names=['date', 'surge', 'tide', 'obs',
                              'fcst', 'anom', 'comment'], comment='#')
    # Drop rows with all Nans
    data = data.dropna(how='all')

    return data


def _to_datetime(datestr, year, isDec, isJan):
    """ Converts the string given by datestr to a datetime object.
    The year is an argument because the datestr in the NOAA data
    doesn't have a year. Times are in UTC/GMT.

    :arg datestr: Date of data.
    :type datestr: datetime object

    :arg year: Year of data.
    :type year: datetime object

    :arg isDec: True if run date was December.
    :type isDec: Boolean

    :arg isJan: True if run date was January.
    :type isJan: Boolean

    :returns: dt (datetime representation of datestr)
    """

    dt = datetime.datetime.strptime(datestr, '%m/%d %HZ')
    # Dealing with year changes.
    if isDec and dt.month == 1:
        dt = dt.replace(year=year+1)
    elif isJan and dt.month == 12:
        dt = dt.replace(year=year-1)
    else:
        dt = dt.replace(year=year)
    dt = dt.replace(tzinfo=tz.tzutc())

    return dt


def _retrieve_surge(data, run_date):
    """ Gathers the surge information a forcing file from on run_date.

    :arg data: Surge predictions data.
    :type data: data structure

    :arg run_date: Simulation run date.
    :type run_date: datetime object

    :returns: surges (meteres), times (array with time_counter)
    """

    surge = []
    times = []
    isDec, isJan = False, False
    if run_date.month == 1:
        isJan = True
    if run_date.month == 12:
        isDec = True
    # Convert datetime to string for comparing with times in data
    for d in data.date:

        dt = _to_datetime(d, run_date.year, isDec, isJan)
        times.append(dt)
        daystr = dt.strftime('%m/%d %HZ')
        tide = data.tide[data.date == daystr].item()
        obs = data.obs[data.date == daystr].item()
        fcst = data.fcst[data.date == daystr].item()
        if obs == 99.90:
            # Fall daylight savings
            if fcst == 99.90:
                # If surge is empty, just append 0
                if not surge:
                    surge.append(0)
                else:
                    # Otherwise append previous value
                    surge.append(surge[-1])
            else:
                surge.append(_feet_to_metres(fcst-tide))
        else:
            surge.append(_feet_to_metres(obs-tide))

    return surge, times


def calculate_wlev_residual_NOAA(name, t_orig):
    """ Calculates the residual of the observed water levels with respect
    to the predicted tides at a specific station and for a specific date.

    :arg name: Name of station.
    :type name: string

    :arg t_orig: The beginning of the date range of interest.
    :type t_orig: datetime object

    :returns: residual (calculated residual), obs (observed water levels),
              tides (predicted tides)
    """
    stations = {'Cherry Point': 9449424,
                'Neah Bay': 9443090,
                'Friday Harbor': 9449880}
    start_date = t_orig.strftime('%d-%b-%Y')
    end_date = start_date
    obs = figures.get_NOAA_wlevels(stations[name], start_date, end_date)
    tides = figures.get_NOAA_tides(stations[name], start_date, end_date)

    # Prepare to find residual
    residual = np.zeros(len(obs.time))

    # Residual and time check
    for i in np.arange(0, len(obs.time)):
        if any(tides.time == obs.time[i]):
            residual[i] = obs.wlev[i] - tides.pred[tides.time == obs.time[i]]
        else:
            residual[i] = float('Nan')

    return residual, obs, tides


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

    residual, obs, tides = calculate_wlev_residual_NOAA('Neah Bay', t_orig)

    # Figure
    fig, ax = plt.subplots(1, 1, figsize=figsize)

    # Plot
    ax.plot(obs.time, residual, colours['residual'], label='Observed Residual',
            linewidth=2.5)
    if elements == 'all':
        ax.plot(obs.time, obs.wlev,
                colours['observed'], label='Observed Water Level', lw=2.5)
        ax.plot(tides.time, tides.pred[tides.time == obs.time],
                colours['predicted'], label='Tidal Predictions', linewidth=2.5)
    if elements == 'residual':
        pass
    ax.set_title('Residual of the observed water levels at'
                 ' Neah Bay: {t:%d-%b-%Y}'.format(t=t_orig))
    ax.set_ylim([-3.0, 3.0])
    ax.set_xlabel('[hrs]')
    hfmt = mdates.DateFormatter('%m/%d %H:%M')
    ax.xaxis.set_major_formatter(hfmt)
    ax.legend(loc=2, ncol=3)
    ax.grid()

    return fig
