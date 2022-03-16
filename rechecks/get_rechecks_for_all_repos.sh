#!/bin/bash

repos_list=$1
dest_path=$2

time_period=365  # days

for repo in $(cat ${repos_list}); do
    echo "Getting data for ${repo}..."
    dest_file_name=$(echo ${repo} | awk -F'/' '{print $2}')
    python3 rechecks.py --no-cache --newer-than ${time_period} --time-window week --branch master --project ${repo} --report-format csv > ${dest_path}/${dest_file_name}_${time_period}.csv
done
