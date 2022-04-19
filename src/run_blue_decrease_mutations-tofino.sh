
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/blue_decrease

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun-tofino_mute.sh $folder "blue_decrease_equivalent_"$i"_canonicalizer" sub

done
