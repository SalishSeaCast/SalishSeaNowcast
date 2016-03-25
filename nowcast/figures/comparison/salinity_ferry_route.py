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

"""Produce a figure that compares salinity at 1.5m depth model results to
salinity observations from the ONC instrument package aboard a BC Ferries
vessel.
"""
import datetime
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.io as sio

from salishsea_tools import (
    viz_tools,
    tidetools,
    teos_tools
)
from salishsea_tools.places import PLACES

## TODO: only figures.axis_colors() is used, so replace this:
from nowcast.figures import figures
## with something like:
# from nowcast import website_theme


__all__ = ['salinity_ferry_route', 'prep_plot_arrays']


def salinity_ferry_route(
    figsize=(20, 7.5),
):
    """Plot salinity comparison of 1.5m depth model results to
    salinity observations from the ONC instrument package aboard a BC Ferries
    vessel as well as ferry route with model salinity distribution.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :returns: :py:class:`matplotlib.Figure.figure`
    """
    prep_plot_arrays()
    return fig


def prep_plot_arrays():
    """
    """
    pass
