.. Copyright 2013-2015 The Salish Sea MEOPAR contributors
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


.. _salishsea_tools.nowcast:

*****************************************
:py:mod:`salishsea_tools.nowcast` Package
*****************************************

The :py:mod:`salishsea_tools.nowcast` package is a collection of Python modules associated with running the Salish Sea NEMO model in a daily nowcast/forecast mode.
The runs use as-recent-as-available
(typically previous day)
forcing data for the western boundary sea surface height and the Fraser River flow,
and atmospheric forcing from the four-times-daily produced forecast results from the Environment Canada High Resolution Deterministic Prediction System (HRDPS) operational GEM 2.5km resolution model.

The runs are automated using an asynchronous,
message-based architecture that:

* obtains the forcing datasets from web services
* pre-processes the forcing datasets into the formats expected by NEMO
* uploads the forcing dataset files to the HPC or cloud-computing facility where the run will be executed
* executes the run
* downloads the results
* prepares a collection of plots from the run results for monitoring purposes
* publishes the plots and the processing log to the web

The automation architecture is presently under development.
It consists of a long-running manager process and a collection of worker processes which are launched by the manager or by cron to perform specific tasks.


Contents:

.. toctree::
   :maxdepth: 2

   framework
   workers
   config
   dev_deploy
   api
