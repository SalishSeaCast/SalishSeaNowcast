# Copyright 2013-2018 The Salish Sea MEOPAR Contributors
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
"""Produce a figure that shows the sea water current at the 2nd Narrows
Ironworkers Memorial Crossing bridge calculated by the VHFR FVCOM model,
the observed current measured by a horizontal ADCP on the bridge piling.

Testing notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/fvcom/TestSecondNarrowsCurrent.ipynb

Development notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/fvcom/DevelopSecondNarrowsCurrent.ipynb
"""
import nowcast.figures.website_theme


def make_figure(figsize=(16, 9), theme=nowcast.figures.website_theme):
    """Plot sea water current calculated by the VHFR FVCOM model, and the
    observed current measured by a horizontal ADCP on the 2nd Narrows
    Ironworkers Memorial Crossing bridge piling.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
