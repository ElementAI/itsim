ITsim
=====

Welcome to the ITSim documentation
----------------------------------

ITSim is a discrete event simulation of IT infrastructures.

.. toctree::
   :hidden:

   overview
   build_instructions
   networks
   internet
   endpoints

The source code is all available on `Github <https://github.com/ElementAI/itsim>`_ and it can be built on your machine by following the :doc:`build_instructions`

In addition, take a gander at the :doc:`overview` to get an understanding of our language design from the top level.

How-to
-------

An ITsim-based simulation first involves the descriptive instantiation of the
IT infrastructure of interest. This can be then further spiced up by
incorporating *users* of the IT resources, as well as *intruders* making their way
to some of the assets for fun and profit. The following articles illustrate
how to perform this set-up, and then run the simulation.

#. Setting up :doc:`networks <networks>`
#. Adding :doc:`endpoints <endpoints>` to a network
#. Setting up :doc:`internet hosts <internet>`
#. Running the simulation -- **TBD**

.. _networks: :doc:networks

Module reference
----------------

.. toctree::
   :maxdepth: 5

   modules/itsim
