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
"""Colour, fonts, and utility functions that define the look of figures for the
https://salishsea.eos.ubc.ca/nemo/ web pages.
"""

from matplotlib.font_manager import FontProperties

#: The :kbd:`salishsea.eos.ubc.ca/nemo/` pages background colour,
#: from the https://bootswatch.com/superhero/ theme.
SITE_BACKGROUND_COLOUR = "#2B3E50"

#: Colours of various figure elements;
#: the dict key(s) should be descriptive enough to identify the element
#: to which the colour applies.
COLOURS = {
    "axes": {"background": "#dbdee1"},
    "axes textbox": {"facecolor": "white"},
    "axis": {"labels": "white", "spines": "white", "ticks": "white"},
    "cbar": {"label": "white", "tick labels": "white"},
    "contour lines": {"Baynes Sound entrance": "black"},
    "figure": {"facecolor": SITE_BACKGROUND_COLOUR},
    "dark land": "#8b7765",
    "land": "burlywood",
    "marker": {
        "place": {"facecolor": "white", "edgecolor": "black"},
        "max ssh": {"facecolor": "white", "edgecolor": "black"},
    },
    "storm surge risk levels": {
        "extreme risk": "red",
        "moderate risk": "Gold",
        None: "green",
    },
    "text": {
        "axes annotation": "black",
        "axes title": "white",
        "axis": "white",
        "figure annotation": "white",
        "figure title": "white",
        "info box title": "white",
        "info box content": "white",
        "risk level label": "white",
    },
    "time series": {
        # Please keep keys in alphabetical order
        "ciliates": "brown",
        "datetime line": "red",
        "diatoms": "brown",
        "flagellates": "darkgreen",
        "mesozooplankton": "brown",
        "microzooplankton": "darkgreen",
        "nitrate": "darkgreen",
        "salinity": "blue",
        "2nd Narrows model current direction": {"x2": "blue", "r12": "purple"},
        "2nd Narrows model current speed": {"x2": "blue", "r12": "purple"},
        "2nd Narrows observed current direction": "green",
        "2nd Narrows observed current speed": "green",
        "Sand Heads HRDPS wind direction": "blue",
        "Sand Heads HRDPS wind speed": "blue",
        "Sand Heads observed wind direction": "green",
        "Sand Heads observed wind speed": "green",
        "silicon": "brown",
        "ssh residual": "blue",
        "obs residual": "green",
        "temperature": "red",
        "tidal prediction": "black",
        "tidal prediction vs model": "purple",
        "tide gauge ssh": "MediumBlue",
        "tide gauge obs": "green",
        "VENUS node model salinity": "blue",
        "VENUS node dev model salinity": "magenta",
        "VENUS CTD salinity": "green",
        "VENUS node model temperature": "blue",
        "VENUS node dev model temperature": "magenta",
        "VENUS CTD temperature": "green",
        "vhfr fvcom ssh": {"x2": "magenta", "r12": "purple"},
        "wave height": "blue",
        "obs wave height": "green",
        "wave period": "blue",
        "obs wave period": "green",
    },
    "wind arrow": {"facecolor": "DarkMagenta", "edgecolor": "black"},
}

#: Font properties of various figure text elements;
#: the top level dict keys should be descriptive enough to identify the element
#: to which the font properties apply.
FONTS = {
    "axes annotation": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=15
    ),
    "axes title": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=15
    ),
    "axes title large": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=35
    ),
    "axis": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=15
    ),
    "axis small": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=12
    ),
    "figure annotation": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=15
    ),
    "figure annotation small": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=10
    ),
    "figure title": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=15
    ),
    "info box title": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=20
    ),
    "info box content": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=15
    ),
    "legend label": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=15
    ),
    "legend label large": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=25
    ),
    "legend label small": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=12
    ),
    "legend title": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=20
    ),
    "legend title small": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=15
    ),
    "location label large": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=20
    ),
    "location label small": FontProperties(
        family=["Bitstream Vera Sans", "sans-serif"], weight="medium", size=13
    ),
}


def set_axis_colors(ax):
    """Set the colours of axis labels, ticks, and spines.

    :arg ax: Axes object to be formatted.
    :type ax: :py:class:`matplotlib.axes.Axes`
    """
    ax.xaxis.label.set_color(COLOURS["axis"]["labels"])
    ax.yaxis.label.set_color(COLOURS["axis"]["labels"])
    ax.tick_params(axis="x", colors=COLOURS["axis"]["ticks"])
    ax.tick_params(axis="y", colors=COLOURS["axis"]["ticks"])
    ax.spines["bottom"].set_color(COLOURS["axis"]["spines"])
    ax.spines["top"].set_color(COLOURS["axis"]["spines"])
    ax.spines["left"].set_color(COLOURS["axis"]["spines"])
    ax.spines["right"].set_color(COLOURS["axis"]["spines"])
