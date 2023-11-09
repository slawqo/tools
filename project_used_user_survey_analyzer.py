#!/bin/env python

import csv
import collections
import sys

from prettytable import PrettyTable

PROJECT_NAME = "Project"
PRODUCTION = "Production"
TESTING = "Testing"
INTERESTED = "Interested"


def get_data_in_lists(csv_file):
    # This returns data in list of lists in format like:
    # [['Project', 'Answear', 'Answear', ... ],
    #  ['Question 2', 'Answear', 'Answear', ... ]]

    result_data = []
    with open(csv_file) as data:
        raw_data = list(csv.reader(data, delimiter=',', quotechar='"'))
        result_data = [[question] for question in raw_data[0]]
        for row in raw_data[1:]:
            for i, element in enumerate(row):
                if element:
                    result_data[i].append(element)
    return result_data


def get_projects_data(data):
    projects = {}
    for row in data:
        project_name = row[0]
        projects[project_name] = collections.defaultdict(int)
        for response in row[1:]:
            projects[project_name][response] += 1
    return projects


def print_data(data):
    table = PrettyTable(
        [PROJECT_NAME, PRODUCTION, TESTING, INTERESTED])
    table._max_width = {
        PROJECT_NAME: 100,
        PRODUCTION: 20,
        TESTING: 20,
        INTERESTED: 20}
    for project, usage_data in data.items():
        table.add_row([
            project.replace("ProjectsUsed - ", ""),
            usage_data.get(PRODUCTION, 0),
            usage_data.get(TESTING, 0),
            usage_data.get(INTERESTED, 0)
        ])
    print(table)


if __name__ == '__main__':
    csv_file = sys.argv[1]
    data_lists = get_data_in_lists(csv_file)
    projects_data_dict = get_projects_data(data_lists)
    print_data(projects_data_dict)
