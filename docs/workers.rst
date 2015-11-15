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


.. _CreatingNowcastWorkers:

Creating Nowcast Workers
========================

Nowcast workers are Python modules that can be imported from :py:mod:`salishsea_tools.nowcast.workers`.
They are composed of some standard code to enable them to interface with the nowcast system messaging and logging framework,
and one or more functions to execute their task in the nowcast system.
Most of the standard code is centred around setup of a :py:class:`~SalishSeaTools.salishsea_tools.nowcast.nowcast_worker.NowcastWorker` object and executing method calls on it.
The worker object is an instance of the :py:class:`SalishSeaTools.salishsea_tools.nowcast.nowcast_worker.NowcastWorker` class.

Here is a skeleton example of a worker module showing the standard code.
It is explained,
line by line,
below.
Actual
(and obviously, more complicated)
worker modules can be found in :file:`tools/SalishSeaTools/salishsea_tools/nowcast/workers/`.

.. note::
    The skeleton code below describes :py:class:`~SalishSeaTools.salishsea_tools.nowcast.nowcast_worker.NowcastWorker`-based workers.
    Not all workers have been re-implemented to use :py:class:`~SalishSeaTools.salishsea_tools.nowcast.nowcast_worker.NowcastWorker`.


.. code-block:: python
    :linenos:

    # Copyright 2013-2015 The Salish Sea MEOPAR contributors
    # and The University of British Columbia

    # Licensed under the Apache License, Version 2.0 (the "License");
    # you may not use this file except in compliance with the License.
    # You may obtain a copy of the License at

    #    http://www.apache.org/licenses/LICENSE-2.0

    # Unless required by applicable law or agreed to in writing, software
    # distributed under the License is distributed on an "AS IS" BASIS,
    # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    # See the License for the specific language governing permissions and
    # limitations under the License.

    """Salish Sea NEMO nowcast ... worker.
    ...
    """
    import logging

    from .. import lib
    from ..nowcast_worker import NowcastWorker


    worker_name = lib.get_module_name()
    logger = logging.getLogger(worker_name)


    def main():
        worker = NowcastWorker(worker_name, description=__doc__)
        worker.run(worker_func, success, failure)


    def success(parsed_args):
        logger.info('success message')
        return 'success'


    def failure(parsed_args):
        logger.error('failure message')
        return 'failure'


    def worker_func(parsed_args, config):
        ...
        return checklist


    if __name__ == '__main__':
        main()

Lines 1 through 14 are our standard project copyright and license statement.
It uses :kbd:`#` comments rather than being enclosed in triple quotes to segregate it from the docstring which is used in automatic documentation generation and help text.

Lines 16 to 18 are the module's triple-quoted docstring.
As noted above,
it will appear in auto-generated documentation of the module.
For convenience we will also use the docstring as the description element of the worker's command-line help message,
although that can easily be changed if you prefer to put more details in the docstring than you want to appear in the help text.

The minimum set of imports that a worker needs are:

.. code-block:: python

    import logging

    from .. import lib
    from ..nowcast_worker import NowcastWorker

The :py:mod:`logging` module is a Python standard library module that provides the mechanism that we use to print output about the worker's progress and status to the log file or the screen,
effectively developer-approved print statements on steroids :-)
The :ref:`salishsea_tools.nowcast.lib` is our collection of functions that are used across workers.
If you find yourself writing the same function in more than one worker it should probably be generalized and included in :py:mod:`lib`.
The :py:class:`NowcastWorker` class provides the interface to the nowcast framework.
We use relative imports for :py:mod:`lib` and :py:class:`NowcastWorker` because they are defined within the :py:mod:`SalishSeaNowcast` package.

Obviously you will need to import whatever other modules your worker needs for its task.

Next up are 2 module level variables:

.. code-block:: python

    worker_name = lib.get_module_name()
    logger = logging.getLogger(worker_name)

:py:data:`worker_name` is used to identify the source of logging messages,
and messages exchanged between the worker and the nowcast manager process.
:py:func:`~SalishSeaTools.salishsea_tools.nowcast.lib.get_module_name` provides the worker's module name stripped of its path and :kbd:`.py` suffix.

:py:data:`logger` is our interface to the Python standard library logging framework and we give this module's instance the worker's name.

Python scoping rules make module level variables available for use in any functions in the module without passing them as arguments but assigning new values to them elsewhere in the module will surely mess things up.


The :py:func:`main` Function
----------------------------

The :py:func:`main` function is where our worker gets down to work.
It is called when the worker is run from the command line by virtue of the

.. code-block:: python

    if __name__ == '__main__':
        main()

stanza at the end of the module.

The minimum possible :py:func:`main` function is shown in lines 32 to 34:

.. code-block:: python

    def main():
        worker = NowcastWorker(worker_name, description=__doc__)
        worker.run(worker_func, success, failure)

