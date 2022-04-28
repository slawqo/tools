#!/bin/bash

repos_list=$1

time_period=$2  # days

for repo in $(cat ${repos_list}); do
    dest_file_name=$(echo ${repo} | awk -F'/' '{print $1}')
    repo_avg=$(python3 rechecks.py --no-cache --newer-than ${time_period} --branch master --project ${repo} --only-average)
    if [ "$repo_avg" != "No patches found!" ]; then
        echo "${repo}: ${repo_avg}"
    fi
done
