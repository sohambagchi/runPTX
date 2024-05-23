#!/bin/bash

# iterate through all the directories within the current directory, cd into them, and run the run-all.sh script

for dir in */; do
    cd $dir
    ./run-all.sh
    cd ..
done