First,
we create an instance of the :py:class:`~SalishSeaTools.salishsea_tools.nowcast.nowcast_worker.NowcastWorker` class that we call,
by convention,
:py:data:`worker`.
The :py:class:`~SalishSeaTools.salishsea_tools.nowcast.nowcast_worker.NowcastWorker` constructor takes 2 arguments:

* the :py:data:`worker_name` that we defined as a module-level variable above
* a :py:data:`description` string that is used as the description element of the worker's command-line help message;
  here we use the worker's module docstring
  (that is automatically stored in the :py:data:`__doc__` module-level variable)

  The description part of the help message is the paragraph after the usage,
  for example:

  .. code-block:: bash

      (nowcast)$ python -m salishsea_tools.nowcast.workers.download_weather --help

  .. code-block:: none

      usage: python -m salishsea_tools.nowcast.workers.download_weather
             [-h] [--debug] [--yesterday] config_file {18,00,12,06}

      Salish Sea NEMO nowcast weather model dataset download worker. Download the
      GRIB2 files from today's 00, 06, 12, or 18 EC GEM 2.5km HRDPS operational
      model forecast.

      ...

See the :py:class:`nowcast.nowcast_worker.NowcastWorker` documentation for details of the :py:class:`~SalishSeaTools.salishsea_tools.nowcast.nowcast_worker.NowcastWorker` object's contructor arguments,
other attributes,
and methods.

Second,
we call the :py:meth:`run` method on the :py:data:`worker` to do the actual work.
The :py:meth:`run` method takes 3 function names as arguments:

* :py:data:`worker_func` is the name of the function that does the worker's job
* :py:data:`success` is the name of the function to be called when the worker finishes successfully
* :py:data:`failure` is the name of the function to be called when the worker fails

All 3 functions must be defined in the worker module.
Their required call signatures and return values are described below.

It is also possible to add command-line arguments to the :py:data:`worker`.
See :ref:`ExtendingTheCommandLineParser`.


:py:func:`success` and :py:func:`failure` Functions
---------------------------------------------------

The :py:func:`success` function is called when the worker successfully completes its task.
It is used to generate the message that is sent to the nowcast manager process to indicate the worker's success so that the nowcast automation can proceed to the next appropriate worker(s).
A minimal :py:func:`success` function is shown in lines 34 through 36:

.. code-block:: python

    def success(parsed_args):
        logger.info('success message')
        return 'success'

The name of the function is :py:func:`success` by convention,
but it could be anything provided that it is the 2nd argument passed to the :py:meth:`worker.run` method.

The :py:func:`success` function must accept exactly 1 argument,
named :py:data:`parsed_args` by convention.
It is an :py:obj:`argparse.Namespace` object that has the worker's command-line argument names and values as attributes.
Even if your :py:func:`success` function does not use :py:data:`parsed_args` it must still be included in the function definition.

.. TODO::
    Add a link to the Python docs for argparse.Namespace

The :py:func:`success` function should send a message via :py:meth:`logger.info` to the logging system that describes the worker's success.

The :py:func:`success` function must return a string that is a key registered for the worker in the :kbd:`msg_types` section of the :ref:`NowcastConfigFile`.
The returned key specifies the message type that is sent to the nowcast manager process to indicate the worker's success.

Here is a more sophisticated example of a :py:func:`success` function from the :py:mod:`download_weather` worker:

.. code-block:: python

    def success(parsed_args):
        logger.info(
            'weather forecast {.forecast} downloads complete'
            .format(parsed_args))
        msg_type = 'success {.forecast}'.format(parsed_args)
        return msg_type

The :py:func:`failure` function is very similar to the :py:func:`success` function except that it is called if the worker fails to complete its task.
It is used to generate the message that is sent to the nowcast manager process to indicate the worker's failure so that appropriate notifications can be produced and/or remedial action(s) taken.
A minimal :py:func:`failure` function is shown on lines 39 through 41:

.. code-block:: python

    def failure(parsed_args):
        logger.error('failure message')
        return 'failure'

The name of the function is :py:func:`failure` by convention,
but it could be anything provided that it is the 3rd argument passed to the :py:meth:`worker.run` method.

Like the :py:func:`success` function,
the :py:func:`failure` function must accept exactly 1 argument,
named :py:data:`parsed_args` by convention.
It is an :py:obj:`argparse.Namespace` object that has the worker's command-line argument names and values as attributes.
Even if your :py:func:`failure` function does not use :py:data:`parsed_args` it must still be included in the function definition.

The :py:func:`failure` function should send a message via :py:meth:`logger.error` to the logging system that describes the worker's failure.

The :py:func:`failure` function must return a string that is a key registered for the worker in the :kbd:`msg_types` section of the :ref:`NowcastConfigFile`.
The returned key specifies the message type that is sent to the nowcast manager process to indicate the worker's failure.


Doing the Work
--------------

Lines 44 through 46 show the required call signature and return value for the function that is called to do the worker's task:

.. code-block:: python

    def worker_func(parsed_args, config):
        ...
        return checklist

