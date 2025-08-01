..  Copyright 2013 – present by the SalishSeaCast Project contributors
..  and The University of British Columbia
..
..  Licensed under the Apache License, Version 2.0 (the "License");
..  you may not use this file except in compliance with the License.
..  You may obtain a copy of the License at
..
..     https://www.apache.org/licenses/LICENSE-2.0
..
..  Unless required by applicable law or agreed to in writing, software
..  distributed under the License is distributed on an "AS IS" BASIS,
..  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
..  See the License for the specific language governing permissions and
..  limitations under the License.

.. SPDX-License-Identifier: Apache-2.0


.. _NowcastProductionDeployment:

******************************
Nowcast Production Deployments
******************************

In October 2016 the production deployment of the nowcast system was changed to use the :ref:`SalishSeaNowcast-repo` package that is based on the `NEMO_Nowcast framework`_ framework.
The production deployment uses 2 systems:

.. _NEMO_Nowcast framework: https://nemo-nowcast.readthedocs.io/en/latest/

#. The :py:mod:`nemo_nowcast.message_broker`,
   :py:mod:`nemo_nowcast.manager`,
   :py:mod:`nemo_nowcast.log_aggregator`,
   most of the pre- and post-processing workers run on the :ref:`SalishSeaModelResultsServer`, :`m``, where the deployment is in the :file:`/SalishSeaCast/` directory tree.

#. The daily
   ``forecast2``
   (preliminary forecast),
   ``nowcast``,
   ``forecast``,
   and ``nowcast-green`` NEMO-3.6 model runs are computed on a cluster of virtual machines provided by `Ocean Networks Canada`_ on the Compute Canada `arbutus.cloud`_ cluster.
   The shared storage for those VMs is provided by an NFS-mounted volume of ``arbutus.cloud`` `Ceph object storage`_.
   The nowcast deployment is in the :file:`/nemoShare/MEOPAR/nowcast-sys/` directory tree.

   In April 2017,
   daily ``wwatch3-nowcast``,
   daily ``wwatch3-forecast``,
   and ``wwatch3-forecast2``
   (preliminary wave forecast)
   WaveWatch III® v5.16 wave model runs for the Strait of Georgia and Juan de Fuca Strait were added to the computations on ``arbutus.cloud``.
   The ``wwatch3-nowcast`` and ``wwatch3-forecast`` runs are executed in sequence after the daily ``nowcast-green`` NEMO-3.6 runs.
   The ``wwatch3-forecast2`` runs are executed after the daily ``forecast2`` NEMO-3.6 runs.

   In January 2018,
   daily ``fvcom-nowcast``
   and ``fvcom-forecast`` FVCOM v4.1-beta model runs for Vancouver Harbour and the Lower Fraser River were added to the computations on the ``arbutus.cloud``.
   They are executed in sequence after the daily ``nowcast`` NEMO-3.6 runs.
   In January 2019,
   the resolution of the Vancouver Harbour and Lower Fraser River FVCOM v4.1-beta model was increased.
   Those runs are designated ``fvcom-nowcast-x2`` and ``fvcom-forecast-x2``.
   In March 2019,
   an even higher resolution Vancouver Harbour and Lower Fraser River model configuration was added to the system,
   running daily nowcast runs as ``fvcom-nowcast-r12``.

   In February 2023,
   we stopped running the Vancouver Harbour and Lower Fraser River FVCOM v4.1-beta model configurations
   because the focus of high resolution models being developed for harbours and the like by DFO had
   shifted to nested NEMO grid configurations.
   In April 2024,
   all of the code,
   tests,
   documentation,
   and configuration for running FVCOM was removed from the ``SalishSeaNowcast`` package.
   Version 25.1 of ``SalishSeaNowcast`` was released before that removal was started.

   .. _Ocean Networks Canada: https://www.oceannetworks.ca/
   .. _arbutus.cloud: https://docs.alliancecan.ca/wiki/Cloud_resources
   .. _Ceph object storage: https://en.wikipedia.org/wiki/Ceph_(software)

These sections describe the setup of the nowcast system on ``skookum`` and ``arbutus.cloud``,
and their operation.

.. toctree::
   :maxdepth: 2

   skookum
   arbutus_cloud
   operations

In May 2018 production runs of a ``nowcast-green`` configuration with AGRIF sub-grids for Baynes Sound and Haro Strait were added to the system.
Those runs are executed on a reserved chassis on ``orcinus``.
The setup on ``orcinus``,
as well are the sub-grid initialization preparation with the NEMO-AGRIF nesting tools are described in:

.. toctree::
   :maxdepth: 2

   orcinus

In February 2019 we got access to the UBC EOAS ``optimum`` cluster.
We use it primarily for long hindcast runs,
but also some research runs.
The setup on ``optimum`` is described in:

.. toctree::
   :maxdepth: 2

   optimum

See also the `#optimum-cluster`_ Slack channel.

.. _#optimum-cluster: https://salishseacast.slack.com/?redir=%2Farchives%2FC011S7BCWGK

With the update of the production to run the V21-11 model version in January 2024,
we decided to end the daily ``nowcast-dev`` development model runs on ``salish``.
Development is now generally done in research runs on ``graham``.
``salish`` is now mostly used for analysis tasks, post-processing of NEMO model results files
to produce day-average and month-average dataset files,
and Lagrangian particle tracking analysis with :program:`ariane` and :program:`OceanParcels`.
