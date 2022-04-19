
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/marple_tcp_nmo

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun_mute.sh $folder "marple_tcp_nmo_equivalent_"$i"_canonicalizer" pred_raw
done
