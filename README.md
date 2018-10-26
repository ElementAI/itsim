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
