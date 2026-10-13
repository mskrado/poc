#!/usr/bin/env bash
# Log load average and available memory every 15 s while run.py is running (shared box => noisy wall times).
out=${1:-results/env_samples.csv}
echo "time,load1,load5,mem_available_mb,top_other_process" > "$out"
while pgrep -f "run.py" >/dev/null; do
  top=$(ps -eo pcpu,comm --sort=-pcpu | awk 'NR>1 && $2!="llama-server" && $2!="ollama" {print $2":"$1; exit}')
  echo "$(date +%T),$(cut -d' ' -f1,2 /proc/loadavg | tr ' ' ','),$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo),$top" >> "$out"
  sleep 15
done
