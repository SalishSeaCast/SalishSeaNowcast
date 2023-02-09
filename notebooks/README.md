The Jupyter Notebooks in this directory document
various aspects of the development and maintenance of the SalishSeaCast
automation system.

In particular:

* The [ERDDAP_datasets.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/ERDDAP_datasets.ipynb)
  notebook describes and partially automates the process of generating
  XML fragments for model results datasets to be included in the ERDDAP
  server system.
* The
  [DevelopingNowcastFigureFunctions.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/DevelopingNowcastFigureFunctions.ipynb)
  notebook describes the recommended process for development of those functions,
  and provides an example of development of one.


The links below are to static renderings of the notebooks via
[nbviewer.org](https://nbviewer.org/).
Descriptions under the links below are from the first cell of the notebooks
(if that cell contains Markdown or raw text).

* ## [FCST_Template.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/FCST_Template.ipynb)

    Forecast template

* ## [Out_Template.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/Out_Template.ipynb)

    Production template

* ## [DevelopingSalinityTemplate.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/DevelopingSalinityTemplate.ipynb)

* ## [In_Template.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/In_Template.ipynb)

    Reasearch figures template

* ## [SSH_NeahBay.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/SSH_NeahBay.ipynb)

    This notebook creates daily forcing files for the sea surface height (hourly frequency) at Neah Bay. This can be used to create "obs" or "hindcast" forcing files for nowcasts in the event of a automation system error.

* ## [ERDDAP_datasets.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/ERDDAP_datasets.ipynb)

    **Building ERDDAP Datasets**

    This notebook documents the process of creating XML fragments
    for nowcast system run results files
    for inclusion in `/opt/tomcat/content/erddap/datasets.xml`
    on the `skookum` ERDDAP server instance.

    The contents are a combination of:

    * instructions for using the
    `GenerateDatasetsXml.sh` and `DasDds.sh` tools found in the
    `/opt/tomcat/webapps/erddap/WEB-INF/` directory
    * instructions for forcing the server to update the datasets collection
    via the `/results/erddap/flags/` directory
    * code and metadata to transform the output of `GenerateDatasetsXml.sh`
    into XML fragments that are ready for inclusion in `/opt/tomcat/content/erddap/datasets.xml`

* ## [DevelopingAnalyzeModule.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/DevelopingAnalyzeModule.ipynb)

    Notebook for developing functions in analyze.py

* ## [Developing-make_ww3_current_file-worker.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/Developing-make_ww3_current_file-worker.ipynb)

    **Developing `make_ww3_current_file` Worker**

    Code experiments and verification for the `make_ww3_current_file` worker.

* ## [Test-research_VENUS-Module.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/Test-research_VENUS-Module.ipynb)

    **Test research_VENUS.py**

    This notebook is used to test the research_VENUS.py module.

* ## [LiveOcean_TS_BC_Runner.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/LiveOcean_TS_BC_Runner.ipynb)

    Test LiveOcean BC's for new tidally average single time files

* ## [Salininty_Template.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/Salininty_Template.ipynb)

    Salinity ferry data template

* ## [TofinoWaterLevels.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/TofinoWaterLevels.ipynb)

    Notebook to compare Tofino water levels to previous years.

* ## [ProductionDailyRiverNCfile.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/ProductionDailyRiverNCfile.ipynb)

    **Test `make_runoff_file` for v202111**

    This notebook was used to develop and test the code for generation of the v202111 daily runoff forcing files.
    Those runoff files are based on day-averaged discharge (1 day lagged) observations from gauged rivers across
    the SalishSeaCast model domain.
    That replaces the use of climatology for all watersheds,
    in contrast to prior model versions that used observations for the Fraser River at Hope and climatology for all
    other rivers.

* ## [Original_DailyNowcastFigures.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/Original_DailyNowcastFigures.ipynb)

    Template notebook for creation of notebooks that show daily figures
    from most recent SalishSeaCast NEMO model real-time (nowcast) run.

    This is an interim step toward fully automated web publication of
    analysis and monitoring figures from nowcast runs.

* ## [MakeOldRunoffFiles.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/MakeOldRunoffFiles.ipynb)

    **Code to make old runoff files ****
    note: make_old_runoffs.yaml is identical to nowcast.yaml but puts the river output files somewhere other that /results to avoid accidental overwriting

* ## [surge_warning.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/surge_warning.ipynb)

* ## [ExamineResiduals.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/ExamineResiduals.ipynb)

    Notebook for examinng residuals and error in residuals

* ## [Developing-make_ww3_wind_file-worker.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/Developing-make_ww3_wind_file-worker.ipynb)

    **Developing `make_ww3_wind_file` Worker**

    Code experiments and verification for the `make_ww3_wind_file` worker.

* ## [TestResearchFerriesModule.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/TestResearchFerriesModule.ipynb)

    **Test New `research_ferries` Module**

    Render figure objects returned by `nowcast.research_ferries.salinity_ferry_route()` function.
    Provides data for visual testing to confirm that refactoring has not adversely changed figures for web pages.

    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker.

* ## [DevelopingNowcastFigureFunctions.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/DevelopingNowcastFigureFunctions.ipynb)

    This notebook describes the recommended process for development of
    functions for the `salishsea_tools.nowcast.figures` module,
    and provides an example of development of such a function.

* ## [DailyNowcastFigures.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/DailyNowcastFigures.ipynb)

    Template for daily nowcast figure generation.

* ## [TestingAnalyzeModule.ipynb](https://nbviewer.org/github/SalishSeaCast/SalishSeaNowcast/blob/main/notebooks/TestingAnalyzeModule.ipynb)

    Noteboook to test analyze.py functions


##License

These notebooks and files are copyright 2013 – present
by the SalishSeaCast Project Contributors
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
http://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
