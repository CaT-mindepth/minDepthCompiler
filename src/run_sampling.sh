
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/sampling

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun_mute.sh $folder "sampling_equivalent_"$i"_canonicalizer" if_else_raw
done
