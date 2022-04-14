# MinDepthCompiler



## Running

To use the Domino backend and generate a `.json` file: (using the `learn_filter` benchmark as an example)
First run the preprocessor (https://github.com/CaT-mindepth/CaT-Preprocessor) using 
```
./domino learn_filter.c learn_filter.in
```
Then run the code generator:
```
cd src/
python3 ./main-domino.py ./learn_filter.in _learn_filter_out learn_filter.json # it will output to learn_filter.json with intermediate sketch files located at _learn_filter_out
# cleanup:
rm -rf _learn_filter_out
```

Some examples for generated output can be found in the `generated_fpga_outputs` directory.

<br><br>


To use the Tofino backend:
```
cd src/
python3 ./main-single.py ./blue_decrease.in _blue_decrease_out  blue_decrease.json
```

Multi-table mode (TODO)


## Intro

This project is divided into two programs: a preprocessor (https://github.com/CaT-mindepth/CaT-Preprocessor) that takes in a Domino `.c` program and outputs it into a `.in` file, and a compiler (`src/main.py`) that takes in a `.in` file, an argument specifying the folder in which intermediate sketch files can be written to, and an argument specifying the output filename. 

To call the preprocessor, run
```
./domino <Domino .c file> <output .in file>
```
To run the main compiler, you need to take a `.in` file generated by the preprocessor, and run
```
cd src/ && python3 ./main.py <path to .in file> <path to a directory for temporary files> <path to output file>
```
Along the way, the compiler will use the Graphviz `dot` command to generate and display the mid-end dependency graph and components graph as PDFs.

## Python Dependencies
Python version: 3.5 or up
```
PLY  
networkx  
graphviz  
overrides 
jinja2 
gurobipy
```
Note that only having the pip3 graphviz package is not enough; please make sure the Graphviz `dot`-language compiler is installed on your system and available in the `PATH`. 

To install `dot` on Ubuntu:
```
sudo apt install graphviz
```

To install `dot` on macOS/OSX: Make sure to have Homebrew installed, and run
```
brew install graphviz
```
` 
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
