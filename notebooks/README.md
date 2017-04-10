The Jupyter Notebooks in this directory document
various aspects of the development and maintenance of the Salish Sea
model nowcast system.

In particular:

* The [ERDDAP_datasets.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/ERDDAP_datasets.ipynb)
  notebook describes and partially automates the process of generating
  XML fragments for model results datasets to be included in the ERDDAP
  server system.
* The
[DevelopingNowcastFigureFunctions.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/DevelopingNowcastFigureFunctions.ipynb)
  notebook describes the recommended process for development of those functions,
  and provides an example of development of one.


The links below are to static renderings of the notebooks via
[nbviewer.ipython.org](http://nbviewer.ipython.org/).
Descriptions under the links below are from the first cell of the notebooks
(if that cell contains Markdown or raw text).

* ##[TofinoWaterLevels.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/TofinoWaterLevels.ipynb)  
    
    Notebook to compare Tofino water levels to previous years.  

* ##[In_Template.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/In_Template.ipynb)  
    
    Reasearch figures template  

* ##[ERDDAP_datasets.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/ERDDAP_datasets.ipynb)  
    
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

* ##[DevelopingNowcastFigureFunctions.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/DevelopingNowcastFigureFunctions.ipynb)  
    
    This notebook describes the recommended process for development of  
    functions for the `salishsea_tools.nowcast.figures` module,  
    and provides an example of development of such a function.  

* ##[DailyNowcastFigures.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/DailyNowcastFigures.ipynb)  
    
    Template for daily nowcast figure generation.  

* ##[ExamineResiduals.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/ExamineResiduals.ipynb)  
    
    Notebook for examinng residuals and error in residuals  

* ##[MakeOldRunoffFiles.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/MakeOldRunoffFiles.ipynb)  
    
    **Code to make old runoff files ****  
    note: make_old_runoffs.yaml is identical to nowcast.yaml but puts the river output files somewhere other that /results to avoid accidental overwriting  

* ##[Out_Template.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/Out_Template.ipynb)  
    
    Production template  

* ##[Developing-make_ww3_wind_file-worker.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/Developing-make_ww3_wind_file-worker.ipynb)  
    
    **Developing `make_ww3_wind_file` Worker**  
      
    Code experiments and verification for the `make_ww3_wind_file` worker.  

* ##[Original_DailyNowcastFigures.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/Original_DailyNowcastFigures.ipynb)  
    
    Template notebook for creation of notebooks that show daily figures  
    from most recent Salish Sea NEMO model real-time (nowcast) run.  
      
    This is an interim step toward fully automated web publication of  
    analysis and monitoring figures from nowcast runs.  

* ##[DevelopingSalinityTemplate.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/DevelopingSalinityTemplate.ipynb)  
    
* ##[Testing research_VENUS.py module.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/Testing research_VENUS.py module.ipynb)  
    
    This notebook is used to test the research_VENUS.py module.  

* ##[SSH_NeahBay.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/SSH_NeahBay.ipynb)  
    
    This notebook creates daily forcing files for the sea surface height (hourly frequency) at Neah Bay. This can be used to create "obs" forcing files for nowcasts in the event of a automation system error.  

* ##[surge_warning.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/surge_warning.ipynb)  
    
* ##[TestResearchFerriesModule.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/TestResearchFerriesModule.ipynb)  
    
    **Test New `research_ferries` Module**  
      
    Render figure objects returned by `nowcast.research_ferries.salinity_ferry_route()` function.  
    Provides data for visual testing to confirm that refactoring has not adversely changed figures for web pages.  
      
    Set-up and function call replicates as nearly as possible what is done in the `nowcast.workers.make_plots` worker.  

* ##[Salininty_Template.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/Salininty_Template.ipynb)  
    
    Salinity ferry data template  

* ##[TestingAnalyzeModule.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/TestingAnalyzeModule.ipynb)  
    
    Noteboook to test analyze.py functions  

* ##[DevelopingAnalyzeModule.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/DevelopingAnalyzeModule.ipynb)  
    
    Notebook for developing functions in analyze.py  

* ##[FCST_Template.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/salishseanowcast/raw/tip/notebooks/FCST_Template.ipynb)  
    
    Forecast template  


##License

These notebooks and files are copyright 2013-2017
by the Salish Sea MEOPAR Project Contributors
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
http://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
