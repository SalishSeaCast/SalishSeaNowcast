..  Copyright 2013-2019 The Salish Sea MEOPAR contributors
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

.. _ArbutusCloudDeployment:

*******************************
:kbd:`arbutus.cloud` Deployment
*******************************

In April 2019 the `Ocean Networks Canada`_ private cloud computing facility was migrated from :kbd:`west.cloud` to the Compute Canada `arbutus.cloud`_.
:kbd:`arbutus.cloud` runs on `OpenStack Queens`_ release.

.. _Ocean Networks Canada: http://www.oceannetworks.ca/
.. _arbutus.cloud: https://www.westgrid.ca/support/systems/arbutus
.. _OpenStack Queens: https://www.openstack.org/software/queens/

The `OpenStack dashboard`_ provides a web interface to manage and report on cloud resources.
The :kbd:`arbutus.cloud` dashboard is at https://arbutus.cloud.computecanada.ca/.

.. _OpenStack dashboard: https://docs.openstack.org/horizon/queens/user/

Authentication and authorization for :kbd:`arbutus.cloud` is managed by `computecanada`_,
so those are the userid/password that are required to log in to the dashboard.

.. _computecanada: https://www.computecanada.ca/


Web Interface
=============

Initial setup was done via the https://arbutus.cloud.computecanada.ca/ web interface with guidance from the
`Compute Canada Cloud Quickstart Guide`_ and the `OpenStack End User Guide`_.

.. _Compute Canada Cloud Quickstart Guide: https://docs.computecanada.ca/wiki/Cloud_Quick_Start
.. _OpenStack End User Guide: https://docs.openstack.org/queens/user/

The project (aka tenant) name for the SalishSeaCast system is :kbd:`rrg-allen`.


Network
-------

The network configuration was done for us by Compute Canada.
It's configuration can be inspected via the :guilabel:`Network` section of the web interface.
The subnet of the VMs is :kbd:`rrg-allen-network` and it routes to the publich network via the :kbd:`rrg-allen-router`.
There is 1 floating IP address available for assignment to provide access from the public network to a VM.


.. _AccessAndSecurity:

Access & Security
-----------------

Generate an ssh key pair on a Linux or OS/X system using the command:

.. code-block:: bash

    $ cd $HOME/.ssh/
    $ ssh -t rsa -b 4096 -f ~/.ssh/arbutus.cloud_id_rsa -C <yourname>-arbutus.cloud

Assign a strong passphrase to the key pair when prompted.
Passphraseless keys have their place,
but they are a bad idea for general use.

Import the public key into the web interface via the :guilabel:`Compute > Key Pairs > Import Key Pair` button.

Use the :guilabel:`Compute > Network > Security Groups > Manage Rules` button associated with the :guilabel:`default` security group to add security rules to allow:

* :command:`ssh`
* :command:`ping`
* ZeroMQ distributed logging subscriptions

access to the image instances.

:command:`ssh` Rule:

* Rule: SSH
* Remote: CIDR
* CIDR: 0.0.0.0/0

:command:`ping` Rule:

* Rule: ALL ICMP
* Direction: Ingress
* Remote: CIDR
* CIDR: 0.0.0.0/0

ZeroMQ distributed logging subscription Rules:

* For :py:mod:`~nowcast.workers.run_NEMO` and :py:mod:`~nowcast.workers.watch_NEMO`:

  * Rule: Custom TCP
  * Direction: Ingress
  * Port range: 5556 - 5557
  * Remote: CIDR
  * CIDR: 142.103.36.0/24

* For :py:mod:`~nowcast.workers.make_ww3_wind_file`,
  :py:mod:`~nowcast.workers.make_ww3_current_file`,
  :py:mod:`~nowcast.workers.run_ww3`,
  and :py:mod:`~nowcast.workers.watch_ww3`:

  * Rule: Custom TCP
  * Direction: Ingress
  * Port range: 5570 - 5573
  * Remote: CIDR
  * CIDR: 142.103.36.0/24

* For :py:mod:`~nowcast.workers.make_fvcom_boundary`,
  :py:mod:`~nowcast.workers.make_fvcom_rivers_forcing`,
  :py:mod:`~nowcast.workers.run_fvcom`,
  and :py:mod:`~nowcast.workers.watch_fvcom`:

  * Rule: Custom TCP
  * Direction: Ingress
  * Port range: 5580 - 5587
  * Remote: CIDR
  * CIDR: 142.103.36.0/24


.. _HeadNodeInstance:

Head Node Instance
------------------

Use the :guilabel:`Compute > Instances` section of the web interface to manage instances.

