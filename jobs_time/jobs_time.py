#!/usr/bin/env python3

import argparse
import collections
import datetime
import json
import os
import re
import requests
import subprocess
import sys

import matplotlib.pyplot as plt

# Script based on Assaf Muller's script
# https://github.com/assafmuller/gerrit_time_to_merge/blob/master/time_to_merge.py
# and using also Dan Smith's script
# https://gist.githubusercontent.com/kk7ds/5edbfacb2a341bb18df8f8f32d01b37c/raw/c505de9f5cfa58dcbb37bf5630104ceaaa97574f/job_timer.py

HOST = 'https://review.opendev.org'


def get_parser():
    parser = argparse.ArgumentParser(
        description='Take from gerrit list of changes merged in a given '
                    'time period.')
    parser.add_argument('start')
    parser.add_argument('end')
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Be more verbose.')
    parser.add_argument(
        '--branch',
        default='master',
        help='Branch to check. For example stable/stein.')
    parser.add_argument(
        '--project',
        help='The OpenStack project to query. For example openstack/neutron.')
    parser.add_argument(
        '--status',
        default=None,
        help="Status of changes, e.g. merged or open.")
    parser.add_argument(
        '--job-name-regex',
        default=None,
        help='Regex of the name of the job(s) which will be displayed')

    return parser.parse_args()


def get_gerrit_json(path):
    r = requests.get('%s/%s' % (HOST, path))
    return json.loads(r.content.split(b'\n', 1)[1])


def get_changes(query):
    changes = []
    start = 0
    patches = get_gerrit_json(query)

    changes = [p['_number'] for p in patches]

    if not changes:
        print('No patches found!')
        sys.exit(1)

    return changes


def get_latest_zuul_change_comments(change):
    messages = get_gerrit_json('changes/%s/messages' % change)
    for message in reversed(messages):
        if message['author']['username'] == 'zuul' \
           and ('Verified+1' in message['message'] or \
                'Verified-1' in message['message']):
            print('Chose zuul comment from PS %s on change %s' % (
                message['_revision_number'], change))
            return message['message'], get_comment_week(message)
    return None, None


def get_comment_week(message):
    comment_date = message.get('date')
    # 2021-06-10 15:15:00.000000000
    comment_date = comment_date.split(".")[0]
    _date = datetime.datetime.strptime(comment_date, "%Y-%m-%d %H:%M:%S")
    year, week, _ = _date.isocalendar()
    return "%s-%s" % (year, week)


def parse_human_time(timestr):
    sec = 0
    for piece in timestr.split():
        suffix = piece[-1]
        amount = int(piece[:-1])
        if suffix == 's':
            sec += amount
        elif suffix == 'm':
            sec += 60 * amount
        elif suffix == 'h':
            sec += 3600 * amount
        else:
            print('Unhandled suffix %s in %s' % (suffix, piece))
    return sec


def parse_job_info(zuul_msg):
    jobs = {}
    last = None
    for line in zuul_msg.split('\n'):
        if line.startswith('-'):
            _dash, job, url, _colon, status, _in, time = (
                line.split(' ', 6))
            if '(' in time:
                time, voting = time.rsplit(' ', 1)
            else:
                voting = None
            jobs[job] = (url, status, parse_human_time(time), voting)
    return jobs


def get_summary(changes, job_name_pattern=None):
    job_name_re = None
    if job_name_pattern:
        job_name_re = re.compile(job_name_pattern)
    summary = {}
    for change in changes:
        msg, week = get_latest_zuul_change_comments(change)
        if not msg or not week:
            print("No Zuul data found for change %s. Skipping it." % change)
            continue
        jobinfo = parse_job_info(msg)
        for job_name, info in jobinfo.items():
            if not job_name_re or job_name_re.match(job_name):
                job_time = info[2]
                if job_name not in summary:
                    summary[job_name] = collections.defaultdict(list)
                summary[job_name][week].append(job_time)
    return summary


def plot_jobs(job_data):
    plt.xlabel('year-week of the comment')
    plt.ylabel('avg job time [seconds]')

    for job_name, job_data in jobs_data.items():
        x_values = []
        y_values = []
        points = []
        for week, values in job_data.items():
            x = week
            y = sum(values) / len(values)
            points.append((x, y))
        points = sorted(points, key=lambda x: x[0])
        x_values = [p[0] for p in points]
        y_values = [p[1] for p in points]
        plt.plot(x_values, y_values,
                 label='Average time of the job %s' % job_name)
    plt.legend()
    plt.show()


if __name__ == '__main__':
    args = get_parser()
    query = ("/changes/?q=branch:%(branch)s+"
             "after:%(start)s+before:%(end)s" % {
                'branch': args.branch, 'start': args.start, 'end': args.end})
    if args.project:
        query += "+project:%s" % args.project
    if args.status:
        query += "+is:%s" % args.status

    print("Query: %s" % query)
    changes = get_changes(query)
    print("Found %s changes matching requested condition." % len(changes))
    jobs_data = get_summary(changes, args.job_name_regex)
    plot_jobs(jobs_data)
