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

## Testing

To run tests on one of the passing benchmarks, simply go and locate the `test_*.sh` files in the main directory and run it in the main directory. The script will tell you where to find the generated `.p4` file.

## Running the code

Go to the src directory ("cd src").

Use the command "python3 preprocessor.py \<input Domino program\> \<output file\>" to generate the preprocessed code.    

Use the command "python3 main.py \<input preprocessed file\> \<output directory\>" to generate code by querying Sketch. Sketch input files will be created in \<output directory\>.

## Currently passing tests
If there is a corrsponding `.sh` file in the main directory, then the test is passing. All tests are located in the `stable_benchmarks/` folder.
## Project structure
This is a developmental fork of Divya's repository at https://github.com/divya-urs/minDepthCompiler. We periodically merge commits into that repository, and all issues are reported at the stable repo: https://github.com/divya-urs/minDepthCompiler/issues. All source code are located in `src/`. Benchmarks (tests) are located in `benchmarks/`. The program `src/preprocessor.py` takes in a Domino `.c` file and converts it into a `.in` file, used as input for the main compiler `src/main.py`. The main compiler at `src/main.py` currently takes in a `.in` file, outputs intermediate Sketch files to a user-specified folder location, and prints out the P4 program in stdout. It is WIP to add a command line arg for the main program to export P4 code to a user-specified file, as well as specifying loglevel / having better debug messages.

## Refactoring
Some refactoring is being done to the compiler at `new_src/`. The main idea is to refactor everything into transformation and analysis passes that operate on the components graph in the mid-end, and the ALU dependency graph in the codegen. There will also be a pass manager that schedules all the passes. This is on the back-burner as we are still fixing various issues involved with compiling everything in `benchmarks/` folder correctly.
