# run all the .out files in the directory and write their output to a .txt file with the same name

mem=$(basename "$(pwd)" | cut -d'_' -f2)

MEM_TYPES=("GPU" "CPU" "UM")

for file in *.out; do
    for mem_type in "${MEM_TYPES[@]}"; do
        echo "Running $file with $mem_type"
        ./runPTX 1 $mem $mem_type $file  > ${file%.out}_${mem_type}.txt
    done
done
