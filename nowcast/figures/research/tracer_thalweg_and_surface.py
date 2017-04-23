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

"""Produce a figure that shows colour contours of a tracer on a vertical slice 
along a section of the domain thalweg,
and on the surface for a section of the domain that excludes Puget Sound 
in the south and Johnstone Strait in the north.
"""
from types import SimpleNamespace

import matplotlib.pyplot as plt

import nowcast.figures.website_theme


def make_figure(figsize=(20, 12), theme=nowcast.figures.website_theme):
    """
    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_data = _prep_plot_data()
    fig, (ax_thalweg, ax_surface) = _prep_fig_axes(figsize, theme)
    _plot_thalweg(ax_thalweg)
    _plot_surface(ax_surface)
    return fig


def _prep_plot_data():
    return SimpleNamespace()


def _prep_fig_axes(figsize, theme):
    fig = plt.figure(
        figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])
    return fig, (ax_thalweg, ax_surface)


def _plot_thalweg(ax_thalweg):
    pass


def _plot_surface(ax_surface):
    pass
