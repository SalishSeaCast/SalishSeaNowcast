#  Copyright 2013 – present The Salish Sea MEOPAR contributors
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
"""A collection of Python functions to produce model results visualization
figures for analysis and model evaluation of nowcast, forecast, and
forecast2 runs.
"""
import datetime
import glob
import os

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import netCDF4 as nc
import numpy as np
from salishsea_tools import nc_tools, tidetools, geo_tools

from nowcast import figures

# Paths for model results
paths = {
    "nowcast": "/results/SalishSea/nowcast/",
    "forecast": "/results/SalishSea/forecast/",
    "forecast2": "/results/SalishSea/forecast2/",
}

# Colours for plots
colours = {
    "nowcast": "DodgerBlue",
    "forecast": "ForestGreen",
    "forecast2": "MediumVioletRed",
    "observed": "Indigo",
    "predicted": "ForestGreen",
    "model": "blue",
    "residual": "DimGray",
}


def get_filenames(t_orig, t_final, period, grid, model_path):
    """Returns a list with the filenames for all files over the
    defined period of time and sorted in chronological order.

    :arg t_orig: The beginning of the date range of interest.
    :type t_orig: datetime object

    :arg t_final: The end of the date range of interest.
    :type t_final: datetime object

    :arg period: Time interval of model results (eg. 1h or 1d).
    :type period: string

    :arg grid: Type of model results (eg. grid_T, grid_U, etc).
    :type grid: string

    :arg model_path: Defines the full path for model results
                     (eg. '/results/SalishSea/nowcast/')
    :type model_path: string

    :returns: files, a list of filenames
    """

    numdays = (t_final - t_orig).days
    dates = [t_orig + datetime.timedelta(days=num) for num in range(0, numdays + 1)]
    dates.sort()

    allfiles = glob.glob(model_path + "*/SalishSea_" + period + "*_" + grid + ".nc")
    sdt = dates[0].strftime("%Y%m%d")
    edt = dates[-1].strftime("%Y%m%d")
    sstr = f"SalishSea_{period}_{sdt}_{sdt}_{grid}.nc"
    estr = f"SalishSea_{period}_{edt}_{edt}_{grid}.nc"

    files = []
    for filename in allfiles:
        if os.path.basename(filename) >= sstr:
            if os.path.basename(filename) <= estr:
                files.append(filename)

    files.sort(key=os.path.basename)

    return files


def get_filenames_15(t_orig, t_final, station, model_path):
    """Returns a list with the filenames for all files over the
    defined period of time and sorted in chronological order for
    the gridded quarter-hourly data.

    :arg t_orig: The beginning of the date range of interest.
    :type t_orig: datetime object

    :arg t_final: The end of the date range of interest.
    :type t_final: datetime object

    :arg station: The VENUS station for which data files are required.
        (east or central)
    :type station: string

    :arg model_path: Defines the path used (eg. nowcast)
    :type model_path: string

    :returns: files, a list of filenames
    """

    numdays = (t_final - t_orig).days
    dates = [t_orig + datetime.timedelta(days=num) for num in range(0, numdays + 1)]
    dates.sort()

    files = []
    for i in dates:
        sdt = i.strftime("%d%b%y").lower()
        filename = f"{model_path}{sdt}/VENUS_{station}_gridded.nc"
        files.append(filename)

    return files


def combine_files(files, var, kss, jss, iss):
    """Returns the value of the variable entered over
    multiple files covering a certain period of time at
    a set of grid coordinates.

    :arg files: Multiple result files in chronological order.
    :type files: list

    :arg var: Name of variable (sossheig = sea surface height,
                      vosaline = salinity, votemper = temperature,
                      vozocrtx = Velocity U-component,
                      vomecrty = Velocity V-component).
    :type var: string

    :arg kss: list of model depth levels (<=39)
    'None' if depth is not applicable (example sea surface height).
    :type kss: integer or string

    :arg jss: list of (y) indices of location (<=897).
    :type jss:  list of integers

    :arg iss: list of (x) indices of location (<=397).
    :type iss: list of integers

    :returns: var_ary, time - array of model results and time.
    """

    time = np.array([])
    var_list = []

    for f in files:
        with nc.Dataset(f) as G:
            if kss == "None":
                try:  # for variavles with no depht like ssh
                    var_tmp = G.variables[var][..., jss, iss]
                except IndexError:  # for variables with depth
                    var_tmp = G.variables[var][:, :, jss, iss]
            else:
                var_tmp = G.variables[var][..., kss, jss, iss]

            var_list.append(var_tmp)
            t = nc_tools.timestamp(G, np.arange(var_tmp.shape[0]))
            try:
                for ind in range(len(t)):
                    t[ind] = t[ind].datetime
            except TypeError:
                t = t.datetime
            time = np.append(time, t)

    var_ary = np.concatenate(var_list, axis=0)
    return var_ary, time


