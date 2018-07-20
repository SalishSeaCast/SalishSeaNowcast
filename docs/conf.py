#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Salish Sea MEOPAR tools documentation build configuration file
#
# This file is execfile()d with the current directory set to
# its containing dir.
#
# Note that not all possible configuration values are present in this
# auto-generated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import datetime
import os
import sys


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))


# -- Project information -----------------------------------------------------

project = 'Salish Sea Nowcast System'
author = (
    'Salish Sea MEOPAR Project Contributors '
    'and The University of British Columbia')
copyright_years = (
    '2013' if datetime.date.today().year == 2013
    else '2016-{this_year:%Y}'.format(this_year=datetime.date.today()))
copyright = '{copyright_years}, {author}'.format(
    copyright_years=copyright_years, author=author)

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
# The short X.Y version.
from nowcast import __pkg_metadata__
version = __pkg_metadata__.VERSION
# The full version, including alpha/beta/rc tags.
release = version


# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings.
# They can be extensions coming with Sphinx
# (named 'sphinx.ext.*')
# or your custom ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'nemonowcast': ('https://nemo-nowcast.readthedocs.io/en/latest/', None),
    'salishseadocs': (
        'https://salishsea-meopar-docs.readthedocs.io/en/latest/', None),
    'salishseatools': (
        'https://salishsea-meopar-tools.readthedocs.io/en/latest/', None),
    'salishseasite': (
        'https://salishsea-site.readthedocs.io/en/latest/', None),
    'salishseacmd': (
        'https://salishseacmd.readthedocs.io/en/latest/', None),
}

todo_include_todos = True

autodoc_mock_imports = [
    'bs4',
    'cmocean',
    'driftwood',
    'driftwood.formatters',
    'f90nml',
    'feedgen',
    'feedgen.entry',
    'feedgen.feed',
    'fvcom_cmd',
    'gsw',
    'mako',
    'mako.template',
    'moad_tools',
    'moad_tools.observations',
    'moad_tools.places',
    'nemo_cmd',
    'nemo_nowcast.fileutils',
    'nemo_nowcast.workers',
    'nemo_nowcast.workers.clear_checklist',
    'nemo_nowcast.workers.rotate_logs',
    'netCDF4',
    'OPPTools',
    'pandas',
    'paramiko',
    'salishsea_cmd',
    'salishsea_cmd.api',
    'salishsea_cmd.lib',
    'salishsea_tools',
    'salishsea_tools.LiveOcean_BCs',
    'salishsea_tools.namelist',
    'salishsea_tools.places',
    'salishsea_tools.UBC_subdomain',
    'salishsea_tools.unit_conversions',
    'scipy',
    'scipy.interpolate',
    'scipy.io',
    'shapely',
    'xarray',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build', '**.ipynb_checkpoints']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'sphinx_rtd_theme'

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
html_favicon = '_static/MEOPAR_favicon.ico'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If false, no module index is generated.
html_domain_indices = False

# If false, no index is generated.
html_use_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
html_show_copyright = True
