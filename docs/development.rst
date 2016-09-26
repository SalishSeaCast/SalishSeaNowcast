.. Copyright 2013-2016 The Salish Sea MEOPAR contributors
.. and The University of British Columbia
..
.. Licensed under the Apache License, Version 2.0 (the "License");
.. you may not use this file except in compliance with the License.
.. You may obtain a copy of the License at
..
..    http://www.apache.org/licenses/LICENSE-2.0
..
.. Unless required by applicable law or agreed to in writing, software
.. distributed under the License is distributed on an "AS IS" BASIS,
.. WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
.. See the License for the specific language governing permissions and
.. limitations under the License.


.. _SalishSeaNowcastPackageUseAndDevelopment:

Use and Development
===================

The primary use for the :kbd:`SalishSeaNowcast` package is development and deployment of the Salish Sea NEMO model nowcast system.
To work on that you should set up a :ref:`SalishSeaNowcastPythonPackageEnvironmwnt` as described below.

A secondary use for the package is to import one of the modules from the :kbd:`nowcast` namespace so that you can use functions from it in code outside of the nowcast system.
To facilitate that use case you can install the package in a Python 3 Anaconda or :program:`conda` environment with:

.. code-block:: bash

    $ cd tools
    $ pip install --editable SalishSeaNowcast/

Having done so,
you should be able to use imports like:

.. code-block:: python

    from nowcast import figures
    ...
    fig = figures.compare_tidalpredictions_maxSSH(...)

or

.. code-block:: python

    import nowcast
    ...
    xxx = nowcast.analyze.depth_average(...)


.. _SalishSeaNowcastPythonPackageEnvironmwnt:

:kbd:`SalishSeaNowcast` Python Package Environment
--------------------------------------------------

The nowcast manager and workers require several Python packages that are not part of the default :ref:`AnacondaPythonDistro` environment.
To avoid adding complexity and potential undesirable interactions and/or side-effects to the default Anaconda Python environment we create an isolated environment for nowcast.


The Fast Way to Create a :kbd:`nowcast` Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The fast way to set up an environment for development,
testing,
and documentation of the nowcast system is:

.. code-block:: bash

    $ conda update conda
    $ cd MEOPAR/tools
    $ conda env create -f SalishSeaNowcast/environment-dev.yaml
    $ source activate nowcast
    (nowcast)$ pip install --editable SalishSeaTools/
    (nowcast)$ pip install --editable SalishSeaCmd/
    (nowcast)$ pip install --editable SalishSeaNowcast/

To deactivate the :kbd:`nowcast` environment and return to your root Anaconda Python environment use:

.. code-block:: bash

    (nowcast)$ source deactivate

If you need to set up a nowcast system test space to run workers in,
jump to :ref:`SalishSeaNowcastDirectoryStructure`.

If you want to know the nitty-gritty details of what the above commands do,
read on...


The Details of Creating a :kbd:`nowcast` Environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The explanation of what those commands accomplish follows:

Ensure that your :program:`conda` package manager is up to date:

.. code-block:: bash

    $ conda update conda

Create a new :program:`conda` environment with Python 3 and program:`pip` installed in it,
and activate the environment:

.. code-block:: bash

    $ conda create -n nowcast python=3 pip

    ...

    $ source activate nowcast

Our first choice for installing packages is the :program:`conda` installer because it uses pre-built binary packages so it is faster and avoids problems that can arise with compilation of C extensions that are part of some of the packages.
Unfortunately,
not all of the packages that we need are available in the :program:`conda` repositories so we use :program:`pip` to install those from the `Python Package Index`_ (PyPI).

.. _Python Package Index: https://pypi.python.org/pypi

Install the packages that the :ref:`SalishSeaToolsPackage` depends on,
the package itself,
and its companion package :ref:`SalishSeaCmdProcessor`:

.. code-block:: bash

    (nowcast)$ conda install matplotlib netCDF4 numpy pandas pyyaml requests scipy
    (nowcast)$ pip install arrow angles
    (nowcast)$ cd MEOPAR/tools
    (nowcast)$ pip install --editable SalishSeaTools
    (nowcast)$ pip install --editable SalishSeaCmd

Install the additional packages that the nowcast manager and workers depend on:

* thee paramiko package that provides a Python implementation of the SSH2 protocol
* the Python bindings to the `ZeroMQ`_ messaging library
* the BeautifulSoup HTML parsing package

.. _ZeroMQ: http://zeromq.org/

.. code-block:: bash

    (nowcast)$ conda install lxml paramiko pyzmq
    (nowcast)$ pip install BeautifulSoup4 driftwood feedgen

Finally,
install Sphinx,
the mako template library,
and the sphinx-bootstrap-theme,
used for the salishsea.eos.ubc.ca site:

