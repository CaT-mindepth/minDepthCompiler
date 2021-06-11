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