To launch an instance to use as the head node use the :guilabel:`Launch Instance` button.
On the :guilabel:`Details` tab set the following parameters:

* Instance Name: :kbd:`nowcast0`
* Description: :kbd:`SalishSeaCast system head node`
* Availability Zone: :kbd:`Any Availability Zone`
* Count: :kbd:`1`

On the :guilabel:`Source` tab set the following parameters:

* Select Boot Source: :kbd:`Image`
* Create New Volume: :kbd:`No`
* Image: :kbd:`Ubuntu-18.04-Bionic-x64-2018-09`

.. note::
    We have to use the :kbd:`Ubuntu-18.04-Bionic-x64-2018-09` image,
    not the :kbd:`Ubuntu-18.04-Bionic-minimal-x64-2018-08` image because the latter does not include the kernel elements required for the head node to run the NFS server service.

On the :guilabel:`Flavor` tab choose: :kbd:`nemo-c16-60gb-90-numa-test`

On the :guilabel:`Network` tab confirm that :kbd:`rrg-allen-network` is selected.

On the :guilabel:`Security Groups` tab confirm that :kbd:`default` is selected.

On the :guilabel:`Key Pairs` tab confirm that the key pair you imported in the :ref:`AccessAndSecurity` section above is selected.

.. note::

    If only 1 key pair has been imported it will be used by default.
    If there is more than 1 key pair available,
    one must be selected.
    Only 1 key can be loaded automatically into an instance on launch.
    Additional public keys can be loaded once an instance is running.

Click the :guilabel:`Launch` button to launch the instance.

Once the instance is running use the :guilabel:`More > Associate Floating IP` menu item to associate a public IP address with the instance.


.. _ComputeNodeInstance:

Compute Node Instance
---------------------

Use the :guilabel:`Compute > Instances` section of the web interface to manage instances.

To launch an instance to use as a compute node template use the :guilabel:`Launch Instance` button.
On the :guilabel:`Details` tab set the following parameters:

* Instance Name: :kbd:`nowcast1`
* Description: :kbd:`SalishSeaCast system compute node`
* Availability Zone: :kbd:`Any Availability Zone`
* Count: :kbd:`1`

On the :guilabel:`Source` tab set the following parameters:

* Select Boot Source: :kbd:`Image`
* Create New Volume: :kbd:`No`
* Image: :kbd:`Ubuntu-18.04-Bionic-minimal-x64-2018-08`

On the :guilabel:`Flavor` tab choose: :kbd:`nemo-c16-60gb-90-numa-test`

On the :guilabel:`Network` tab confirm that :kbd:`rrg-allen-network` is selected.

On the :guilabel:`Security Groups` tab confirm that :kbd:`default` is selected.

On the :guilabel:`Key Pairs` tab confirm that the key pair you imported in the :ref:`AccessAndSecurity` section above is selected.

.. note::

    If only 1 key pair has been imported it will be used by default.
    If there is more than 1 key pair available,
    one must be selected.
    Only 1 key can be loaded automatically into an instance on launch.
    Additional public keys can be loaded once an instance is running.

Click the :guilabel:`Launch` button to launch the instance.


.. _PersistentSharedStorage:

Persistent Shared Storage
-------------------------

Use the :guilabel:`Volumes > Volumes` section of the web interface to manage the persistent shared storage volume.

To create a persistent shared storage volume that will be mounted on all instances use the :guilabel:`Create Volume` button and fill in the dialog with the following parameters:

* Volume Name: :kbd:`nemoShare`
* Description: :kbd:`SalishSeaCast system shared persistent storage`
* Volume Source: :kbd:`No source, empty volume`
* Type: :kbd:`Default`
* Size (GB): :kbd:`1024`
* Availability Zone: :kbd:`nova`

Use :guilabel:`Actions > Manage Attachments` to attach the volume to the :kbd:`nowcast0` :ref:`HeadNodeInstance`.



:command:`ssh` Access
=====================

Log in to the publicly accessible head node instance with the command:

.. code-block:: bash

    $ ssh -i $HOME/.ssh/arbutus.cloud_id_rsa ubuntu@<ip-address>

The first time you connect to an instance you will be prompted to accept its RSA host key fingerprint.
You can verify the fingerprint by looking for the :kbd:`SSH HOST KEY FINGERPRINT` section in the instance log in the :guilabel:`Instances > nowcast0 > Log` tab.
If you have previously associated a different instance with the IP address you may receive a message about host key verification failure and potential man-in-the-middle attacks.
To resolve the issue delete the prior host key from your :file:`$HOME/.ssh/known_hosts` file.
The message will tell you what line it is on.

