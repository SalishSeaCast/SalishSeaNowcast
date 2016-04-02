# Copyright 2013-2016 The Salish Sea MEOPAR contributors
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

"""
"""
import io

import matplotlib.image
from matplotlib import patches as patches
from matplotlib.backends import backend_agg as backend
from matplotlib.figure import Figure


def plot_map(
    ax,
    coastline,
    lat_range=(47.5, 50.7),
    lon_range=(-126, -122),
    land_c='burlywood',
    land_patch_min_area=1e-3,
):
    """Plot map of Salish Sea region, including the options to add a
    coastline, colour of the land, and colour of the domain.

    :arg ax: Axis for map.
    :type ax: axis object

    :arg coastline: Coastline dataset.
    :type coastline: :class:`mat.Dataset`

    :arg tuple lat_range: latitude range to be plotted

    :arg tuple lon_range: longitude range to be plotted

    :arg string land_c: colour of land if coastline

    :arg float land_patch_min_area: minimum area of land patch
                    that is plotted
    """

    mapfig = make_background_map(
        coastline, lat_range=lat_range, lon_range=lon_range,
        land_c=land_c, land_patch_min_area=land_patch_min_area)
    buffer_ = _render_png_buffer(mapfig)
    img = matplotlib.image.imread(buffer_, format='anything')
    ax.imshow(
        img, zorder=0,
        extent=[lon_range[0], lon_range[1], lat_range[0], lat_range[1]])
    ax.set_xlim(lon_range[0], lon_range[1])
    ax.set_ylim(lat_range[0], lat_range[1])


def make_background_map(
        coastline, lat_range=(47.5, 50.7), lon_range=(-126, -122),
        land_patch_min_area=1e-4, land_c='burlywood'):
    """
    Create a figure from an mmap dataset showing a lat-lon patch.

    The map is intended for use as the background in figures on which model
    results are plotted. It is rasterized to minimize file size.

    :arg coastline: Coastline dataset.
    :type coastline: :class:`mat.Dataset`

    :arg tuple lat_range:  latitude range to be plotted

    :arg tuple lon_range: longitude range to be plotted

    :arg string land_c: colour of land if coastline

    :arg float land_patch_min_area: minimum area of land patch
                    that is plotted
    """

    coast_lat = coastline['ncst'][:, 1]
    coast_lon = coastline['ncst'][:, 0]
    fig = Figure(figsize=(15, 15))
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(coast_lon, coast_lat, '-k', rasterized=True, markersize=1)

    k = coastline['k'][:, 0]
    area_ = coastline['Area'][0]
    ## WTF???
    Area = area_
    mask = Area > land_patch_min_area
    kss = k[:-1][mask]
    kee = k[1:][mask]

    for ks, ke in zip(kss, kee):
        poly = list(zip(coast_lon[ks:ke-2], coast_lat[ks:ke-2]))
        ax.add_patch(
            patches.Polygon(
                poly, facecolor=land_c, rasterized=True))

    ax.set_frame_on(False)
    ax.axes.get_yaxis().set_visible(False)
    ax.axes.get_xaxis().set_visible(False)
    ax.set_xlim(lon_range)
    ax.set_ylim(lat_range)
    fig.set_tight_layout({'pad': 0})
    return fig


def _render_png_buffer(fig):
    canvas = backend.FigureCanvasAgg(fig)
    buffer = io.BytesIO()
    canvas.print_figure(buffer, format='png')
    return buffer
