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
"""A collection of Python functions to produce comparisons between with the
salinity of British Columbia ferry observations data and the model results with
visualization figures for analysis of daily nowcast runs.
"""
import datetime
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.io as sio
from salishsea_tools import geo_tools, viz_tools, teos_tools
from salishsea_tools.places import PLACES

from nowcast.figures import research_VENUS

# Font format
title_font = {
    "fontname": "Bitstream Vera Sans",
    "size": "15",
    "color": "black",
    "weight": "medium",
}
axis_font = {"fontname": "Bitstream Vera Sans", "size": "13"}

FERRY_ROUTES = {
    "HB_DB": {
        "start": {"terminal": "Horseshoe Bay", "hour": 2, "minute": 0},
        "end": {"terminal": "Departure Bay", "hour": 4, "minute": 30},
    },
    "TW_DP": {
        "start": {"terminal": "Tsawwassen", "hour": 1, "minute": 0},
        "end": {"terminal": "Duke Pt.", "hour": 3, "minute": 45},
    },
    "TW_SB": {
        "start": {"terminal": "Tsawwassen", "hour": 2, "minute": 0},
        "end": {"terminal": "Swartz Bay", "hour": 4, "minute": 0},
    },
}


def salinity_ferry_route(
    ferry_data_dir, grid_T_hr, bathy, route_name, dmy, figsize=(20, 7.5)
):
    """Plot daily salinity comparisons between ferry observations and model
    results as well as ferry route with model salinity distribution.

    :arg str ferry_data_dir: storage file location for ONC ferry data.

    :arg grid_T_hr: Hourly tracer results dataset from NEMO.
    :type grid_T_hr: :class:`netCDF4.Dataset

    :arg bathy: model bathymetry
    :type bathy: numpy array

    :arg str route_name: route name of these three ferry routes respectively

    :arg str dmy: date in form ddmonyy

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :returns: matplotlib figure object instance (fig).
    """
    # Grid region to plot
    si, ei = 200, 610
    sj, ej = 20, 370
    lons = grid_T_hr.variables["nav_lon"][si:ei, sj:ej]
    lats = grid_T_hr.variables["nav_lat"][si:ei, sj:ej]
    # Salinity calculated by NEMO and observed by ONC ferry package
    model_depth_level = 1  # 1.5 m
    ## TODO: model time step for salinity contour map should be calculated from
    ##       ferry route time
    model_time_step = 3  # 02:30 UTC
    sal_hr = grid_T_hr.variables["vosaline"]
    ## TODO: Use mesh mask instead of 0 for masking
    sal_masked = np.ma.masked_values(
        sal_hr[model_time_step, model_depth_level, si:ei, sj:ej], 0
    )
    sal_t = teos_tools.psu_teos(sal_masked)
    sal_obs = ferry_salinity(ferry_data_dir, route_name, dmy)
    nemo_a, nemo_b = nemo_sal_route(grid_T_hr, bathy, route_name, sal_obs)

    fig, axs = plt.subplots(1, 2, figsize=figsize)
    axs[1].set_facecolor("burlywood")
    viz_tools.set_aspect(axs[1], coords="map", lats=lats)
    cmap = plt.get_cmap("plasma")
    axs[1].set_xlim(-124.5, -122.5)
    axs[1].set_ylim(48.3, 49.6)

    # Plot model salinity
    mesh = axs[1].contourf(lons, lats, sal_t, 20, cmap=cmap)
    cbar = plt.colorbar(mesh, ax=axs[1])
    cbar.ax.axes.tick_params(labelcolor="w")
    cbar.set_label("Absolute Salinity [g/kg]", color="white", **axis_font)
    axs[1].set_title("Ferry Route: 3am[UTC] 1.5m model result ", **title_font)
    axs[1].set_xlabel("Longitude [°E]", **axis_font)
    axs[1].set_ylabel("Latitude [°N]", **axis_font)

    # Plot ferry route.
    axs[1].plot(sal_obs[1], sal_obs[2], "black", linewidth=4)
    research_VENUS.axis_colors(axs[1], "grey")

    # Add locations and markers on plot for orientation
    bbox_args = dict(boxstyle="square", facecolor="white", alpha=0.7)
    places = [
        FERRY_ROUTES[route_name]["start"]["terminal"],
        FERRY_ROUTES[route_name]["end"]["terminal"],
        "Vancouver",
    ]
    label_offsets = [0.04, -0.4, 0.09]
    for stn, loc in zip(places, label_offsets):
        axs[1].plot(
            *PLACES[stn]["lon lat"],
            marker="D",
            color="white",
            markersize=10,
            markeredgewidth=2,
        )
        axs[1].annotate(
            stn,
            (PLACES[stn]["lon lat"][0] + loc, PLACES[stn]["lon lat"][1]),
            fontsize=15,
            color="black",
            bbox=bbox_args,
        )

    # Set up model part of salinity comparison plot
    axs[0].plot(
        sal_obs[1],
        nemo_a,
        "DodgerBlue",
        linewidth=2,
        label=f'{FERRY_ROUTES[route_name]["start"]["hour"]} am [UTC]',
    )
    axs[0].plot(
        sal_obs[1],
        nemo_b,
        "MediumBlue",
        linewidth=2,
        label=f'{FERRY_ROUTES[route_name]["start"]["hour"]+1} am [UTC]',
    )

    # Observational component of salinity comparisons plot
    axs[0].plot(sal_obs[1], sal_obs[3], "DarkGreen", linewidth=2, label="Observed")
    axs[0].text(
        0.25,
        -0.1,
        "Observations from Ocean Networks Canada",
        transform=axs[0].transAxes,
        color="white",
    )

    axs[0].set_xlim(-124, -123)
    axs[0].set_ylim(10, 32)
    axs[0].set_title("Surface Salinity: " + dmy, **title_font)
    axs[0].set_xlabel("Longitude", **axis_font)
    axs[0].set_ylabel("Absolute Salinity [g/kg]", **axis_font)
    axs[0].legend(loc=3)
    axs[0].grid(axis="both")

    fig.patch.set_facecolor("#2B3E50")
    research_VENUS.axis_colors(axs[0], "grey")

    return fig


