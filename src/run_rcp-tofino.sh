
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/rcp

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun-tofino_mute.sh $folder "rcp_equivalent_"$i"_canonicalizer" pred_raw
done
