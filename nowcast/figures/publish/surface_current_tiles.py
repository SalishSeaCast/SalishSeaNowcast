# Copyright 2013-2019 The Salish Sea MEOPAR Contributors
# and The University of British Columbia

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Produce surface currents tile figures in both website themed and unthemed style.
"""

import datetime

from matplotlib.figure import Figure
import netCDF4
import numpy
import numpy.ma
import pytz
from salishsea_tools import viz_tools

import nowcast.figures.website_theme


def make_figure(
    run_date,
    t_index,
    Uf,
    Vf,
    coordf,
    mesh_maskf,
    bathyf,
    tile_coords_dic,
    expansion_factor,
    theme=nowcast.figures.website_theme,
):
    """
    Create a list of surface current tile figures for a given time index t_index.

    :param run_date: Date of the run to create the figure tiles for.
    :type run_date: :py:class:`Arrow.arrow`

    :param t_index: time index 
    :type t_index: int

    :param Uf: Path to Salish Sea NEMO grid_U output file.
    :type Uf: :py:class:`pathlib.Path`

    :param Vf: Path to Salish Sea NEMO grid_V output file.
    :type Vf: :py:class:`pathlib.Path`

    :param coordf: Path to Salish Sea NEMO model coordinates file.
    :type coordf: :py:class:`pathlib.Path`

    :param mesh_maskf: Path to Salish Sea NEMO-generated mesh mask file.
    :type mesh_maskf: :py:class:`pathlib.Path`

    :param bathyf: Path to Salish Sea NEMO model bathymetry file.
    :type bathyf: :py:class:`pathlib.Path`

    :param tile_coords_dic: Dictionary containing tile coordinate definitions in longitude and latitude.
                            See :py:mod:`nowcast.figures.surface_current_domain`.
    :type tile_coords_dic: dict

    :param expansion_factor: Overlap fraction for tiles (typically between 0 and 0.25)
    :type expansion_factor: float

    :param theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: list of matplotlib Figures and list of names for all figures
    """

    with netCDF4.Dataset(coordf) as dsCoord:
        coord_xt, coord_yt = _prepareCoordinates(dsCoord)

    with netCDF4.Dataset(Uf) as dsU, netCDF4.Dataset(Vf) as dsV, netCDF4.Dataset(
        mesh_maskf
    ) as dsMask, netCDF4.Dataset(bathyf) as dsBathy:
        fig_list, tile_list = _makeTiles(
            t_index,
            dsU,
            dsV,
            dsMask,
            coord_xt,
            coord_yt,
            dsBathy,
            theme,
            tile_coords_dic,
            expansion_factor,
        )

    return fig_list, tile_list


def _prepareVelocity(time, dsU, dsV, dsMask):
    """
    Load the velocities and unstagger, rotate and mask them.
    """

    # Get array of u (x-direction velocity) at time index time and depthU=0 (top layer)
    u = dsU.variables["vozocrtx"][time, 0, :, :]

    # Get array of v (y-direction velocity) at time index time and depthV=0 (top layer)
    v = dsV.variables["vomecrty"][time, 0, :, :]

    # Unstagger the velocities so they are on T points
    unstaggerU, unstaggerV = viz_tools.unstagger(u, v)

    # Rotate the velocities from grid coordinates to east-north
    unstaggerU_rotate, unstaggerV_rotate = viz_tools.rotate_vel(
        unstaggerU, unstaggerV, origin="grid"
    )

    # Load land mask (0 for land, 1 for water)
    # Drop the first row and first column of the mask to match the unstaggered velocities
    mask = dsMask.variables["tmask"][0, 0, 1:, 1:]

    # Apply land mask to velocities data
    # Use 1-mask here because masked_array needs 1 for missing values.
    maskU = numpy.ma.masked_array(unstaggerU_rotate, 1 - mask)
    maskV = numpy.ma.masked_array(unstaggerV_rotate, 1 - mask)
    return maskU, maskV


def _prepareCoordinates(_dsCoord):
    """
    Loads the longitude and latitude coordinates and trim to match unstaggered velocities
    """
    coord_xt = _dsCoord.variables["glamt"][0, 1:, 1:]
    coord_yt = _dsCoord.variables["gphit"][0, 1:, 1:]
    return coord_xt, coord_yt


def _createTileTitle(sec, units, calendar):
    """
    Constructs the time stamp in both UTC and local time for the figure title
    """
    dt = netCDF4.num2date(sec, units, calendar=calendar)
    dt_utc = datetime.datetime.combine(
        dt.date(), dt.time(), pytz.utc
    )  # add timezone to utc time
    pst_tz = pytz.timezone("Canada/Pacific")
    fmt = "%Y-%m-%d %H:%M:%S %Z"

    loc_dt = dt_utc.astimezone(pst_tz)
    title_pst = loc_dt.strftime(fmt)
    title_utc = dt_utc.strftime(fmt)

    return title_pst + "\n" + title_utc


def _makeTiles(
    t_index,
    dsU,
    dsV,
    dsMask,
    coord_xt,
    coord_yt,
    dsBathy,
    theme,
    tile_coords_dic,
    expansion_factor,
):
    """
    Produce surface current tile figures for each tile at time index t_index
    """
    units = dsU.variables["time_counter"].units
    calendar = dsU.variables["time_counter"].calendar
    maskU, maskV = _prepareVelocity(t_index, dsU, dsV, dsMask)

    k = 3

    tiles = []
    figs = []
    for tile, values in tile_coords_dic.items():

        x1, x2, y1, y2 = values[0], values[1], values[2], values[3]
        sec = dsU.variables["time_counter"][t_index]

        if theme is None:
            fig = Figure(figsize=(8.5, 11), facecolor="white")
        else:
            fig = Figure(
                figsize=(11, 9), facecolor=theme.COLOURS["figure"]["facecolor"]
            )

        ax = fig.add_subplot(111)

        X, Y = coord_xt[::k, ::k].flatten(), coord_yt[::k, ::k].flatten()
        U, V = maskU[::k, ::k].flatten(), maskV[::k, ::k].flatten()

        i = numpy.logical_not(U.mask)
        XC, YC, UC, VC = X[i], Y[i], U[i].data, V[i].data

        # Add some vectors in the middle of the Atlantic to ensure we get at least one for each arrow size
        tempU = numpy.linspace(0, 5, 50)
        zeros = numpy.zeros(tempU.shape)
        XC = numpy.concatenate([XC, zeros])
        YC = numpy.concatenate([YC, zeros])
        UC = numpy.concatenate([UC, tempU])
        VC = numpy.concatenate([VC, zeros])
        SC = numpy.sqrt(UC ** 2 + VC ** 2)
        i = SC < 0.05
        if numpy.any(i):
            UCC, VCC, XCC, YCC = _cut(UC, VC, XC, YC, i)
            ax.scatter(XCC, YCC, s=2, c="k")

        # Arrow parameters: list of tuples of (speed_min, speed_max, arrow_width, arrow_head_width)
        arrowparamslist = [
            (0.05, 0.25, 0.003, 3.00),
            (0.25, 0.50, 0.005, 2.75),
            (0.50, 1.00, 0.007, 2.25),
            (1.00, 1.50, 0.009, 2.00),
            (1.50, 2.00, 0.011, 1.50),
            (2.00, 2.50, 0.013, 1.25),
            (2.50, 3.00, 0.015, 1.00),
            (3.00, 4.00, 0.017, 0.75),
            (4.00, 100, 0.020, 2.00),
        ]

        if theme is None:
            # Quiver key positions (x,y) relative to axes that spans [0,1]x[0,1]
            positionslist = [
                (0.55, 1.14),
                (0.55, 1.10),
                (0.55, 1.06),
                (0.55, 1.02),
                (0.80, 1.18),
                (0.80, 1.14),
                (0.80, 1.10),
                (0.80, 1.06),
                (0.80, 1.02),
            ]
            FP = None
            ax.text(0.53, 1.17, r"$\bullet$    < 0.05 m/s", transform=ax.transAxes)

        else:
            # Quiver key positions (x,y) relative to axes that spans [0,1]x[0,1]
            positionslist = [
                (1.05, 0.95),
                (1.05, 0.90),
                (1.05, 0.85),
                (1.05, 0.80),
                (1.05, 0.75),
                (1.05, 0.70),
                (1.05, 0.65),
                (1.05, 0.60),
                (1.05, 0.55),
            ]

            FP = theme.FONTS["axis"]
            fontsize = FP.get_size() - 4
            ax.text(
                1.03,
                0.98,
                r"$\bullet$    < 0.05 m/s",
                color=theme.COLOURS["text"]["axis"],
                fontsize=fontsize,
                transform=ax.transAxes,
            )

        # Draw each arrow
        for arrowparams, positions in zip(arrowparamslist, positionslist):
            _drawArrows(arrowparams, positions, UC, VC, XC, YC, SC, ax, theme, FP)

        ax.grid(True)

        # Use expansion factor to set axes limits
        dx = (x2 - x1) * expansion_factor
        dy = (y2 - y1) * expansion_factor
        ax.set_xlim([x1 - dx, x2 + dx])
        ax.set_ylim([y1 - dy, y2 + dy])

        # Decorations
        title = _createTileTitle(sec, units, calendar) + "\n" + tile
        x_label = "Longitude"
        y_label = "Latitude"

        if theme is None:
            title_notheme = "SalishSeaCast Surface Currents\n" + title + "\n"
            ax.set_title(title_notheme, fontsize=12, loc="left")
            ax.set_xlabel(x_label)
            ax.set_ylabel(y_label)
        else:
            ax.set_title(
                title,
                fontsize=10,
                color=theme.COLOURS["text"]["axis"],
                fontproperties=FP,
            )
            ax.set_xlabel(
                x_label,
                fontsize=8,
                color=theme.COLOURS["text"]["axis"],
                fontproperties=FP,
            )
            ax.set_ylabel(
                y_label, color=theme.COLOURS["text"]["axis"], fontproperties=FP
            )
            theme.set_axis_colors(
                ax
            )  # Makes the x and y numbers and axis lines into near-white

        x_tick_loc = ax.get_xticks()
        x_tick_label = ["{:.1f}".format(q) for q in x_tick_loc]
        ax.set_xticklabels(x_tick_label, rotation=45)

        viz_tools.plot_land_mask(
            ax, dsBathy, coords="map", color="burlywood", zorder=-9
        )
        ax.set_rasterization_zorder(-1)
        viz_tools.plot_coastline(ax, dsBathy, coords="map")
        viz_tools.set_aspect(ax, coords="map", lats=coord_yt)

        tiles += [tile]
        figs += [fig]
    return figs, tiles


def _cut(UC, VC, XC, YC, i):
    """
    Helper function to subset vectors
    """
    return UC[i], VC[i], XC[i], YC[i]


def _drawArrows(arrowparams, positions, UC, VC, XC, YC, SC, ax, theme, FP):
    """
    Helper function to draw arrows in each velocity range
    arrowparams holds the quiver arrow parameters corresponding to each speed range
    positions holds the coordinates relative to the [0,1]x[0,1] axes to draw the quiverkey
    UC, VC are the velocity components at positions XC, YC
    SC is the speed
    ax is the axes to draw on
    theme is the theme
    FP is a font properties dictionary
    """

    speed_min, speed_max, width, headwidth = arrowparams
    xpos, ypos = positions

    i = (SC >= speed_min) & (SC < speed_max)
    if numpy.any(i):
        # Draw the quiver arrows
        UCC, VCC, XCC, YCC = _cut(UC, VC, XC, YC, i)
        q = ax.quiver(
            XCC,
            YCC,
            UCC / SC[i],
            VCC / SC[i],
            headwidth=2,
            headlength=0.008 / width,
            headaxislength=0.008 / width,
            width=width,
            scale=50,
            zorder=3,
        )

        # Construct quiver label
        if speed_min >= 4:
            label = r">= {:.2f} m/s".format(speed_min)
        else:
            label = r"{:.2f}-{:.2f} m/s".format(speed_min, speed_max)

        # Add the quiverkey label
        if theme is None:
            qk = ax.quiverkey(q, xpos, ypos, 1, label, labelpos="E")
        else:
            fontsize = FP.get_size() - 4
            quickerKey_dict = {
                "family": FP.get_family(),
                "style": FP.get_style(),
                "variant": FP.get_variant(),
                "weight": FP.get_weight(),
                "stretch": FP.get_stretch(),
                "size": fontsize,
            }
            qk = ax.quiverkey(
                q,
                xpos,
                ypos,
                1,
                label,
                labelpos="E",
                color=theme.COLOURS["text"]["axis"],
                labelcolor=theme.COLOURS["text"]["axis"],
                fontproperties=quickerKey_dict,
            )
