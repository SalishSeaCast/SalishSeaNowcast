The Jupyter Notebooks in this directory are for development and testing of
the results figures generation modules of the SalishSeaCast automation system.

The links below are to static renderings of the notebooks via
[nbviewer.jupyter.org](https://nbviewer.jupyter.org/).
Descriptions under the links below are from the first cell of the notebooks
(if that cell contains Markdown or raw text).

* ## [TestSurfaceCurrents.ipynb](https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/research/TestSurfaceCurrents.ipynb)

    **Test `surface_currents` Module**

    Render figure object produced by the `nowcast.figures.fvcom.surface_currents` module.
    Provides data for visual testing to confirm that refactoring has not adversely changed figure for web page.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker.

* ## [TestThalwegTransect.ipynb](https://nbviewer.jupyter.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/research/TestThalwegTransect.ipynb)

    **Test `thalweg_transect` Module**

    Render figure object produced by the `nowcast.figures.fvcom.thalweg_transect` module.
    Provides data for visual testing to confirm that refactoring has not adversely changed figure for web page.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker.


##License

These notebooks and files are copyright 2013-2020
by the Salish Sea MEOPAR Project Contributors
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
https://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
