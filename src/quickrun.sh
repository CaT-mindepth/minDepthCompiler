#!/bin/bash

# set -x

export DOMINO=/home/xiangyug/ruijief/CaT-Preprocessor/

echo "directory: "$1", program name: "$2". Grammar: "$3". Continue?"
read -n 1

$DOMINO/domino $1/$2.c > $1/$2.in
echo "------------------------------"
echo "Preprocessing done. Continue?"
read -n 1

python3 main-domino.py --eval $1/$2.in $1/$2_out $1/$2.json $3

