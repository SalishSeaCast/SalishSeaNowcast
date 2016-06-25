# Copyright 2013-2016 The Salish Sea NEMO Project and
# The University of British Columbia

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
from collections import namedtuple

import nowcast.figures.website_theme


def compare_venus_ctd(
    node_name, grid_T_hr, timezone,
    figsize=(6, 10),
    theme=nowcast.figures.website_theme,
):
    """Plot the temperature and salinity time series of observations and model
    results at an ONC VENUS node.

    :arg grid_T_hr: Hourly tracer results dataset from NEMO.
    :type grid_T_hr: :class:`netCDF4.Dataset`

    :arg str timezone: Timezone to use for display of model results.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
    plot_date = _prep_plot_data()
    fig, (ax_sal, ax_temp) = _prep_fig_axes(figsize, theme)