You will also be prompted for the pasphrase that you assigned to the ssh key pair when you created it.
On Linux and OS/X authenticating the ssh key with your pasphrase has the side-effect of adding it to the :command:`ssh-agent` instance that was started when you logged into the system.
You can add the key to the agent yourself with the command:

.. code-block:: bash

    $ ssh-add $HOME/.ssh/arbutus.cloud_id_rsa

You can list the keys that the agent is managing for you with:

.. code-block:: bash

    $ ssh-add -l

You can simplify logins to the instance by adding the following lines to your :file:`$HOME/.ssh/config` file::

  Host west.cloud
      Hostname        <ip-address>
      User            ubuntu
      IdentityFile    ~/.ssh/arbutus.cloud_id_rsa
      ForwardAgent    yes

With that in place you should be able to connect to the instance with:

.. code-block:: bash

    $ ssh arbutus.cloud


Provisioning and Configuration
==============================

Head Node
---------

Fetch and apply any available updates on the :kbd:`nowcast0` :ref:`HeadNodeInstance` that you launched above with:

.. code-block:: bash

    $ sudo apt update
    $ sudo apt upgrade
    $ sudo apt auto-remove

Set the timezone with:

.. code-block:: bash

    $ sudo timedatectl set-timezone America/Vancouver

Confirm the date,
time,
time zone,
and that the :kbd:`systemd-timesyncd.service` is activate with:

.. code-block:: bash

    $ timedatectl status

Provision the :ref:`HeadNodeInstance` with the following packages:

.. code-block:: bash

    $ sudo apt update
    $ sudo apt install -y mercurial git
    $ sudo apt install -y gfortran
    $ sudo apt install -y libopenmpi2 libopenmpi-dev openmpi-bin
    $ sudo apt install -y libnetcdf-dev libnetcdff-dev netcdf-bin
    $ sudo apt install -y nco
    $ sudo apt install -y liburi-perl m4
    $ sudo apt install -y make cmake ksh mg
    $ sudo apt install -y python3-pip python3-dev
    $ sudo apt install -y nfs-common nfs-kernel-server

Copy the public key of the passphrase-less ssh key pair that will be used for nowcast cloud operations into :file:`$HOME/.ssh/` and append it to the :file:`authorized_keys` file:

.. code-block:: bash

    # on a system where they key pair is stored
    $ ssh-copy-id -f -i $HOME/.ssh/SalishSeaNEMO-nowcast_id_rsa arbutus.cloud

The nowcast operations key pair could have been used as the default key pair in the OpenStack web interface,
but using a key pair with a passphrase there allows for more flexibility:
in particular,
the possibility of revoking the passphrase-less key pair without loosing access to the instances.

Add code to :file:`$HOME/.profile` to add wwatch3 :file:`bin/` and :file:`exe/` paths to :envvar:`PATH` if they exist,
and export environment variables to enable wwatch3 to use netCDF4:

.. code-block:: bash

    # Add wwatch3 bin/ and exe/ paths to PATH if they exist
    if [ -d "/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin" ] ; then
        PATH="/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin:$PATH"
    fi
    if [ -d "/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/exe" ] ; then
        PATH="/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/exe:$PATH"
    fi

    # Enable wwatch3 to use netCDF4
    export WWATCH3_NETCDF=NC4
    export NETCDF_CONFIG=$(which nc-config)

Create :file:`$HOME/.bash_aliases` containing a command to make :command:`rm` default to prompting for confirmation:

.. code-block:: bash

    alias rm="rm -i"


Shared Persistent Storage
^^^^^^^^^^^^^^^^^^^^^^^^^

Confirm that the :ref:`PersistentSharedStorage` volume is attached on :kbd:`vdc` with:

.. code-block:: bash

    $ sudo lsblk -f

The expected output is like::

  NAME    FSTYPE LABEL           UUID                                 MOUNTPOINT
  vda
  ├─vda1  ext4   cloudimg-rootfs 5e99de08-0334-45c0-82a2-7938eb21ac53 /
  ├─vda14
  └─vda15 vfat   UEFI            B60C-5465                            /boot/efi
  vdb     ext4   ephemeral0      5f16e568-7cff-4a88-a51c-b3c0bd50803c /mnt
  vdc


Format the volume with an `ext4` file system and confirm:

.. code-block:: bash

    $ sudo mkfs.ext4 /dev/vdc
    $ sudo lsblk -f

