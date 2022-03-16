#!/usr/bin/env python3

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

import matplotlib.pyplot as plt
from prettytable import PrettyTable


# Script based on Assaf Muller's script
# https://github.com/assafmuller/gerrit_time_to_merge/blob/master/time_to_merge.py


def log_debug(msg):
    if args.verbose:
        print(msg)


def exec_cmd(command):
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()

    return output, error


def get_parser():
    parser = argparse.ArgumentParser(
        description='Get from gerrit informations about how many builds failed '
                    'on patches before it was finally merged.'
                    'Note that the app uses a caching system - Query results '
                    'are stored in the cache dir with no timeout. Subsequent '
                    'runs of the app against the same project and time '
                    'will not query Gerrit, but will use the local results. '
                    'As the cache has no timeout, its contents '
                    'must be deleted manually to get a fresh query.')
    parser.add_argument(
        '--newer-than',
        help='Only look at patches merged in the last so and so days.')
    parser.add_argument(
        '--time-window',
        default='week',
        help='Count average number of recheck per "week" (default), "month" '
             'or "year".')
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help="Don't use cached results, always download new ones.")
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Be more verbose.')
    parser.add_argument(
        '--plot',
        action='store_true',
        help='Generate graphs directly by script.')
    parser.add_argument(
        '--report-format',
        default='human',
        help=('Format in which results will be printed. '
              'Default value: "human" '
              'Possible values: "human", "csv"'))
    parser.add_argument(
        '--branch',
        default='master',
        help='Branch to check. For example stable/stein.')
    parser.add_argument(
        '--project',
        default=None,
        help='The OpenStack project to query. For example openstack/neutron.')

    return parser.parse_args()


def _get_file_from_query(query):
    return query.replace('/', '_')


def get_json_data_from_cache(query):
    try:
        os.mkdir('cache')
    except OSError:
        pass

    query = _get_file_from_query(query)
    if query in os.listdir('cache'):
        with open('cache/%s' % query) as query_file:
            return json.load(query_file)


def put_json_data_in_cache(query, data):
    try:
        os.mkdir('cache')
    except OSError:
        pass
    query = _get_file_from_query(query)
    with open('cache/%s' % query, 'w') as query_file:
        json.dump(data, query_file)


def get_json_data_from_query(query):
    data = []
    start = 0

    while True:
        gerrit_cmd = (
            'ssh -p 29418 review.opendev.org gerrit query --format=json '
            '--current-patch-set --comments --start %(start)s %(query)s' %
            {'start': start,
             'query': query})
        result, error = exec_cmd(gerrit_cmd)

        if error:
            print(error)
            sys.exit(1)

        result = result.decode('utf-8')
        lines = result.split('\n')[:-2]
        data += [json.loads(line) for line in lines]

        if not data:
            print('No patches found!')
            sys.exit(1)

        log_debug('Found metadata for %s more patches, %s total so far' %
                  (len(lines), len(data)))
        start += len(lines)
        more_changes = json.loads(result.split('\n')[-2])['moreChanges']
        if not more_changes:
            break

    data = sorted(data, key=lambda x: x['createdOn'])
    return data


def get_submission_timestamp(patch):
    try:
        # Not all patches have approvals data
        approvals = patch['currentPatchSet']['approvals']
    except KeyError:
        return patch['lastUpdated']

    # Weirdly enough some patches don't have submission data.
    # Take lastUpdated instead.
    return next(
        (approval['grantedOn'] for approval in approvals if
         approval['type'] == 'SUBM'), patch['lastUpdated'])


def get_points_from_data(data):

    points = []
    build_failed_regex = re.compile(
        r"Build failed \(\w+ pipeline\)")
    ps_regex = re.compile(r"Patch Set (\d+)\:")

    for patch in data:
        last_ps = int(patch['currentPatchSet']['number'])
        build_failures = 0
        for comment in patch['comments']:
            if comment['reviewer']['name'].lower() != 'zuul':
                continue
            msg = comment['message']
            re_ps = re.search(ps_regex, msg)
            if not re_ps:
                log_debug("No patch set found for comment: %s" % msg)
                continue
            if int(re_ps.group(1)) != last_ps:
                log_debug("Comment was not for last patch set. Skipping")
                continue

            if build_failed_regex.search(msg):
                build_failures += 1

        points.append(
            {'id': patch['id'],
             'merged': get_submission_timestamp(patch),
             'build_failures': build_failures})
    points = sorted(points, key = lambda i: i['merged'])
    return points


