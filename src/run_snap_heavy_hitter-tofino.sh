
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/snap_heavy_hitter

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun-tofino_mute.sh $folder "snap_heavy_hitter_equivalent_"$i"_canonicalizer" pair
done