def plot_files(ax, grid_B, files, var, depth, t_orig, t_final, name, label, colour):
    """Plots values of  variable over multiple files covering
    a certain period of time.

    :arg ax: The axis where the variable is plotted.
    :type ax: axis object

    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg files: Multiple result files in chronological order.
    :type files: list

    :arg var: Name of variable (sossheig = sea surface height,
                      vosaline = salinity, votemper = temperature,
                      vozocrtx = Velocity U-component,
                      vomecrty = Velocity V-component).
    :type var: string

    :arg depth: Depth of model results ('None' if var=sossheig).
    :type depth: integer or string

    :arg t_orig: The beginning of the date range of interest.
    :type t_orig: datetime object

    :arg t_final: The end of the date range of interest.
    :type t_final: datetime object

    :arg name: The name of the station.
    :type name: string

    :arg label: Label for plot line.
    :type label: string

    :arg colour: Colour of plot lines.
    :type colour: string

    :returns: matplotlib figure object instance (fig) and axis object (ax).
    """

    # Stations information
    lat = figures.SITES[name]["lat"]
    lon = figures.SITES[name]["lon"]

    # Bathymetry
    bathy, X, Y = tidetools.get_bathy_data(grid_B)

    # Get index
    j, i = geo_tools.find_closest_model_point(lon, lat, X, Y, land_mask=bathy.mask)

    # Call function
    var_ary, time = combine_files(files, var, depth, j, i)

    # Plot
    ax.plot(time, var_ary, label=label, color=colour, linewidth=2.5)

    # Figure format
    ax_start = t_orig
    ax_end = t_final + datetime.timedelta(days=1)
    ax.set_xlim(ax_start, ax_end)
    hfmt = mdates.DateFormatter("%m/%d %H:%M")
    ax.xaxis.set_major_formatter(hfmt)

    return ax


def compare_ssh_tides(
    grid_B, files, t_orig, t_final, name, PST=0, MSL=0, figsize=(20, 6)
):
    """
    :arg grid_B: Bathymetry dataset for the Salish Sea NEMO model.
    :type grid_B: :class:`netCDF4.Dataset`

    :arg files: Multiple result files in chronological order.
    :type files: list

    :arg t_orig: The beginning of the date range of interest.
    :type t_orig: datetime object

    :arg t_final: The end of the date range of interest.
    :type t_final: datetime object

    :arg name: Name of station.
    :type name: string

    :arg PST: Specifies if plot should be presented in PST.
              1 = plot in PST, 0 = plot in UTC.
    :type PST: 0 or 1

    :arg MSL: Specifies if the plot should be centred about mean sea level.
              1=centre about MSL, 0=centre about 0.
    :type MSL: 0 or 1

    :arg figsize: Figure size (width, height) in inches.
    :type figsize: 2-tuple

    :returns: matplotlib figure object instance (fig).
    """

    # Figure
    fig, ax = plt.subplots(1, 1, figsize=figsize)

    # Model
    ax = plot_files(
        ax,
        grid_B,
        files,
        "sossheig",
        "None",
        t_orig,
        t_final,
        name,
        "Model",
        colours["model"],
    )
    # Tides
    figures.plot_tides(ax, name, PST, MSL, color=colours["predicted"])

    # Figure format
    ax.set_title(
        f"Modelled Sea Surface Height versus Predicted Tides at {name}: "
        f"{t_orig:%d-%b-%Y} to {t_final:%d-%b-%Y}"
    )
    ax.set_ylim([-3.0, 3.0])
    ax.set_xlabel("[hrs]")
    ax.legend(loc=2, ncol=2)
    ax.grid()

    return fig


def create_path(mode, t_orig, file_part):
    """Creates a path to a file associated with a simulation for date t_orig.
    E.g.
    create_path('nowcast',datatime.datetime(2015,1,1),'SalishSea_1h*grid_T.nc')
    gives
    /data/dlatorne/MEOPAR/SalishSea/nowcast/01jan15/SalishSea_1h_20150101_20150101_grid_T.nc

    :arg mode: Mode of results - nowcast, forecast, forecast2.
    :type mode: string

    :arg t_orig: The simulation start date.
    :type t_orig: datetime object


    :arg file_part: Identifier for type of file.
    E.g. SalishSea_1h*grid_T.nc or ssh*.txt
    :type grid: string

    :returns: filename, run_date
    filename is the path of the file or empty list if the file does not exist.
    run_date is a datetime object that represents the date the simulation ran
    """

    run_date = t_orig

    if mode == "nowcast":
        results_home = paths["nowcast"]
    elif mode == "forecast":
        results_home = paths["forecast"]
        run_date = run_date + datetime.timedelta(days=-1)
    elif mode == "forecast2":
        results_home = paths["forecast2"]
        run_date = run_date + datetime.timedelta(days=-2)

    results_dir = os.path.join(results_home, run_date.strftime("%d%b%y").lower())

    filename = glob.glob(os.path.join(results_dir, file_part))

    try:
        filename = filename[-1]
    except IndexError:
        pass

    return filename, run_date


