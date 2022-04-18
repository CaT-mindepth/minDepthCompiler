
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/flowlets

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun_mute.sh $folder "flowlets_equivalent_"$i pred_raw
done
