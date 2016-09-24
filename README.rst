*****************************
Salish Sea NEMO Model Nowcast
*****************************

The ``SalishSeaNowcast`` package is a collection of Python modules associated with running the Salish Sea NEMO model in a daily nowcast/forecast mode.
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

Documentation for the package is in the ``docs/`` directory and is rendered at https://salishsea-nowcast.readthedocs.io/en/latest/.

.. image:: https://readthedocs.org/projects/salishsea-nowcast/badge/?version=latest
    :target: http://salishsea-nowcast.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status


License
=======

The Salish Sea NEMO model nowcast system code and documentation are copyright 2013-2016 by the `Salish Sea MEOPAR Project Contributors`_ and The University of British Columbia.

.. _Salish Sea MEOPAR Project Contributors: https://bitbucket.org/salishsea/docs/src/tip/CONTRIBUTORS.rst

They are licensed under the Apache License, Version 2.0.
http://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