.. code-block:: bash

    (nowcast)$ conda install mako sphinx
    (nowcast)$ pip install sphinx-bootstrap-theme

The above packages are sufficient to run the nowcast system.
For development and debugging of Python code,
:ref:`nowcast.figures` functions,
etc.,
you may also want to install IPython and IPython Notebook,
the pytest and coverage unit testing tools,
and the ipdb debugger:

.. code-block:: bash

    (nowcast)$ conda install ipython jupyter pytest coverage
    (nowcast)$ pip install ipdb

The complete list of Python packages installed including their version numbers (at time of writing) created by the :command:`pip freeze` command is available in :file:`SalishSeaNowcast/requirements.txt`.

To deactivate the :kbd:`nowcast` environment and return to your root Anaconda Python environment use:

.. code-block:: bash

    (nowcast)$ source deactivate


.. _SalishSeaNowcastDirectoryStructure:

Directory Structure for Development and Testing
-----------------------------------------------

.. warning::

    Development and testing of nowcast workers, etc. should only be done on machines *other than* :kbd:`salish`.
    If you test on :kbd:`salish` your test runs will interact with the production nowcast manager process and,
    in all likelihood,
    cause other workers to run at in appropriate times,
    potentially disrupting the production real-time runs.

The directory structure described in this section mirrors the one used for the production deployment of the nowcast system.
It can be used to:

* test nowcast workers during development
* test rendering of page templates for the :kbd:`salishsea.eos.ubc.ca` site
* download EC weather model products in the event of an automation failure

