
folder=/home/xiangyug/ruijief/benchmarks/Domino_mutations/spam_detection

for ((i=1;i<11;i++)); do

  echo "running mutation "$i
  ./quickrun_mute.sh $folder "spam_detection_equivalent_"$i"_canonicalizer" pair
done
