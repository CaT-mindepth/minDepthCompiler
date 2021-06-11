#!/bin/bash
echo " * testing marple_new_flow..."
set -x 
cd src/
python3 main.py ../stable_benchmarks/marple_new_flow.in ../_test_marple_new_flow_out ../marple_new_flow.p4 > ../compile_debug.log
set +x
echo " * compilation complete. p4 file at marple_new_flow.p4 and log at compile_debug.log"

