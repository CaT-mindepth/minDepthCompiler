# MinDepthCompiler

## Python Dependencies
PLY  
networkx  
graphviz  
overrides 
jinja2 
gurobipy

## Non-python dependencies
Sketch-1.7.6

## Running the code

Go to the src directory ("cd src").

Use the command "python3 preprocessor.py \<input Domino program\> \<output file\>" to generate the preprocessed code.    

Use the command "python3 main.py \<input preprocessed file\> \<output directory\>" to generate code by querying Sketch. Sketch input files will be created in \<output directory\>.

## Currently passing tests

 - `sampling`: To run, `cd src/ && python3 ./main.py ../benchmarks/sampling/samplin.in _test_sampling_out/`. The output p4 program will be printed in stdout. (TODO: We will add a command line option to specify where to output the P4 program. The intermediate Sketch input/outputs are located in the `_test_sampling_out` subfolder.
 - `blue_decrease`: To run, `cd src/ && python3 ./preprocessor.py ../benchmarks/blue_decrease.c ./blue_decrease.in && python3 ./main.py ./blue_decrease.in _test_blue_decrease_out`. 
 - `stateful_fw`: To run, `cd src/ && python3 ./main.py ../benchmarks/stateful_fw/stateful_fw.in _test_stateful_fw_out`.
 - `learn_filter`: To run, `cd src/ && python3 ./main.py ../benchmarks/learn_filter/learn_filter.in _test_learn_filter_out`.

## Project structure
This is a developmental fork of Divya's repository at https://github.com/divya-urs/minDepthCompiler. We periodically merge commits into that repository, and all issues are reported at the stable repo: https://github.com/divya-urs/minDepthCompiler/issues. All source code are located in `src/`. Benchmarks (tests) are located in `benchmarks/`. The program `src/preprocessor.py` takes in a Domino `.c` file and converts it into a `.in` file, used as input for the main compiler `src/main.py`. The main compiler at `src/main.py` currently takes in a `.in` file, outputs intermediate Sketch files to a user-specified folder location, and prints out the P4 program in stdout. It is WIP to add a command line arg for the main program to export P4 code to a user-specified file, as well as specifying loglevel / having better debug messages.

## Refactoring
Some refactoring is being done to the compiler at `new_src/`. The main idea is to refactor everything into transformation and analysis passes that operate on the components graph in the mid-end, and the ALU dependency graph in the codegen. There will also be a pass manager that schedules all the passes. This is on the back-burner as we are still fixing various issues involved with compiling everything in `benchmarks/` folder correctly.
