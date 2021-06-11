#!/bin/bash
echo " * testing stateful_fw..."
set -x 
cd src/
python3 main.py ../stable_benchmarks/stateful_fw.in ../_test_stateful_fw_out ../stateful_fw.p4 > ../compile_debug.log
python3 main.py ../stable_benchmarks/stateful_fw.in ../_test_stateful_fw_out ../stateful_fw.p4 > ../compile_debug.log

set +x
echo " * compilation complete. p4 file at stateful_fw.p4 and log at compile_debug.log"

