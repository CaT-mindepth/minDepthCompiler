#!/bin/bash
echo " * testing sampling..."
set -x 
cd src/
python3 main.py ../stable_benchmarks/sampling.in ../_test_sampling_out ../sampling.p4 > ../compile_debug.log
set +x
echo " * compilation complete. p4 file at sampling.p4 and log at compile_debug.log"

