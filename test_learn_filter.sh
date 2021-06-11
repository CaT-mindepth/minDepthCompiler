#!/bin/bash
echo " * testing learn_filter..."
set -x 
cd src/
python3 main.py ../stable_benchmarks/learn_filter.in ../_test_learn_filter_out ../learn_filter.p4 > ../compile_debug.log
set +x
echo " * compilation complete. p4 file at learn_filter.p4 and log at compile_debug.log"

