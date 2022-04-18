
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/dns_ttl_change

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun_mute.sh $folder "dns_ttl_change_equivalent_"$i nested_ifs
done