The name of the function can be anything provided that it is the 1st argument passed to the :py:meth:`worker.run` method.
Ideally,
the function name should be descriptive of the worker's task.
If you can't think of anything else,
you can use the name of the worker module.

The function must accept exactly 2 arguments:

* The 1st argument is named :py:data:`parsed_args` by convention.
  It is an :py:obj:`argparse.Namespace` object that has the worker's command-line argument names and values as attributes.
  Even if your function does not use :py:data:`parsed_args` it must still be included in the function definition.

* The 2nd argument is named :py:data:`config` by convention.
  It is a Python :py:obj:`dict` containing the keys and values read from the :ref:`NowcastConfigFile`.
  Even if your function does not use :py:data:`config` it must still be included in the function definition.

The function must return a Python :py:obj:`dict`,
known as :py:data:`checklist` by convention.
:py:data:`checklist` must contain at least 1 key/value pair that provides information about the worker's successful completion.
:py:data:`checklist` is sent to the nowcast manager process as the payload of the worker's success message.
A simple example of a :py:data:`checklist` from the :py:mod:`download_weather` worker is:

.. code-block:: python

    checklist = {'{} forecast'.format(forecast): True}

which just indicates that the particular forecast download was successful.
A more sophisticated :py:data:`checklist` such as the one produced by the :py:mod:`SalishSeaTools.salishsea_tools.nowcast.workers.get_NeahBay_ssh` worker contains multiple keys and lists of filenames.

The function whose name is passed as the 1st argument to the :py:meth:`worker.run` method can be a driver function that calls other functions in the worker module to subdivide the worker task into smaller,
more readable,
and more testable sections.
By convention,
such "2nd level" functions are marked as private by prefixing their names with the :kbd:`_` (underscore) character;
e.g. :py:func:`_calc_date`.
This is in line with the Python language convention that functions and methods that start with an underscore should not be called outside the module in which they are defined.

The worker should send messages to the logging system that indicate its progress.
Messages sent via :py:meth:`logger.info` appear in the :file:`nowcast.log` file.
Info level logging should be used for "high level" progress messages,
and preferrably not used inside loops.
Messages logged via :py:meth:`logger.debug` can be used for more detailed logging.
Those messages appear in the :file:`nowcast.debug.log` file.

If a worker function encounters an expected error condition
(a file download failure or timeout, for example)
it should send a message to the logging system via :py:meth:`logger.critical` and raise a :py:exc:`salishsea_tools.nowcast.lib.WorkerError` exception.
Here is an example that handles an empty downloaded file in the :py:mod:`download_weather` worker:

.. code-block:: python

    if size == 0:
        logger.critical('Problem, 0 size file {}'.format(fileURL))
        raise lib.WorkerError

This section has only outlined the basic code structure and conventions for writing nowcast workers.
The best way to learn now to write a new worker is by studying the code in the existing worker modules in :file:`SalishSeaTools/salishsea_tools/nowcast/workers/`.


.. _ExtendingTheCommandLineParser:

Extending the Command-line Parser
---------------------------------

If you need to add a command-line argument to a worker you can do so by calling the :py:meth:`worker.arg_parser.add_argument` method.
Here is an example from the :py:mod:`get_NeahBay_ssh` worker:

.. code-block:: python

    def main():
        worker = NowcastWorker(worker_name, description=__doc__)
        worker.arg_parser.add_argument(
            'run_type', choices=set(('nowcast', 'forecast', 'forecast2')),
            help='Type of run to execute.'
        )
        worker.run(get_NeahBay_ssh, success, failure)

The :py:meth:`worker.arg_parser.add_argument` method takes the same arguments as the Python standard library :py:meth:`argparse.ArgumentParser.add_argument` method.

.. TODO::
    Add a link to the Python docs for argparse.ArgumentParser.add_argument

.. note::
    When the :py:class:`~SalishSeaTools.salishsea_tools.nowcast.nowcast_worker.NowcastWorker` object is set up its base command-line parser is created as :py:attr:`worker.arg_parser`.
    That parser provides help messages,
    and handles the :option:`config_file` argument,
    and the :option:`--debug` option.

For workers that require a :option:`run-date` command-line option,
use this pattern:

.. code-block:: python

    salishsea_today = arrow.now('Canada/Pacific').floor('day')
    worker.arg_parser.add_argument(
        '--run-date', type=lib.arrow_date,
        default=salishsea_today,
        help='''
        Date of the run to make runoff file for; use YYYY-MM-DD format.
        Defaults to {}.
        '''.format(salishsea_today.format('YYYY-MM-DD')),
    )

The above pattern causes :py:data:`parsed_args.run_date` to have a value which is an :py:class:`arrow.Arrow` object with the given date,
:kbd:`00:00:00` as its time part,
and :kbd:`Canada/Pacific` as its timezone.
If the :option:`--run-date` option is not specified :py:data:`parsed_args.run_date` will have the present date in :kbd:`Canada/Pacific` as its date.
