#!/bin/bash
# Substep 0 field-geometry check: 20 cases (grids 7 and 11, d 4 and 6, lengths 1 to 4 cells), one process each.
cd /root/sp0
mkdir -p out
for i in $(seq 0 19); do
  nohup python sparse_field_geometry.py --only "$i" --out "out/case_$i.json" > "out/case_$i.log" 2>&1 &
done
wait
touch out/finished