def ferry_salinity(ferry_data_dir, route_name, dmy, step=1):
    """Load ferry data and slice it to contain only the during route values.

    :arg str ferry_data_dir: storage file location for ONC ferry data.

    :arg str route_name: name of a ferre route. HBDB, TWDP or TWSB.

    :arg str dmy: today's date in :kbd:`ddmmmyy` format

    :arg int step: selecting every nth data point

    :returns: matrix containing time, lon, lat and salinity of ferry
              observations
    """
    # Load observation ferry salinity data with locations and time
    date = datetime.datetime.strptime(dmy, "%d%b%y")
    dayf = date - datetime.timedelta(days=1)
    dmyf = dayf.strftime("%d%b%y").lower()

    obs = _get_sal_data(ferry_data_dir, route_name, dmyf)

    # Create datetime object for start and end of route times
    date = datetime.datetime.strptime(dmy, "%d%b%y")
    start_time = date.replace(
        hour=FERRY_ROUTES[route_name]["start"]["hour"],
        minute=FERRY_ROUTES[route_name]["start"]["minute"],
    )
    end_time = date.replace(
        hour=FERRY_ROUTES[route_name]["end"]["hour"],
        minute=FERRY_ROUTES[route_name]["end"]["minute"],
    )

    # Slice the observational arrays to only have "during route" data
    time_obs = datenum2datetime(obs[0])
    df = pd.DataFrame(time_obs)
    j = np.logical_and(df >= start_time, df <= end_time)
    j = np.array(j)
    obs_route = obs[0:4, j]

    # High frequency ferry data, take every 20th value
    obs_slice = obs_route[:, 0:-1:step]

    # Convert to TEOS-10
    obs_slice[3] = teos_tools.psu_teos(obs_slice[3])

    return obs_slice


def nemo_sal_route(grid_T_hr, bathy, route_name, obs_sal):
    """Get the salanity data form the NEMO run that matches the time and
    locations of the ferry route by integrated distance weighted
    interpolation.

    :arg grid_T_hr: Hourly tracer results dataset from NEMO.
    :type grid_T_hr: :class:`netCDF4.Dataset

    :arg bathy: model bathymetry
    :type bathy: numpy array

    :arg route_name: name of a ferre route. HBDB, TWDP or TWSB.
    :type route_name: string

    :arg obs_sal: ferry data during route
    :type obs_sal: numpy array

    :return: model salinity array along the ferry route for two times
    """

    # Get the salinity data
    sal_a, sal_b = _get_nemo_salinity(route_name, grid_T_hr)

    sal_a_route = np.zeros(obs_sal.shape[1])
    sal_b_route = np.zeros(obs_sal.shape[1])

    # Perform the IDW on each data point and put them into an array for
    # the whole route.
    for i in np.arange(obs_sal.shape[1]):
        sal_a_route[i], sal_b_route[i] = _model_IDW(
            obs_sal[:, i], bathy, grid_T_hr, sal_a, sal_b
        )

    # Convert to TEOS-10
    sal_a_t = teos_tools.psu_teos(sal_a_route)
    sal_b_t = teos_tools.psu_teos(sal_b_route)

    return sal_a_t, sal_b_t


