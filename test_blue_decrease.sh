#!/bin/bash
echo " * testing blue_decrease..."
set -x 
cd src/
python3 main.py ../stable_benchmarks/blue_decrease.in ../_test_blue_decrease_out ../blue_decrease.p4 > ../compile_debug.log
set +x
echo " * compilation complete. p4 file at blue_decrease.p4 and log at compile_debug.log"

