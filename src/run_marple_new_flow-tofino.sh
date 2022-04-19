
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/marple_new_flow

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun-tofino_mute.sh $folder "marple_new_flow_equivalent_"$i"_canonicalizer" pred_raw
done
