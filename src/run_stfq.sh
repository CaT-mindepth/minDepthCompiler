
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/stfq

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun_mute.sh $folder "stfq_equivalent_"$i"_canonicalizer" nested_ifs
done
