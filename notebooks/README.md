The Jupyter Notebooks in this directory document
various aspects of the developemtn and maintenance of the Salish Sea
model nowcast system.

In particular,
the [ERDDAP_datasets.ipynb](http://nbviewer.ipython.org/urls/bitbucket.org/salishsea/tools/raw/tip/SalishSeaNowcast/notebooks/ERDDAP_datasets.ipynb)
notebook describes and partially automates the process of generating
XML fragments for model results datasets to be included in the ERDDAP
server system.

The links below are to static renderings of the notebooks via
[nbviewer.ipython.org](http://nbviewer.ipython.org/).
Descriptions under the links below are from the first cell of the notebooks
(if that cell contains Markdown or raw text).

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


##License

These notebooks and files are copyright 2013-2016
by the Salish Sea MEOPAR Project Contributors
and The University of British Columbia.

They are licensed under the Apache License, Version 2.0.
http://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
