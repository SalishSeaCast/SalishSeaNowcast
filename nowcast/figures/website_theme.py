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

"""Colour, fonts, and utility functions that define the look of figures for the
https://salishsea.eos.ubc.ca/nemo/ web pages.
"""


from matplotlib.font_manager import FontProperties


#: The :kbd:`salishsea.eos.ubc.ca/nemo/` pages background colour,
#: from the http://bootswatch.com/superhero/ theme.
SITE_BACKGROUND_COLOUR = '#2B3E50'


#: Colours of various figure elements;
#: the dict key(s) should be descriptive enough to identify the element
#: to which the colour applies.
COLOURS = {
    'axes textbox': {
        'facecolor': 'white',
    },
    'axis': {
        'labels': 'white',
        'spines': 'white',
        'ticks': 'white',
    },
    'cbar': {
        'label': 'white',
        'tick labels': 'white',
    },
    'figure': {
        'facecolor': SITE_BACKGROUND_COLOUR,
    },
    'land': 'burlywood',

    'storm surge risk levels': {
        'extreme risk': 'red',
        'moderate risk': 'Gold',
        None: 'green',
    },
    'wind arrow': {
        'facecolor': 'DarkMagenta',
        'edgecolor': 'black',
    },
}


#: Font properties of various figure text elements;
#: the top level dict keys should be descriptive enough to identify the element
#: to which the font properties apply.
#: The font property keys are names of the attributes of a
#: :py:class:`matplotlib.font_manager.FontProperties` object.
FONTS = {
    'axes annotation': {
        'fontname': 'Bitstream Vera Sans',
        'size': 14,
        'color': 'black',
        'weight': 'medium',
    },
    'axes title': {
        'fontname': 'Bitstream Vera Sans',
        'size': 15,
        'color': 'white',
        'weight': 'medium',
    },
    'axis': {
        'fontname': 'Bitstream Vera Sans',
        'size': 13,
        'color': 'white',
        'weight': 'medium',
    },
    'figure annotation': {
        'fontname': 'Bitstream Vera Sans',
        'size': 14,
        'color': 'white',
        'weight': 'medium',
    },
    'legend label': FontProperties(
        family=['Bitstream Vera Sans', 'sans-serif'], weight='medium', size=15),
    'legend title': FontProperties(
        family=['Bitstream Vera Sans', 'sans-serif'], weight='medium', size=20),
    'location label large': FontProperties(
        family=['Bitstream Vera Sans', 'sans-serif'], weight='medium', size=20),
    'location label small': FontProperties(
        family=['Bitstream Vera Sans', 'sans-serif'], weight='medium', size=13),
}


def set_axis_colors(ax):
    """Set the colours of axis labels, ticks and spines.

    :arg ax: Axes object to be formatted.
    :type ax: :py:class:`matplotlib.axes.Axes`
    """
    ax.xaxis.label.set_color(COLOURS['axis']['labels'])
    ax.yaxis.label.set_color(COLOURS['axis']['labels'])
    ax.tick_params(axis='x', colors=COLOURS['axis']['ticks'])
    ax.tick_params(axis='y', colors=COLOURS['axis']['ticks'])
    ax.spines['bottom'].set_color(COLOURS['axis']['spines'])
    ax.spines['top'].set_color(COLOURS['axis']['spines'])
    ax.spines['left'].set_color(COLOURS['axis']['spines'])
    ax.spines['right'].set_color(COLOURS['axis']['spines'])