The expected output is like::

  NAME    FSTYPE LABEL           UUID                                 MOUNTPOINT
  vda
  ├─vda1  ext4   cloudimg-rootfs 5e99de08-0334-45c0-82a2-7938eb21ac53 /
  ├─vda14
  └─vda15 vfat   UEFI            B60C-5465                            /boot/efi
  vdb     ext4   ephemeral0      5f16e568-7cff-4a88-a51c-b3c0bd50803c /mnt
  vdc     ext4                   381a0eb2-9429-42b2-9be0-1ddb53087f94

Create the :file:`/nemoShare/` mount point,
mount the volume,
and set the owner and group:

.. code-block:: bash

    $ sudo mkdir /nemoShare
    $ sudo mount /dev/vdc /nemoShare
    $ sudo chown ubuntu:ubuntu /nemoShare

Set up the NFS server service to provide access to the shared storage on the compute nodes.

Reference: https://help.ubuntu.com/community/SettingUpNFSHowTo

.. code-block:: bash

    $ sudo mkdir -p /export/MEOPAR
    $ sudo mount --bind /nemoShare/MEOPAR /export/MEOPAR

Add the following line to :file:`/etc/fstab`::

  /nemoShare/MEOPAR   /export/MEOPAR  none  bind  0  0

Add the following lines to :file:`/etc/exports`::

  /export        192.168.238.0/24(rw,fsid=0,insecure,no_subtree_check,async)
  /export/MEOPAR 192.168.238.0/24(rw,nohide,insecure,no_subtree_check,async)

Restart the NFS service:

  .. code-block:: bash

    $ sudo systemctl start nfs-kernel-server.service


Compute Node Template
---------------------

Fetch and apply any available updates on the :kbd:`nowcast1` :ref:`ComputeNodeInstance` that you launched above with:

.. code-block:: bash

    $ sudo apt update
    $ sudo apt upgrade
    $ sudo apt auto-remove

Set the timezone with:

.. code-block:: bash

    $ sudo timedatectl set-timezone America/Vancouver

Confirm the date,
time,
time zone,
and that the :kbd:`systemd-timesyncd.service` is activate with:

.. code-block:: bash

    $ timedatectl status

Provision the :ref:`HeadNodeInstance` with the following packages:

.. code-block:: bash

    $ sudo apt update
    $ sudo apt install -y gfortran
    $ sudo apt install -y libopenmpi2 libopenmpi-dev openmpi-bin
    $ sudo apt install -y libnetcdf-dev libnetcdff-dev netcdf-bin
    $ sudo apt install -y mg
    $ sudo apt install -y nfs-common

Add code to :file:`$HOME/.profile` to add wwatch3 :file:`bin/` and :file:`exe/` paths to :envvar:`PATH` if they exist,
and export environment variables to enable wwatch3 to use netCDF4:

.. code-block:: bash

    # Add wwatch3 bin/ and exe/ paths to PATH if they exist
    if [ -d "/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin" ] ; then
        PATH="/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin:$PATH"
    fi
    if [ -d "/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/exe" ] ; then
        PATH="/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/exe:$PATH"
    fi

    # Enable wwatch3 to use netCDF4
    export WWATCH3_NETCDF=NC4
    export NETCDF_CONFIG=$(which nc-config)

Create :file:`$HOME/.bash_aliases` containing a command to make :command:`rm` default to prompting for confirmation:

.. code-block:: bash

    alias rm="rm -i"

Create the :file:`/nemoShare/` mount point,
and set the owner and group:

.. code-block:: bash

    $ sudo mkdir -p /nemoShare/MEOPAR
    $ sudo chown ubuntu:ubuntu /nemoShare/ /nemoShare/MEOPAR/

Capture a snapshot image of the instance to use to as the boot image for the other compute nodes using the :guilabel:`Create Snapshot` button on the :guilabel:`Compute > Instances` page.
Use a name like :kbd:`nowcast-compute-node-v0` for the image.


Hosts Mappings
==============

Once all of the compute node VMs have been launched so that we know their IP addresses,
create an :file:`.ssh/config` file,
and MPI hosts mapping files for NEMO/WAVEWATCH VMs and FVCOM VMs on the head node.

Head Node :file:`.ssh/config`
-----------------------------

::

  Host *
       StrictHostKeyChecking no

  # Head node and XIOS host
  Host nowcast0
    HostName 192.168.238.14

  # NEMO compute nodes
  Host nowcast1
    HostName 192.168.238.10
  Host nowcast2
    HostName 192.168.238.13
  Host nowcast3
   HostName 192.168.238.8
  Host nowcast4
    HostName 192.168.238.16
  Host nowcast5
    HostName 192.168.238.5
  Host nowcast6
    HostName 192.168.238.6
  Host nowcast7
    HostName 192.168.238.18
  Host nowcast8
    HostName 192.168.238.15

  # FVCOM compute nodes
  Host fvcom0
    HostName 192.168.238.12
  Host fvcom1
    HostName 192.168.238.7
  Host fvcom2
    HostName 192.168.238.20
  Host fvcom3
    HostName 192.168.238.11
  Host fvcom4
    HostName 192.168.238.9
  Host fvcom5
    HostName 192.168.238.28
  Host fvcom6
    HostName 192.168.238.27


