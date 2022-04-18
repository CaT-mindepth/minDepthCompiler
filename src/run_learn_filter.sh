
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/learn_filter

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun_mute.sh $folder "learn_filter_equivalent_"$i"_canonicalizer" raw
done
