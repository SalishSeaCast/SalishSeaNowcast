..  Copyright 2013-2021 The Salish Sea MEOPAR contributors
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

.. _NowcastProductionDeployment:

******************************
Nowcast Production Deployments
******************************

In October 2016 the production deployment of the nowcast system was changed to use the :ref:`SalishSeaNowcast-repo` package that is based on the `NEMO_Nowcast framework`_ framework.
The production deployment uses 3 systems:

.. _NEMO_Nowcast framework: https://nemo-nowcast.readthedocs.io/en/latest/

#. The :py:mod:`nemo_nowcast.message_broker`,
   :py:mod:`nemo_nowcast.manager`,
   :py:mod:`nemo_nowcast.log_aggregator`,
   most of the pre- and post-processing workers run on the :ref:`SalishSeaModelResultsServer`, :kbd:`skookum`, where the deployment is in the :file:`/SalishSeaCast/` directory tree.

#. The development compute server,
   :kbd:`salish`,
   is used to run the daily development model run,
   :kbd:`nowcast-dev` NEMO-3.6 model run.
   :kbd:`salish` and :kbd:`skookum` share storage via NFS mounts,
   so,
   :kbd:`salish` uses the same deployment in the :file:`/SalishSeaCast/` directory tree.

#. The daily
   :kbd:`forecast2`
   (preliminary forecast),
   :kbd:`nowcast`,
   :kbd:`forecast`,
   and :kbd:`nowcast-green` NEMO-3.6 model runs are computed on a cluster of virtual machines provided by `Ocean Networks Canada`_ on the Compute Canada `arbutus.cloud`_ cluster.
   The shared storage for those VMs is provided by an NFS-mounted volume of ::kbd:`arbutus.cloud` `Ceph object storage`_.
   The nowcast deployment is in the :file:`/nemoShare/MEOPAR/nowcast-sys/` directory tree.

   In April 2017,
   daily :kbd:`wwatch3-nowcast`,
   daily :kbd:`wwatch3-forecast`,
   and :kbd:`wwatch3-forecast2`
   (preliminary wave forecast)
   WaveWatch III® v5.16 wave model runs for the Strait of Georgia and Juan de Fuca Strait were added to the computations on :kbd:`arbutus.cloud`.
   The :kbd:`wwatch3-nowcast` and :kbd:`wwatch3-forecast` runs are executed in sequence after the daily :kbd:`nowcast-green` NEMO-3.6 runs.
   The :kbd:`wwatch3-forecast2` runs are executed after the daily :kbd:`forecast2` NEMO-3.6 runs.

   In January 2018,
   daily :kbd:`fvcom-nowcast`
   and :kbd:`fvcom-forecast` FVCOM v4.1-beta model runs for Vancouver Harbour and the Lower Fraser River were added to the computations on the :kbd:`arbutus.cloud`.
   They are executed in sequence after the daily :kbd:`nowcast` NEMO-3.6 runs.
   In January 2019,
   the resolution of the Vancouver Harbour and Lower Fraser River FVCOM v4.1-beta model was increased.
   Those runs are designated :kbd:`fvcom-nowcast-x2` and :kbd:`fvcom-forecast-x2`.
   In March 2019,
   an even higher resolution Vancouver Harbour and Lower Fraser River model configuration was added to the system,
   running daily nowcast runs as :kbd:`fvcom-nowcast-r12`.

   .. _Ocean Networks Canada: https://www.oceannetworks.ca/
   .. _arbutus.cloud: https://docs.computecanada.ca/wiki/Cloud_resources#Arbutus_cloud_.28arbutus.cloud.computecanada.ca.29
   .. _Ceph object storage: https://en.wikipedia.org/wiki/Ceph_(software)

These sections describe the setup of the nowcast system on :kbd:`skookum`/:kbd:`salish` and :kbd:`arbutus.cloud`,
and it operation.

.. toctree::
   :maxdepth: 2

   skookum_salish
   arbutus_cloud
   operations

In May 2018 production runs of a :kbd:`nowcast-green` configuration with AGRIF sub-grids for Baynes Sound and Haro Strait were added to the system.
Those runs are executed on a reserved chassis on :kbd:`orcinus`.
The setup on :kbd:`orcinus`,
as well are the sub-grid initialization preparation with the NEMO-AGRIF nesting tools are described in:

.. toctree::
   :maxdepth: 2

   orcinus

In February 2019 we got access to the UBC EOAS :kbd:`optimum` cluster.
We use it primarily for long hindcast runs,
but also some research runs.
The setup on :kbd:`optimum` is described in:

.. toctree::
   :maxdepth: 2

   optimum

See also the `#optimum-cluster`_ Slack channel.

.. _#optimum-cluster: https://salishseacast.slack.com/?redir=%2Farchives%2FC011S7BCWGK
