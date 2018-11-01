#!/bin/bash

# Go through the documentation build process without tampering with any existing files

UUID=$(cat /proc/sys/kernel/random/uuid)
TDOCS_BKUP="sphinx-source-modules.runtestsbackup.temp.$UUID"
TDOCS_MODULES="sphinx/source/modules"
# Include dotted files in globbing
shopt -s dotglob
# Make a backup folder
mkdir $TDOCS_BKUP
# Back up everything that is currently in the modules folder
if [ -e $TDOCS_MODULES ]
then
    mv $TDOCS_MODULES $TDOCS_BKUP
fi
# Create a fresh folder
mkdir $TDOCS_MODULES
# Build and compile the document tree
sphinx-apidoc itsim -METf -o $TDOCS_MODULES && make -C sphinx html
# Compile the document tree
# Check for and record a failure
SUCCESS=$?
# Delete the document tree
rm -r $TDOCS_MODULES
# Replace anything that was backed up
if [ -e $TDOCS_BKUP/modules ]
then
    mkdir $TDOCS_MODULES
    if [ -e $TDOCS_BKUP/modules/* ]
    then
        mv -n $TDOCS_BKUP/modules/* $TDOCS_MODULES
    fi
fi
# Clean up
rm -r $TDOCS_BKUP
# Report a failure or die happy
exit $SUCCESS
