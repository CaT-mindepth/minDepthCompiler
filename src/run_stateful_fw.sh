
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/stateful_fw

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun_mute.sh $folder "stateful_fw_equivalent_"$i pred_raw
done
