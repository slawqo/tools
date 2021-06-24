import json
import pprint
import sys
import requests

HOST = 'https://review.opendev.org'
ZUUL = 'https://zuul.opendev.org'
JOBCACHE = {}

def get_gerrit_json(path):
    r = requests.get('%s/%s' % (HOST, path))
    return json.loads(r.content.split(b'\n', 1)[1])


def get_latest_zuul_change_comments(change):
    messages = get_gerrit_json('changes/%s/messages' % change)
    for message in reversed(messages):
        if message['author']['username'] == 'zuul' \
           and ('Verified+1' in message['message'] or \
                'Verified-1' in message['message']):
            print('Chose zuul comment from PS %s on change %s' % (
                message['_revision_number'], change))
            return message['message']


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


def make_human_time(sec):
    timestr = []
    if sec > 3600:
        timestr.append('%ih' % (sec / 3600))
        sec %= 3600
    if sec > 60:
        timestr.append('%im' % (sec / 60))
        sec %= 60

    timestr.append('%is' % sec)

    return ' '.join(timestr)


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


def get_zuul_job(jobname):
    global JOBCACHE
    if jobname not in JOBCACHE:
        r = requests.get('%s/api/tenant/openstack/job/%s' % (
            ZUUL, jobname))
        try:
            JOBCACHE[jobname] = r.json()[0]
        except Exception as e:
            print('Failed to fetch or parse job info for %s: %s' % (
                jobname, e))
            JOBCACHE[jobname] = {'nodeset': {'nodes': []}}
    return JOBCACHE[jobname]


def get_zuul_nodes(jobname):
    while True:
        jobdef = get_zuul_job(jobname)
        if 'nodeset' in jobdef:
            return len(jobdef['nodeset']['nodes'])
        if 'parent' not in jobdef:
            raise Exception(
                '%s has no parent and nodes not found yet' % jobname)
        jobname = jobdef['parent']


def do_summary(change):
    msg = get_latest_zuul_change_comments(change)
    jobinfo = parse_job_info(msg)
    total_time = 0
    total_nodes = 0
    for job, info in jobinfo.items():
        job_time = info[2]
        nodes = get_zuul_nodes(job)
        total_nodes += nodes
        print('Job %s takes %i nodes for %s, total %s' % (
            job, nodes, make_human_time(job_time),
            make_human_time(job_time * nodes)))
        if nodes == 0:
            print(' ^--- no job info for this job, leaked time! ---^')
        total_time += (nodes * job_time)

    print('Total time %s' % make_human_time(total_time))
    print('Total nodes is %i' % total_nodes)


if __name__ == '__main__':
    do_summary(sys.argv[1])
