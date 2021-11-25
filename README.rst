*****************************
Salish Sea NEMO Model Nowcast
*****************************

:License: Apache License, Version 2.0

.. image:: https://img.shields.io/badge/license-Apache%202-cb2533.svg
    :target: https://www.apache.org/licenses/LICENSE-2.0
    :alt: Licensed under the Apache License, Version 2.0
.. image:: https://img.shields.io/badge/python-3.9-blue.svg
    :target: https://docs.python.org/3.9/
    :alt: Python Version
.. image:: https://img.shields.io/badge/version%20control-git-blue.svg?logo=github
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast
    :alt: Git on GitHub
.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://black.readthedocs.io/en/stable/
    :alt: The uncompromising Python code formatter
.. image:: https://readthedocs.org/projects/salishsea-nowcast/badge/?version=latest
    :target: https://salishsea-nowcast.readthedocs.io/en/latest/
    :alt: Documentation Status
.. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/workflows/sphinx-linkcheck/badge.svg
      :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:sphinx-linkcheck
      :alt: Sphinx linkcheck
.. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/workflows/CI/badge.svg
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow%3ACI
    :alt: pytest and test coverage analysis
.. image:: https://codecov.io/gh/SalishSeaCast/SalishSeaNowcast/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/SalishSeaCast/SalishSeaNowcast
    :alt: Codecov Testing Coverage Report
.. image:: https://github.com/SalishSeaCast/SalishSeaNowcast/actions/workflows/codeql-analysis.yaml/badge.svg
      :target: https://github.com/SalishSeaCast/SalishSeaNowcast/actions?query=workflow:CodeQL
      :alt: CodeQL analysis
.. image:: https://img.shields.io/github/issues/SalishSeaCast/SalishSeaNowcast?logo=github
    :target: https://github.com/SalishSeaCast/SalishSeaNowcast/issues
    :alt: Issue Tracker

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
    :target: https://salishsea-nowcast.readthedocs.io/en/latest/
    :alt: Documentation Status


License
=======

.. image:: https://img.shields.io/badge/license-Apache%202-cb2533.svg
    :target: https://www.apache.org/licenses/LICENSE-2.0
    :alt: Licensed under the Apache License, Version 2.0

The Salish Sea NEMO model nowcast system code and documentation are copyright 2013-2021 by the `Salish Sea MEOPAR Project Contributors`_ and The University of British Columbia.

.. _Salish Sea MEOPAR Project Contributors: https://github.com/SalishSeaCast/docs/blob/master/CONTRIBUTORS.rst

They are licensed under the Apache License, Version 2.0.
http://www.apache.org/licenses/LICENSE-2.0
Please see the LICENSE file for details of the license.
