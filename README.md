# ITsim -- Discrete event simulation of IT infrastructures

[![CircleCI](https://circleci.com/gh/ElementAI/itsim/tree/master.svg?style=svg)](https://circleci.com/gh/ElementAI/itsim/tree/master)

Full documentation is here: https://itsim.readthedocs.io

Everything in the class_diagram folder was produced using [Papyrus](https://www.eclipse.org/papyrus/), an open-source product of the [Eclipse Foundation](https://www.eclipse.org/). It can be downloaded from [their website](https://www.eclipse.org/papyrus/download.html).

To install on Linux:

1) Go to the section for the "Latest Released RCP" and select your package version (these files were created with the 64-bit Linux version 4.0.0, available [here](https://www.eclipse.org/downloads/download.php?file=/modeling/mdt/papyrus/rcp/photon/4.0.0/papyrus-photon-4.0.0-linux64.tar.gz))
2) Download the .tar.gz file and move it into a folder for installation
3) Unzip the file in the installation directory with `tar -xzvf papyrus-*.tar.gz`
4) Optionally create a link to the new executable with `ln -s Papyrus/papyrus papyrus`
5) Call `Papyrus/papyrus` or `./papyrus` depending on whether you made the link in order to run the program
6) Create a new project and use File -> Import -> General -> File System, then choose the files in class_diagram to load them in to the editor

## Log level meaning

1. **CRITICAL** -- An unrecoverable error condition has been encountered.
   - Expect things to go boom.
   - In any case, discard all telemetry generated beyond this message.
   - This occurrence should be investigated so as to determine whether it has
     been caused by the simulated model or by ITsim routines. In the latter
     case, submit a bug report; any data collected from the simulation that
     you can share would help.
1. **ERROR** -- An error condition has been encountered, and this condition
   will either be fixed, recovered or tolerated.
   - The simulation should keep running.
   - Telemetry beyond this message is likely good, but should be treated as
     suspicious.
   - This occurrence should be investigated so as to determine whether it has
     been caused by the simulated model or by ITsim routines. In the latter
     case, submit a bug report; any data collected from the simulation that
     you can share would help.
1. **WARNING** -- An anomalous condition has been encountered, but this is
   very unlikely to represent a problem.
   - This occurrence should be investigated so as to determine whether it
     stems from a bug, either in the simulated model or in ITsim routines. In
     the latter cases, submit a bug report; any data collected from the
     simulation that you can share would help.
1. **INFO** -- Default log level. Reports information regarding simulation
   progress that is meaningful to the users of a model.
1. **DEBUG** -- Reports information regarding the micro behaviour of ITsim
   code in context of the user's model that is meaningful for ITsim
   maintainers. This is typically useful when running a model after an error
   condition to investigate its root cause.
