# Copyright 2013 – present The Salish Sea MEOPAR Contributors
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
This standalone code produces the surface current tiled domain figure in both website themed and unthemed style and saves
the figure files in '/SalishSeaCast/salishsea-site/salishsea_site/static/img/'.

The domain is divided into different tiles and needs to be re-run if the tiles specification/coordinates are changed.
"""

from pathlib import Path

import netCDF4
import numpy
from matplotlib.backend_bases import FigureCanvasBase
from matplotlib.figure import Figure
from salishsea_tools import viz_tools

import nowcast.figures.website_theme


def _make_figure_domain(coordf, bathyf, theme):
    """
    Create surface currents tiled domain figure showing the boundary and labels of each tile.

    :param coordf: Path to Salish Sea NEMO model coordinates file.
    :type coordf: :py:class:`pathlib.Path`

    :param bathyf: Path to Salish Sea NEMO model bathymetry file.
    :type bathyf: :py:class:`pathlib.Path`

    :param theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure` and plot axes.
    """

    if theme is None:
        fig = Figure(figsize=(8.5, 11), facecolor="white")
    else:
        fig = Figure(
            figsize=(5, 6), dpi=100, facecolor=theme.COLOURS["figure"]["facecolor"]
        )

    ax = fig.add_subplot(111)
    ax.grid(True)

    # Decorations
    title = "Salish Sea"
    x_label = "Longitude"
    y_label = "Latitude"

    if theme is None:
        ax.set_title(title, fontsize=10)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
    else:
        ax.set_title(
            title,
            fontsize=10,
            color=theme.COLOURS["text"]["axis"],
            fontproperties=theme.FONTS["axis"],
        )
        ax.set_xlabel(
            x_label,
            color=theme.COLOURS["text"]["axis"],
            fontproperties=theme.FONTS["axis"],
        )
        ax.set_ylabel(
            y_label,
            color=theme.COLOURS["text"]["axis"],
            fontproperties=theme.FONTS["axis"],
        )
        theme.set_axis_colors(
            ax
        )  # Makes the x and y numbers and axis lines into near-white

    with netCDF4.Dataset(bathyf) as _dsBathy:
        viz_tools.plot_land_mask(
            ax, _dsBathy, coords="map", color="burlywood", zorder=-9
        )
        ax.set_rasterization_zorder(-1)
        viz_tools.plot_coastline(ax, _dsBathy, coords="map")

    with netCDF4.Dataset(coordf) as _dsCoord:
        coord_yt = _dsCoord.variables["gphit"][0, :, :]
        viz_tools.set_aspect(ax, coords="map", lats=coord_yt)

    _drawTile(tile_coords_dic, ax)

    return fig, ax


def _drawTile(tile_coords_dic, ax):
    """
    Draw boundary of each tile in the main domain.
    """
    i = 1
    for tile, values in tile_coords_dic.items():
        x1, x2, y1, y2 = values[0], values[1], values[2], values[3]
        cornersX = [x1, x2, x2, x1, x1]
        cornersY = [y1, y1, y2, y2, y1]
        ax.text(
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            str(i),
            color="red",
            size=8,
            backgroundcolor="white",
        )
        i += 1
        ax.plot(cornersX, cornersY, color="b", linestyle="--", linewidth=1)


def _makeHTMLmap(fig, ax, htmlmap_path):
    """
    Update 'surface_current_tilemap.html' file that includes a HTML fragment which makes the domain map clickable.
    """
    i = 1
    header = '<map name="tileclickmap">\n'
    footer = "</map>\n"
    with open(htmlmap_path / "surface_current_tilemap.html", "w") as tilemapfile:
        tilemapfile.write(header)
        for tile, values in tile_coords_dic.items():
            x1, x2, y1, y2 = values[0], values[1], values[2], values[3]

            # Transform x,y data into pixel coordinates
            xy_pixels = ax.transData.transform(numpy.vstack([[x1, x2], [y1, y2]]).T)
            xpix, ypix = xy_pixels.T

            # 0,0 is the lower left coordinate in matplotlib but it's the upper left in HTML
            # so the y-coordinate needs to be flipped here
            width, height = FigureCanvasBase(fig).get_width_height()
            ypix = height - ypix

            curline = (
                '    <area shape="rect" coords="{:3d},{:3d},{:3d},{:3d}"  '
                'href="JavaScript: regionMap({:2d}); void(0);">\n'.format(
                    int(xpix[0]), int(ypix[0]), int(xpix[1]), int(ypix[1]), i
                )
            )
            tilemapfile.write(curline)

            i += 1
        tilemapfile.write(footer)


def _render_figure(fig, storage_path, file_type):
    domain_name = "surface_currents_tilemap.{}".format(file_type)
    outfile = Path(storage_path, domain_name)
    FigureCanvasBase(fig).print_figure(
        outfile.as_posix(), facecolor=fig.get_facecolor()
    )
    print(domain_name)


# Coordinates of each tile (lon1, lon2, lat1, lat2)
# NOTE: The tiles must be the same size to get consistent arrows between tiles
tile_coords_dic = {
    "tile01": (-126.18, -125.43, 50.30, 50.80),
    "tile02": (-125.42, -124.67, 50.50, 51.00),
    "tile03": (-125.75, -125.00, 50.00, 50.50),
    "tile04": (-125.00, -124.25, 50.00, 50.50),
    "tile05": (-124.25, -123.50, 50.00, 50.50),
    "tile06": (-125.26, -124.51, 49.50, 50.00),
    "tile07": (-124.51, -123.76, 49.50, 50.00),
    "tile08": (-123.76, -123.01, 49.50, 50.00),
    "tile09": (-124.90, -124.15, 49.00, 49.50),
    "tile10": (-124.15, -123.40, 49.00, 49.50),
    "tile11": (-123.40, -122.65, 49.00, 49.50),
    "tile12": (-123.86, -123.11, 48.50, 49.00),
    "tile13": (-123.11, -122.36, 48.50, 49.00),
    "tile14": (-125.18, -124.43, 48.24, 48.74),
    "tile15": (-124.43, -123.68, 48.11, 48.61),
    "tile16": (-123.68, -122.93, 48.00, 48.50),
    "tile17": (-122.93, -122.18, 48.00, 48.50),
    "tile18": (-123.01, -122.26, 47.50, 48.00),
    "tile19": (-123.46, -122.71, 47.00, 47.50),
    "tile20": (-122.71, -121.96, 47.00, 47.50),
}

if __name__ == "__main__":
    ## TODO: Can these paths be moved into nowcast.yaml config file?
    root_dir = Path("/SalishSeaCast/")
    coordf = root_dir / "grid/coordinates_seagrid_SalishSea201702.nc"
    bathyf = root_dir / "grid/bathymetry_201702.nc"

    # Path to save the tile map
    image_path = root_dir / "salishsea-site/salishsea_site/static/img/"

    # Path to save the HTML fragment that makes the map clickable.
    htmlmap_path = root_dir / "salishsea-site/salishsea_site/templates/salishseacast/"

    # Un-themed version of the domain
    fig_domain, _ = _make_figure_domain(coordf, bathyf, theme=None)
    _render_figure(fig_domain, image_path, "pdf")

    # Themed version of the domain
    fig_domain, ax_domain = _make_figure_domain(
        coordf, bathyf, theme=nowcast.figures.website_theme
    )
    _render_figure(fig_domain, image_path, "svg")

    # Save the html fragment that makes the map clickable.
    _makeHTMLmap(fig_domain, ax_domain, htmlmap_path)