MPI Hosts Mappings
------------------

:file:`$HOME/mpi_hosts` for NEMO/WAVEWATCH VMs containing::

  192.168.238.10 slots=15 max-slots=16
  192.168.238.13 slots=15 max-slots=16
  192.168.238.8  slots=15 max-slots=16
  192.168.238.16 slots=15 max-slots=16
  192.168.238.5  slots=15 max-slots=16
  192.168.238.6  slots=15 max-slots=16
  192.168.238.18 slots=15 max-slots=16
  192.168.238.15 slots=15 max-slots=16

:file:`$HOME/mpi_hosts.fvcom.x2` for FVCOM VMs used for :kbd:`x2` model configuration runs containing::

  192.168.238.12 slots=15 max-slots=16
  192.168.238.7  slots=15 max-slots=16

:file:`$HOME/mpi_hosts.fvcom.r12` for FVCOM VMs used for :kbd:`r12` model configuration runs containing::

  192.168.238.20 slots=15 max-slots=16
  192.168.238.11 slots=15 max-slots=16
  192.168.238.9  slots=15 max-slots=16
  192.168.238.28 slots=15 max-slots=16
  192.168.238.27 slots=15 max-slots=16


Mercurial Repositories
======================

Clone the following repos into :file:`/nemoShare/MEOPAR/nowcast-sys/`:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/
    $ hg clone ssh://hg@bitbucket.org/mdunphy/fvcom-cmd FVCOM-Cmd
    $ hg clone ssh://hg@bitbucket.org/salishsea/grid grid
    $ hg clone ssh://hg@bitbucket.org/UBC_MOAD/moad_tools moad_tools
    $ hg clone ssh://hg@bitbucket.org/salishsea/nemo-3.6-code NEMO-3.6-code
    $ hg clone ssh://hg@bitbucket.org/salishsea/nemo-cmd NEMO-Cmd
    $ hg clone ssh://hg@bitbucket.org/43ravens/nemo_nowcast NEMO_Nowcast
    $ hg clone ssh://hg@bitbucket.org/salishsea/rivers-climatology rivers-climatology
    $ hg clone ssh://hg@bitbucket.org/salishsea/salishseacmd SalishSeaCmd
    $ hg clone ssh://hg@bitbucket.org/salishsea/salishseanowcast SalishSeaNowcast
    $ hg clone ssh://hg@bitbucket.org/salishsea/salishseawaves SalishSeaWaves
    $ hg clone ssh://hg@bitbucket.org/salishsea/ss-run-sets SS-run-sets
    $ hg clone ssh://hg@bitbucket.org/salishsea/tides tides
    $ hg clone ssh://hg@bitbucket.org/salishsea/tools tools
    $ hg clone ssh://hg@bitbucket.org/salishsea/tracers tracers
    $ hg clone ssh://hg@bitbucket.org/salishsea/xios-2 XIOS-2
    $ hg clone ssh://hg@bitbucket.org/salishsea/xios-arch XIOS-ARCH


Git Repositories
================

Clone the following repos into :file:`/nemoShare/MEOPAR/nowcast-sys/`:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/
    $ git clone git@gitlab.com:mdunphy/FVCOM41.git
    $ git clone git@gitlab.com:mdunphy/FVCOM-VHFR-config.git
    $ git clone git@gitlab.com:mdunphy/OPPTools.git


Build XIOS-2
============

Symlink the XIOS-2 build configuration files for :kbd:`arbutus.cloud` from the :file:`XIOS-ARCH` repo clone into the :file:`XIOS-2/arch/` directory:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/XIOS-2/arch
    $ ln -s ../../XIOS-ARCH/COMPUTECANADA/arch-GCC_ARBUTUS.fcm
    $ ln -s ../../XIOS-ARCH/COMPUTECANADA/arch-GCC_ARBUTUS.path

Build XIOS-2 with:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/XIOS-2
    $ ./make_xios --arch GCC_ARBUTUS --netcdf_lib netcdf4_seq --job 8


Build NEMO-3.6
==============

