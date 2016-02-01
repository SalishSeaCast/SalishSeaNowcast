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

* ##[ExamineResiduals.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/ExamineResiduals.ipynb)  
    
    Notebook for examinng residuals and error in residuals  

* ##[TofinoWaterLevels.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/TofinoWaterLevels.ipynb)  
    
    Notebook to compare Tofino water levels to previous years.  

* ##[DailyNowcastFigures.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/DailyNowcastFigures.ipynb)  
    
    Template for daily nowcast figure generation.  

* ##[DevelopingNowcastFigureFunctions.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/DevelopingNowcastFigureFunctions.ipynb)  
    
    This notebook describes the recommended process for development of  
    functions for the `salishsea_tools.nowcast.figures` module,  
    and provides an example of development of such a function.  

* ##[SSH_NeahBay.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/SSH_NeahBay.ipynb)  
    
    This notebook creates daily forcing files for the sea surface height (hourly frequency) at Neah Bay. This can be used to create "obs" forcing files for nowcasts in the event of a automation system error.  

* ##[FCST_Template.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/FCST_Template.ipynb)  
    
    Forecast template  

* ##[Testing research_VENUS.py module.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/Testing research_VENUS.py module.ipynb)  
    
    This notebook is used to test the research_VENUS.py module.  

* ##[DevelopingSalinityTemplate.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/DevelopingSalinityTemplate.ipynb)  
    
* ##[Salininty_Template.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/Salininty_Template.ipynb)  
    
    Salinity ferry data template  

* ##[In_Template.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/In_Template.ipynb)  
    
    Reasearch figures template  

* ##[DevelopingAnalyzeModule.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/DevelopingAnalyzeModule.ipynb)  
    
    Notebook for developing functions in analyze.py  

* ##[Out_Template.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/Out_Template.ipynb)  
    
    Production template  

* ##[ERDDAP_datasets.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/ERDDAP_datasets.ipynb)  
    
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

* ##[Original_DailyNowcastFigures.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/Original_DailyNowcastFigures.ipynb)  
    
    Template notebook for creation of notebooks that show daily figures  
    from most recent Salish Sea NEMO model real-time (nowcast) run.  
      
    This is an interim step toward fully automated web publication of  
    analysis and monitoring figures from nowcast runs.  

* ##[surge_warning.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/surge_warning.ipynb)  
    
* ##[TestingAnalyzeModule.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/TestingAnalyzeModule.ipynb)  
    
    Noteboook to test analyze.py functions  


##License

These notebooks and files are copyright 2013-2016
by the Salish Sea MEOPAR Project Contributors
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
http://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
