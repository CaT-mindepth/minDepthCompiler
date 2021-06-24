#!/bin/bash
set -x
for cprog in `ls | grep '\.c'`; do
  python3 ../src/preprocessor.py $cprog $cprog".in"
done