Build NEMO-3.6 and :program:`rebuild_nemo.exe`:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/NEMO-3.6-code/NEMOGCM/CONFIG
    $ XIOS_HOME=/nemoShare/MEOPAR/nowcast-sys/XIOS-2 ./makenemo -m GCC_ARBUTUS -n SalishSeaCast -j8
    $ XIOS_HOME=/nemoShare/MEOPAR/nowcast-sys/XIOS-2 ./makenemo -m GCC_ARBUTUS -n SalishSeaCast_Blue -j8
    $ cd /nemoShare/MEOPAR/nowcast-sys/NEMO-3.6-code/NEMOGCM/TOOLS/
    $ XIOS_HOME=/nemoShare/MEOPAR/nowcast-sys/XIOS-2 ./maketools -m GCC_ARBUTUS -n REBUILD_NEMO


.. _ArbutusCloudBuildWaveWatch3:

Build WAVEWATCH III :sup:`®`
============================

Access to download WAVEWATCH III :sup:`®`
(wwatch3 hereafter)
code tarballs is obtained by sending an email request from the http://polar.ncep.noaa.gov/waves/wavewatch/license.shtml.
The eventual reply will provide a username and password that can be used to access http://polar.ncep.noaa.gov/waves/wavewatch/distribution/ from which the :file:`wwatch3.v5.16.tar.gz` files can be downloaded with:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/
    $ curl -u username:password -LO download_url

where :kbd:`username`,
:kbd:`password`,
and :kbd:`download_url` are those provided in the reply to the email request.

.. note::
    The `west.cloud-vm`_ repo provides a `Vagrant`_ virtual machine configuration that emulates the Salish Sea Nowcast system compute deployment on ONC west.cloud VMs.
    The VM can be used for small scale testing of wwatch3.

    .. _west.cloud-vm: https://bitbucket.org/salishsea/west.cloud-vm
    .. _Vagrant: https://www.vagrantup.com/

Follow the instructions in the Installing Files section of the `wwatch3 manual`_ to unpack the tarball to create a local installation in :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/`
that will use the :program:`gfortran` and :program:`gcc` compilers:

.. _wwatch3 manual: http://polar.ncep.noaa.gov/waves/wavewatch/manual.v5.16.pdf

.. code-block:: bash

    $ mkdir /nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16
    $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16
    $ tar -xvzf /nemoShare/MEOPAR/nowcast-sys/wwatch3.v5.16.tar.gz
    $ ./install_ww3_tar

:program:`install_ww3_tar` is an interactive shell script.
Accept the defaults that it offers other than to choose:

* local installation in :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/`
* :program:`gfortran` as the Fortran 77 compiler
* :program:`gcc` as the C compiler

Ensure that :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin` and :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/exe` are in :envvar:`PATH`.