def truncate_data(data, time, sdt, edt):
    """Truncates data for a desired time range: sdt <= time <= edt
    data and time must be numpy arrays.
    sdt, edt, and times in time must all have a timezone or all be naive.

    :arg data: the data to be truncated
    :type data: numpy array

    :arg time: array of times associated with data
    :type time: numpy array

    :arg sdt: the start time of the tuncation
    :type sdt: datetime object

    :arg edt: the end time of the truncation
    :type edt: datetime object

    :returns: data_trun, time_trun, the truncated data and time arrays
    """

    inds = np.where(np.logical_and(time <= edt, time >= sdt))

    return data[inds], time[inds]


def verified_runs(t_orig):
    """Compiles a list of run types (nowcast, forecast, and/or forecast 2)
    that have been verified as complete by checking if their corresponding
    .nc files for that day (generated by create_path) exist.

    :arg t_orig:
    :type t_orig: datetime object

    :returns: runs_list, list strings representing the runs that completed
    """

    runs_list = []
    for mode in ["nowcast", "forecast", "forecast2"]:
        files, run_date = create_path(mode, t_orig, "SalishSea*grid_T.nc")
        if files:
            runs_list.append(mode)

    return runs_list


def calculate_error(res_mod, time_mod, res_obs, time_obs):
    """Calculates the model or forcing residual error.

    :arg res_mod: Residual for model ssh or NB surge data.
    :type res_mod: numpy array

    :arg time_mod: Time of model output.
    :type time_mod: numpy array

    :arg res_obs: Observed residual (archived or at Neah Bay)
    :type res_obs: numpy array

    :arg time_obs: Time corresponding to observed residual.
    :type time_obs: numpy array

    :return: error
    """

    res_obs_interp = figures.interp_to_model_time(time_mod, res_obs, time_obs)
    error = res_mod - res_obs_interp

    return error


def depth_average(var, depths, depth_axis):
    """Average var over depth using the trapezoid rule.
    The var should be masked in order to apply this function.
    The depth is calcluated based on masking.
    If var is not masked then the maximum depth of the depths array is used.

    :arg var: variable to average
    :type var: masked numpy array

    :arg depths: the depths associated with var
    :type depths: numpy array

    :arg depth_axis: The axis in var associated with depth
    :type depth_axis: int

    :returns: avg, the depth averaged var.

    """
    # Make sure depths is an array and not an netcdf variable.
    de = np.array(depths)
    # Integrate, the easy part
    integral = np.trapz(var, x=de, axis=depth_axis)
    # Find depth for averaging
    # Need to expand the depths array to same shape as the integrand.
    # This is really awkward..
    for n in np.arange(var.ndim - 1):
        de = de[:, np.newaxis]
    roll = np.rollaxis(var, depth_axis)
    expanded_depths = de + np.zeros(roll.shape)
    expanded_depths = np.rollaxis(expanded_depths, 0, depth_axis + 1)

    # Apply variable mask to depth masks
    mask = np.ma.getmask(var)
    depth_masked = np.ma.array(expanded_depths, mask=mask)

    # Calculate depth of water column
    max_depths = np.ma.max(depth_masked, axis=depth_axis)
    surface_depths = depth_masked.take(0, axis=depth_axis)
    total_depth = max_depths - surface_depths

    # Divide integral by total depth
    average = integral / total_depth

    return average


def depth_average_mask(var, e3, mask, depth_axis):
    """Calculate depth average using the NEMO vertical scale factors and mask."""
    # If depth_axis is not 0, give e3 and mask a time dimension
    if depth_axis != 0:
        e3 = np.expand_dims(e3, 0)
        mask = np.expand_dims(mask, 0)

    integral = np.sum(var * e3 * mask, axis=depth_axis)
    total_depth = np.sum(e3 * mask, axis=depth_axis)
    avg = integral / total_depth
    avg = np.ma.masked_invalid(avg)
    return avg
