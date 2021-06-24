#!/bin/bash
set -x
for domino_program in `ls ../multiple_domino_programs | grep '\.c'`; do
  echo "../multiple_domino_programs/"$domino_program >> domino_programs.txt
done