def _model_IDW(obs, bathy, grid_T_hr, sal_a, sal_b):
    """Perform a inverse distance weighted (IDW) interpolation with 8 nearest
    points to the model value that is nearest to a ferry observation point.

    :arg obs: Array containing time, lon, lat and salinity or a single point
    :type obs: numpy array

    :arg bathy: model bathymetry
    :type bathy: numpy array

    :arg grid_T_hr: Hourly tracer results dataset from NEMO.
    :type grid_T_hr: :class:`netCDF4.Dataset`

    :arg sal_a: 1.5 m depth for 3 am (if TWDP route, 2am)
    :type sal_a: numpy array

    :arg sal_b: 1.5 m depth for 4 am (if TWDP route, 3am)
    :arg sal_b: numpy array

    :returns: integral of model salinity values divided by weights for
              sal_a and sal_b.
    """
    lats = grid_T_hr.variables["nav_lat"][:, :]
    lons = grid_T_hr.variables["nav_lon"][:, :]
    depths = bathy.variables["Bathymetry"][:]
    x1, y1 = geo_tools.find_closest_model_point(
        obs[1], obs[2], lons, lats
    )  # Removed 'lat_tol=0.00210'
    # Inverse distance weighted interpolation with the 8 nearest model values.
    val_a_sum = 0
    val_b_sum = 0
    weight_sum = 0
    # Some ferry model routes go over land, replace locations when 4 or
    # more of the surrounding grid point are land with NaN.
    interp_area = sal_a[x1 - 1 : x1 + 2, y1 - 1 : y1 + 2]
    if interp_area.size - np.count_nonzero(interp_area) >= 4:
        sal_a_idw = np.NaN
        sal_b_idw = np.NaN
    else:
        for i in np.arange(x1 - 1, x1 + 2):
            for j in np.arange(y1 - 1, y1 + 2):
                # Some adjacent points are land we don't count them into the
                # salinity average.
                if depths[i, j] > 0:
                    dist = geo_tools.haversine(obs[1], obs[2], lons[i, j], lats[i, j])
                    weight = 1.0 / dist
                    weight_sum += weight
                    val_a = sal_a[i, j] * weight
                    val_b = sal_b[i, j] * weight
                    val_a_sum += val_a
                    val_b_sum += val_b
        sal_a_idw = val_a_sum / weight_sum
        sal_b_idw = val_b_sum / weight_sum
    return sal_a_idw, sal_b_idw


def _get_nemo_salinity(route_name, grid_T_hr):
    """Load and select the salinity value of the ferry route time."""
    sal_nemo = grid_T_hr.variables["vosaline"]

    a_start = FERRY_ROUTES[route_name]["start"]["hour"]
    b_start = FERRY_ROUTES[route_name]["start"]["hour"] + 1
    sal_a = sal_nemo[a_start, 1, :, :]
    sal_b = sal_nemo[b_start, 1, :, :]

    return sal_a, sal_b


def _get_sal_data(ferry_data_dir, route_name, dmy):
    """Retrieve the ferry route data from matlab.

    :arg str ferry_data_dir: storage file location for ONC ferry data.

    :arg str route_name: name for one of three ferry routes

    :arg str dmy: date in form ddmonyy

    :returns: list containing time_obs, lon_obs, lat_obs, sal_obs
    """
    route = route_name.replace("_", "")
    date = datetime.datetime.strptime(dmy, "%d%b%y")
    date = date.strftime("%Y%m%d")
    saline = sio.loadmat(os.path.join(ferry_data_dir, route, f"{route}_TSG{date}.mat"))
    struct = (((saline[f"{route}_TSG"])["output"])[0, 0])["Practical_Salinity"][0, 0]
    sal_obs = struct["data"][0, 0]
    time_obs = struct["matlabTime"][0, 0]
    lon_obs = struct["longitude"][0, 0]
    lat_obs = struct["latitude"][0, 0]
    return np.array([time_obs[:], lon_obs[:], lat_obs[:], sal_obs[:]])


def datenum2datetime(datenum):
    """Convert MATLAB datenum array into python Datetime array."""

    timearray = []
    for i in np.arange(len(datenum)):
        time = (
            datetime.datetime.fromordinal(int(datenum[i][0]))
            + datetime.timedelta(days=datenum[i][0] % 1)
            - datetime.timedelta(days=366)
        )
        timearray.append(time)

    return timearray
