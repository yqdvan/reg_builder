#!/bin/bash

# Author : Duan Yuanqiang
# Version: v0.1
#          Initial version

TOOLDIR=`dirname $0 | sed -e "s/^\(.*\/arsoc\/\).*$/\1/"` 
 echo ${TOOLDIR}

module unload python3
module load python/3.8.8
python3 ${TOOLDIR}/bin/reg_builder.py $*