AVG_DATA_POINTS = None


def get_avg_failures(points, time_window):
    if time_window == 'week':
        return get_avg_failures_per_week(points)
    elif time_window == 'month':
        return get_avg_failures_per_month(points)
    else:
        return get_avg_failures_per_year(points)


def get_avg_failures_per_week(points):
    global AVG_DATA_POINTS
    if AVG_DATA_POINTS is None:
        data = {}
        for point in points:
            point_date = datetime.date.fromtimestamp(point['merged'])
            point_year, point_week, _ = point_date.isocalendar()
            point_key = "%s-%s" % (point_year, point_week)
            log_debug("Patch %s merged %s (week %s)" % (
                point['id'], point_date, point_key))
            if point_key not in data.keys():
                data[point_key] = [point['build_failures']]
            else:
                data[point_key].append(point['build_failures'])

        AVG_DATA_POINTS = {k: sum(v)/len(v) for k, v in data.items()}

    return AVG_DATA_POINTS


def get_avg_failures_per_month(points):
    global AVG_DATA_POINTS
    if AVG_DATA_POINTS is None:
        data = {}
        for point in points:
            point_date = datetime.date.fromtimestamp(point['merged'])
            point_key = "%s-%s" % (point_date.year, point_date.month)
            log_debug("Patch %s merged %s (week %s)" % (
                point['id'], point_date, point_key))
            if point_key not in data.keys():
                data[point_key] = [point['build_failures']]
            else:
                data[point_key].append(point['build_failures'])

        AVG_DATA_POINTS = {k: sum(v)/len(v) for k, v in data.items()}

    return AVG_DATA_POINTS


def get_avg_failures_per_year(points):
    global AVG_DATA_POINTS
    if AVG_DATA_POINTS is None:
        data = {}
        for point in points:
            point_date = datetime.date.fromtimestamp(point['merged'])
            point_key = point_date.year
            log_debug("Patch %s merged %s (week %s)" % (
                point['id'], point_date, point_key))
            if point_key not in data.keys():
                data[point_key] = [point['build_failures']]
            else:
                data[point_key].append(point['build_failures'])

        AVG_DATA_POINTS = {k: sum(v)/len(v) for k, v in data.items()}

    return AVG_DATA_POINTS


def plot_avg_rechecks(points, time_window):
    plot_points = get_avg_failures(points, time_window)
    x_values = list(plot_points.keys())
    y_values = list(plot_points.values())
    plt.plot(x_values, y_values,
             label=('Average number of failed builds '
                    'before patch merge per %s' % time_window))
    plt.xlabel('patch merge time')
    plt.ylabel('number of failed builds')
    plt.legend()
    plt.show()


def print_avg_rechecks(points, time_window):
    plot_points = get_avg_failures(points, time_window)
    if args.report_format == 'csv':
        print_avg_as_csv(plot_points, time_window)
    else:
        print_avg_as_human_readable(plot_points, time_window)


def print_avg_as_csv(points, time_window):
    print("%s,Average number of failed builds" % time_window)
    for week, value in points.items():
        print('%s,%s' % (week, value))


def print_avg_as_human_readable(points, time_window):
    table = PrettyTable()
    table.field_names = [time_window, "Rechecks"]
    for week, value in points.items():
        table.add_row([week, round(value, 2)])
    print(table)


if __name__ == '__main__':
    args = get_parser()
    query = "status:merged branch:%s " % args.branch
    if args.project:
        query += 'project:%s ' % args.project
    if args.newer_than:
        query += ' -- -age:%dd' % int(args.newer_than)

    data = None
    if not args.no_cache:
        log_debug("Using cached data...")
        data = get_json_data_from_cache(query)
    if not data:
        log_debug("Fetching data from gerrit with query: %s" % query)
        data = get_json_data_from_query(query)
        put_json_data_in_cache(query, data)

    points = get_points_from_data(data)

    if not points:
        error = 'Could not parse points from data. It is likely that the ' \
                'createdOn timestamp of the patches found is bogus.'
        print(error)
        sys.exit(1)

    if args.plot:
        plot_avg_rechecks(points, args.time_window)
    print_avg_rechecks(points, args.time_window)
