#!/usr/bin/env bash
set -euo pipefail
project=$1
out=$2
{
    for parent in "$project" "$project/systemc-llm-issue153" \
        /public/home/yuzelu/Melodydt; do
        find "$parent" -maxdepth 2 -type d -iname '*llama*' -print
    done
} | sort -u > "$out/llama-paths.txt"
while IFS= read -r directory; do
    if [[ -f "$directory/config.json" ]]; then
        echo "$directory"
        find "$directory" -maxdepth 2 -type f \( -name '*.safetensors' \
            -o -name '*safetensors.index.json' -o -name 'tokenizer.json' \) -print
    fi
done < "$out/llama-paths.txt" > "$out/llama-candidates.txt"
cat "$out/llama-candidates.txt"