The directory structure looks like::

  MEOPAR/
  `-- nowcast/
      |-- nowcast.yaml@
      `-- www/
          |-- salishsea-site/
          `-- templates@

:file:`nowcast.yaml` is a symlink to your :file:`MEOPAR/tools/SalishSeaNowcast/nowcast/nowcast.yaml` configuration file.

The :file:`salishsea-site/` directory tree is a clone of the :ref:`salishsea-site-repo` repo.
This clone is for automation testing only - you should not make commits in it.

:file:`templates` is a symlink to your :file:`MEOPAR/tools/SalishSeaNowcast/nowcast/www/templates/` directory,
where the templates for the pages that nowcast creates on the :kbd:`salishsea.eos.ubc.ca` site are stored.

So,
the commands to create the directory structure are:

.. code-block:: bash

    (nowcast)$ cd MEOPAR/
    (nowcast)$ mkdir -p nowcast/www/
    (nowcast)$ cd nowcast/
    (nowcast)$ ln -s ../tools/SalishSeaNowcast/nowcast/nowcast.yaml
    (nowcast)$ cd www/
    (nowcast)$ hg clone ssh://hg@bitbucket.org/salishsea/salishsea-site
    (nowcast)$ ln -s ../../tools/SalishSeaNowcast/nowcast/www/templates


Testing :kbd:`salishsea.eos.ubc.ca` Site Page Templates
-------------------------------------------------------

The pages that the nowcast automation maintains on the :kbd:`salishsea.eos.ubc.ca` site are generated from templates stored in :file:`MEOPAR/tools/SalishSeaNowcast/nowcast/www/templates/`.
Those templates are reStructuredText files that contain `Mako`_ directives that facilitate,
among other things,
substitution of concrete values (like specific dates) into placeholder variables,
and control structures like loops that simplify repetitive page elements (like collections of figure images),
and if-else blocks that allow conditional inclusion or exclusion of page elements.

.. _Mako: http://www.makotemplates.org/

So,
the process to get from a `Mako`_ page template to an HTML page happens in 2 stages:

#. Use a :py:class:`mako.template.Template` object derived from a :file:`.mako` file and a Python dict of placeholder variable names and values to render a :file:`.rst` file.

#. Use :command:`sphinx-build` to render the :file:`.rst` file to a :file:`.html` file.

In the nowcast production deployment the :file:`make_site_page.py` worker processes one or more page template(s) from the :file:`MEOPAR/tools/SalishSeaNowcast/nowcast/www/templates/` directory to create one or more :file:`.rst` file(s) in the :file:`MEOPAR/nowcast/www/salishsea-site/` directory tree.
When the :file:`make_site_page.py` worker sends a success message to the nowcast manager the :file:`push_to_web.py` worker is launched to:

#. Execute the :command:`hg update` command in :file:`MEOPAR/nowcast/www/salishsea-site/` to pull in any changes from other sources.

#. Execute the equivalent of :command:`make html` in the :file:`MEOPAR/nowcast/www/salishsea-site/site/` directory to run :command:`sphinx-build` to generate the new/changed pages of the site.

#. Execute an :command:`rsync` command to push the changes to the web server.

To test the rendering of site page templates we need to emulate the processing that the :file:`make_site_page.py` worker does and then run :command:`make html` in the :file:`MEOPAR/nowcast/www/salishsea-site/site/` directory so that we can preview the rendered page(s) from the :file:`MEOPAR/nowcast/www/salishsea-site/site/_build/html/` directory tree.

Since each page template contains a unique set of placeholder variables,
creating a general purpose template rendering test tool is probably more effort than it is worth.
Instead sample code that tests an early version of the template used to create the http://salishsea.eos.ubc.ca/storm-surge/forecast.html page is provided.
You can implement similar test code for other page templates in a Python script that you run from the command-line,
or in an IPython Notebook.

The template we're going to test looks like:

.. code-block:: mako

    ************************************************************************
    ${fcst_date.strftime('%A, %d %B %Y')} -- Salish Sea Storm Surge Forecast
    ************************************************************************

    Disclaimer
    ==========

    This site presents output from a research project.
    Results are not expected to be a robust prediction of the storm surge.


    Plots
    =====

    .. raw:: html
        <%
            run_dmy = run_date.strftime('%d%b%y').lower()
        %>
        %for svg_file in svg_file_roots:
        <object class="img-responsive" type="image/svg+xml"
          data="../_static/nemo/results_figures/forecast/${run_dmy}/${svg_file}_${run_dmy}.svg">
        </object>
        <hr>
        %endfor

    Model sea surface height has been evaluated through a series of hindcasts for significant surge events in 2006, 2009, and 2012 [1].

    [1] Soontiens, N., Allen, S., Latornell, D., Le Souef, K., Machuca, I., Paquin, J.-P., Lu, Y., Thompson, K., Korbel, V. (2015).  Storm surges in the Strait of Georgia simulated with a regional model. in prep.

The code below assumes that you are working in your :file:`MEOPAR/nowcast/` directory.

First some imports:

.. code-block:: python

    import datetime
    import os

    import mako.template

Create the template object from the :file:`.mako` file:

.. code-block:: python

    template_path = 'www/templates/'
    template_file = 'forecast.mako'
    mako_file = os.path.join(template_path, template_file)
    tmpl = mako.template.Template(filename=mako_file)

Now,
build the file name/path of the :file:`.rst` file that will be produces when we render the template:

.. code-block:: python

    site_path = 'www/salishsea-site/site/'
    page_path = 'storm-surge/'
    page_name = 'forecast.rst'
    rst_file = os.path.join(site_path, page_path, page_name)

Next,
calculate the template placeholder variables dict.
For this version of the forecast page we need the run date,
the forecast date,
and a list of figure image file name roots.

.. code-block:: python

    run_date = datetime.datetime.today()
    fcst_date = run_date + datetime.timedelta(days=1)
    vars = {
        'run_date': run_date,
        'fcst_date': fcst_date,
        'svg_file_roots': [
            'PA_tidal_predictions',
            'Vic_maxSSH',
            'PA_maxSSH',
            'CR_maxSSH',
            'NOAA_ssh',
            'WaterLevel_Thresholds',
            'SH_wind',
            'Avg_wind_vectors',
            'Wind_vectors_at_max',
        ],
    }

Finally,
use the :py:meth:`render` method of the template object to create the :file:`.rst` file:

.. code-block:: python

    with open(rst_file, 'wt') as f:
        f.write(tmpl.render(**vars))

Putting it all together:

.. code-block:: python

    import datetime
    import os

    import mako.template


    # Load the template
    template_path = 'www/templates/'
    template_file = 'forecast.mako'
    mako_file = os.path.join(template_path, template_file)
    tmpl = mako.template.Template(filename=mako_file)

    # Calculate the file path/name of the .rst file
    site_path = 'www/salishsea-site/site/'
    page_path = 'storm-surge/'
    page_name = 'forecast.rst'
    rst_file = os.path.join(site_path, page_path, page_name)

    # Calculate the template placeholder variable values
    run_date = datetime.datetime.today()
    fcst_date = run_date + datetime.timedelta(days=1)
    vars = {
        'run_date': run_date,
        'fcst_date': fcst_date,
        'svg_file_roots': [
            'PA_tidal_predictions',
            'Vic_maxSSH',
            'PA_maxSSH',
            'CR_maxSSH',
            'NOAA_ssh',
            'WaterLevel_Thresholds',
            'SH_wind',
            'Avg_wind_vectors',
            'Wind_vectors_at_max',
        ],
    }

    # Render the template
    with open(rst_file, 'wt') as f:
        f.write(tmpl.render(**vars))

Having executed the above code,
you should be able to go to :file:`MEOPAR/nowcast/www/salishsea-site/site/`,
execute :command:`make html`,
and preview the finished :file:`.html` page:

.. code-block:: bash

    (nowcast)$ cd MEOPAR/nowcast/www/salishsea-site/site/
    (nowcast)$ make html
    ...
    (nowcast)$ firefox _build/html/storm-surge/forecast.html
