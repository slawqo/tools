Plot time of the CI jobs' execution
===================================

This simple script gets data about CI jobs execution time from the
https://review.opendev.org and plot's average time of the job execution per week
of the year.
It always checks only last Zuul's comment made for the change.

Installation
------------

To make this script working its dependencies has to be installed:

.. code-block::

  $ pip install -r requirements.txt

It also requires one of the ``matplotlib`` backends. For example pyqt5:

.. code-block::

  $ pip install pyqt5

See https://matplotlib.org/stable/devel/dependencies.html#dependencies for
details.
