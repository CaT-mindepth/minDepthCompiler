
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/blue_increase

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun-tofino_mute.sh $folder "blue_increase_equivalent_"$i"_canonicalizer" pred_raw
done
