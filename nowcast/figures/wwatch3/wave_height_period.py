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
"""Produce a figure that shows significant wave height and dominant wave period
at a wave buoy calculated by the SoG WaveWatch3(TM) model,
and observed wave heights and dominant wave periods from the NOAA NDBC
http://www.ndbc.noaa.gov/data/realtime2/ web service.

Testing notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/wwatch3/TestWaveHeightPeriod.ipynb

Development notebook for this module is
https://nbviewer.jupyter.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/figures/wwatch3/DevelopWaveHeightPeriod.ipynb
"""
import nowcast.figures.website_theme


def make_figure(
    place,
    fvcom_ssh_dataset,
    nemo_ssh_dataset_url_tmpl,
    figsize=(16, 9),
    theme=nowcast.figures.website_theme
):
    """Plot water levels calculated by the VHFR FVCOM and SalishSeaCast NEMO
    models, and predicted and observed water levels from the CHS
    https://ws-shc.qc.dfo-mpo.gc.ca/ water levels web service for the
    tide gauge station at :kbd:`place`.

    :arg str place: Tide gauge station name;
                    must be a key in :py:obj:`salishsea_tools.places.PLACES`.

    :arg fvcom_ssh_dataset: VHFR FVCOM model tide gauge station sea surface
                            height time series dataset.
    :type fvcom_ssh_dataset: 'py:class:xarray.Dataset`

    :arg str nemo_ssh_dataset_url_tmpl: ERDDAP URL template for SalishSeaCast
                                        NEMO model tide gauge station
                                        sea surface height time series dataset.

    :arg 2-tuple figsize: Figure size (width, height) in inches.

    :arg theme: Module-like object that defines the style elements for the
                figure. See :py:mod:`nowcast.figures.website_theme` for an
                example.

    :returns: :py:class:`matplotlib.figure.Figure`
    """
