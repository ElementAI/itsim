ITsim Build Instructions
========================

Building ITSim from scratch
---------------------------

To build ITSim on UNIX, first make sure you have `Pipenv <https://pipenv.readthedocs.io/en/latest/>`_ installed, then follow the steps below

#. Clone the repository with ``git clone https://github.com/ElementAI/itsim.git``

#. CD into the directory with ``cd itsim``

#. Set up all of the dependencies with ``pipenv install --dev``

#. Verify that the setup was successful with ``pipenv run ./runtests``

#. Optionally build the project locally to get your own copy of the documentation ``pipenv run python setup.py install``
