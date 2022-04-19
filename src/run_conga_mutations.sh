
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/conga

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun_mute.sh $folder "conga_equivalent_"$i"_canonicalizer" pair
done