Change the :file:`comp` and :file:`link` scripts in :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin` to point to :file:`comp.gnu` and :file:`link.gnu`,
and make :file:`comp.gnu` executable:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin
    $ ln -sf comp.gnu comp && chmod +x comp.gnu
    $ ln -sf link.gnu link

Symlink the :file:`SalishSeaWaves/switch` file in :file:`/nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin`:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/bin
    $ ln -sf /nemoShare/MEOPAR/nowcast-sys/SalishSeaWaves/switch switch

Export the :envvar:`WWATCH3_NETCDF` and :envvar:`NETCDF_CONFIG` environment variables:

.. code-block:: bash

    export WWATCH3_NETCDF=NC4
    export NETCDF_CONFIG=$(which nc-config)

Build the suite of wwatch3 programs with:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-5.16/work
    $ w3_make


.. _ArbutusCloudBuildFVCOM41:

Build FVCOM-4.1
===============

Build FVCOM with:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/FVCOM41/Configure
    $ ./setup -c VancouverHarbourX2 -a UBUNTU-18.04-GCC
    $ make libs gotm fvcom


.. _ArbutusCloudUpdateFVCOM41:

Update FVCOM-4.1
----------------

Fetch and merge changes from the `FVCOM41 repo on GitLab`_ and do a clean build:

.. _FVCOM41 repo on GitLab: https://gitlab.com/mdunphy/FVCOM41

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/FVCOM41/
    $ git pull origin master
    $ cd Configure/
    $ ./setup -c VancouverHarbourX2 -a UBUNTU-18.04-GCC
    $ make clean
    $ make libs gotm fvcom


Python Packages
===============

Install the `Miniconda`_ environment and package manager:

.. _Miniconda: https://docs.conda.io/en/latest/miniconda.html

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/
    $ curl -LO https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    $ bash Miniconda3-latest-Linux-x86_64.sh

Answer :file:`/nemoShare/MEOPAR/nowcast-sys/miniconda3` when the installer asks for an installation location.

Answer no when the install asks :guilabel:`Do you wish the installer to initialize Miniconda3 by running conda init? [yes|no]`.

The Python packages that the system depends on are installed in a conda environment with:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/
    $ conda update conda
    $ conda env create \
        --prefix /nemoShare/MEOPAR/nowcast-sys/nowcast-env \
        -f SalishSeaNowcast/environment-prod.yaml
    $ source /nemoShare/MEOPAR/nowcast-sys/miniconda3/bin/activate /nemoShare/MEOPAR/nowcast-sys/nowcast-env/
    (/nemoShare/MEOPAR/nowcast-sys/nowcast-env)$ python -m pip install --editable NEMO_Nowcast/
    (/nemoShare/MEOPAR/nowcast-sys/nowcast-env)$ python -m pip install --editable moad_tools/
    (/nemoShare/MEOPAR/nowcast-sys/nowcast-env)$ python -m pip install --editable tools/SalishSeaTools/
    (/nemoShare/MEOPAR/nowcast-sys/nowcast-env)$ python -m pip install --editable OPPTools/
    (/nemoShare/MEOPAR/nowcast-sys/nowcast-env)$ python -m pip install --editable NEMO-Cmd/
    (/nemoShare/MEOPAR/nowcast-sys/nowcast-env)$ python -m pip install --editable SalishSeaCmd/
    (/nemoShare/MEOPAR/nowcast-sys/nowcast-env)$ python -m pip install --editable FVCOM-Cmd/
    (/nemoShare/MEOPAR/nowcast-sys/nowcast-env)$ python -m pip install --editable SalishSeaNowcast/


Environment Variables
=====================

Add the following files to the :file:`/nemoShare/MEOPAR/nowcast-sys/nowcast-env` environment to automatically :command:`export` the environment variables required by the nowcast system when the environment is activated:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/nowcast-env
    $ mkdir -p etc/conda/activate.d
    $ cat << EOF > etc/conda/activate.d/envvars.sh
    export NOWCAST_ENV=/nemoShare/MEOPAR/nowcast-sys/nowcast-env
    export NOWCAST_CONFIG=/nemoShare/MEOPAR/nowcast-sys/SalishSeaNowcast/config
    export NOWCAST_YAML=/nemoShare/MEOPAR/nowcast-sys/SalishSeaNowcast/config/nowcast.yaml
    export NOWCAST_LOGS=/nemoShare/MEOPAR/nowcast-sys/logs/nowcast
    export SENTRY_DSN=a_valid_sentry_dsn_url
    EOF

and :command:`unset` them when it is deactivated.

.. code-block:: bash

    $ mkdir -p etc/conda/deactivate.d
    $ cat << EOF > etc/conda/deactivate.d/envvars.sh
    unset NOWCAST_ENV
    unset NOWCAST_CONFIG
    unset NOWCAST_YAML
    unset NOWCAST_LOGS
    unset SENTRY_DSN
    EOF


.. _ArbutusCloudNEMORunsDirectory:

NEMO Runs Directory
===================

Create a :file:`runs/` directory for the NEMO runs and populate it with:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/
    $ mkdir -p logs/nowcast/
    $ mkdir runs
    $ chmod g+ws runs
    $ cd runs/
    $ mkdir -p LiveOcean NEMO-atmos rivers ssh
    $ chmod -R g+s LiveOcean NEMO-atmos rivers ssh
    $ ln -s ../grid
    $ ln -s ../rivers-climatology
    $ ln -s ../tides
    $ ln -s ../tracers

    $ cp ../SS-run-sets/v201702/nowcast-green/namelist.time_nowcast_template namelist.time


WaveWatch Runs Directories
==========================

Create a :file:`wwatch3-runs/` directory tree and populate it with:

* The wwatch3 grid:

  .. code-block:: bash

      $ mkdir -p /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/grid
      $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/
      $ ln -s /nemoShare/MEOPAR/nowcast-sys/SalishSeaWaves/ww3_grid_SoG.inp ww3_grid.inp
      $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/grid
      $ ln -sf /nemoShare/MEOPAR/nowcast-sys/SalishSeaWaves/SoG_BCgrid_00500m.bot
      $ ln -sf /nemoShare/MEOPAR/nowcast-sys/SalishSeaWaves/SoG_BCgrid_00500m.msk
      $ cd /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/
      $ ww3_grid | tee ww3_grid.out

* Directory for wind forcing:

  .. code-block:: bash

      $ mkdir -p /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/wind

  The :program:`make_ww3_wind_file` worker:

  * Uses files from :file:`/nemoShare/MEOPAR/GEM2.5/ops/NEMO-atmos/` appropriate for the wwatch3 run date and type to produce a :file:`SoG_wind_yyyymmdd.nc` file in the :file:`wind/` directory

  The :program:`run_ww3` worker:

  * Generates in the temporary run directory a :file:`ww3_prnc_wind.inp` file containing the path to the file produced by the :program:`make_ww3_wind_file` worker
  * Symlinks :file:`ww3_prnc_wind.inp` as :file:`ww3_prnc.inp`
  * Runs :program:`ww3_prnc` to produce the wwatch3 wind forcing files for the run.
    The output of :program:`ww3_prnc` is stored in the run's :file:`stdout` file.

* Directory for current forcing:

  .. code-block:: bash

      $ mkdir -p /nemoShare/MEOPAR/nowcast-sys/wwatch3-runs/current

  The :program:`make_ww3_wind_file` worker:

  * Uses files from the :file:`/nemoShare/MEOPAR/SalishSea/` NEMO results storage tree appropriate for the wwatch3 run date and type to produce a :file:`SoG_current_yyyymmdd.nc` file in the :file:`current/` directory

  The :program:`run_ww3` worker:

  * Generates in the temporary run directory a :file:`ww3_prnc_current.inp` file containing the path to the file produced by the :program:`make_ww3_current_file` worker
  * Symlinks :file:`ww3_prnc_current.inp` as :file:`ww3_prnc.inp`
  * Runs :program:`ww3_prnc` to produce the wwatch3 current forcing files for the run.
    The output of :program:`ww3_prnc` is stored in the run's :file:`stdout` file.


FVCOM Runs Directory
======================

Create an :file:`fvcom-runs/` directory for the VHFR FVCOM runs and populate it with:

.. code-block:: bash

    $ cd /nemoShare/MEOPAR/nowcast-sys/
    $ mkdir fvcom-runs
    $ chmod g+ws fvcom-runs
    $ cd fvcom-runs/
    $ cp ../FVCOM-VHFR-config/namelists/namelist.case.template namelist.case
    $ cp ../FVCOM-VHFR-config/namelists/namelist.grid.template namelist.grid
    $ cp ../FVCOM-VHFR-config/namelists/namelists/namelist.nesting.template namelist.nesting
    $ cp ../FVCOM-VHFR-config/namelists/namelist.netcdf.template namelist.netcdf
    $ cp ../FVCOM-VHFR-config/namelists/namelist.numerics.template namelist.numerics
    $ cp ../FVCOM-VHFR-config/namelists/namelist.obc.template namelist.obc
    $ cp ../FVCOM-VHFR-config/namelists/namelist.physics.template namelist.physics
    $ cp ../FVCOM-VHFR-config/namelists/namelist.restart.template namelist.restart
    $ cp ../FVCOM-VHFR-config/namelists/namelist.rivers.template namelist.rivers.x2
    $ cp ../FVCOM-VHFR-config/namelists/namelist.rivers.template namelist.rivers.r12
    $ cp ../FVCOM-VHFR-config/namelists/namelist.startup.hotstart.template namelist.startup.hotstart
    $ cp ../FVCOM-VHFR-config/namelists/namelist.station_timeseries.template namelist.station_timeseries
    $ cp ../FVCOM-VHFR-config/namelists/namelist.surface.template namelist.surface


Managing Compute Nodes
======================

Here are some useful bash loop one-liners for operating on collections of compute nodes.

If compute node instances are group-launched,
their hostnames can be set with:

.. code-block:: bash

    for n in {1..17}
    do
      echo nowcast${n}
      ssh nowcast${n} "sudo hostnamectl set-hostname nowcast${n}"
    done

Mount shared storage via NFS from head node:

.. code-block:: bash

    for n in {1..17}
    do
      echo nowcast${n}
      ssh nowcast${n} \
        "sudo mount -t nfs -o proto=tcp,port=2049 192.168.238.14:/MEOPAR /nemoShare/MEOPAR"
    done

Confirm whether or not :file:`/nemoShare/MEOPAR/` is a mount point:

.. code-block:: bash

    for n in {1..17}
    do
      echo nowcast${n}
      ssh nowcast${n} "mountpoint /nemoShare/MEOPAR"
    done

Confirm that :file:`/nemoShare/MEOPAR/` has the shared storage mounts:

.. code-block:: bash

    for n in {1..17}
    do
      echo nowcast${n}
      ssh nowcast${n} "ls -l /nemoShare/MEOPAR"
    done
