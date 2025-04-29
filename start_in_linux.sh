#!/bin/bash


TOOLDIR=“./”

module unload python3
module load python/3.8.8
python3 ${TOOLDIR}/bin/reg_builder.py $*
