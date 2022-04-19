..  Copyright 2013 – present The Salish Sea MEOPAR contributors
..  and The University of British Columbia
..
..  Licensed under the Apache License, Version 2.0 (the "License");
..  you may not use this file except in compliance with the License.
..  You may obtain a copy of the License at
..
..     https://www.apache.org/licenses/LICENSE-2.0
..
..  Unless required by applicable law or agreed to in writing, software
..  distributed under the License is distributed on an "AS IS" BASIS,
..  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
..  See the License for the specific language governing permissions and
..  limitations under the License.

.. _WebsiteTheme:

*************
Website Theme
*************

The :py:mod:`nowcast.figures.website_theme` module provides the definition of colours and fonts that figure modules must use in order to ensure consistency from one to the next,
and with the :kbd:`salishsea.eos.ubc.ca` site NEMO results section styling.

The module contains:

* a constant,
  :py:const:`~nowcast.figures.website_theme.SITE_BACKGROUND_COLOUR`
* 2 dictionaries,
  :py:const:`~nowcast.figures.website_theme.COLOURS` and :py:const:`~nowcast.figures.website_theme.FONTS`
* a function,
  :py:func:`~nowcast.figures.website_theme.set_axis_colors`


:py:const:`~nowcast.figures.website_theme.SITE_BACKGROUND_COLOUR`
=================================================================

:py:const:`SITE_BACKGROUND_COLOUR` is the hex code for the :kbd:`salishsea.eos.ubc.ca/` pages background colour,
from the https://bootswatch.com/superhero/ theme.
It is defined explicitly to make it obvious in the :py:mod:`~nowcast.figures.website_theme` module.
It is used in the :py:const:`COLOURS` dictionary as :kbd:`COLOURS['figure']['facecolor']` so that you can apply it to :py:class:`~matplotlib.figure.Figure` objects by creating them with calls like:

.. code-block:: python

    fig = plt.figure(
        figsize=figsize, facecolor=theme.COLOURS['figure']['facecolor'])


:py:const:`~nowcast.figures.website_theme.COLOURS`
==================================================

Colours of various figure elements;
the dict key(s) should be descriptive enough to identify the element to which the colour applies.
Use them wherever you need to specify the colour of an element of a figure;
e.g.:

.. code-block:: python

    ax.set_xlabel(
        'Distance along thalweg [km]', color=theme.COLOURS['text']['axis'],
        fontproperties=theme.FONTS['axis'])


:py:const:`~nowcast.figures.website_theme.FONTS`
================================================

Font properties of various figure text elements;
the top level dict keys should be descriptive enough to identify the element to which the font properties apply.
Use them whereever you need to specify the font properties of an element of a figure;
e.g.:

.. code-block:: python

    cbar.set_label(
        label,
        fontproperties=theme.FONTS['axis'],
        color=theme.COLOURS['text']['axis'])


:py:func:`~nowcast.figures.website_theme.set_axis_colors`
=========================================================

The need to set the colours of axes labels,
ticks,
and spines is common enough,
and requires enough :py:class:`matplotlib.axes.Axes` method calls that we have created a convenience function to do it.
Typical use is in a website figure module axes labeling function:

.. code-block:: python

    theme.set_axis_colors(ax)
