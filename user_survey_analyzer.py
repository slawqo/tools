#!/bin/env python

import csv
import collections
import sys

from prettytable import PrettyTable


TOTAL_COUNT = "All Responses"
RESPONSE_TITLE = "Response"
COUNT_TITLE = "Users"
PERCENTAGE_TITLE = "Percentage of Responses"


def get_data_in_lists(csv_file):
    # This returns data in list of lists in format like:
    # [['Question 1', 'Answear', 'Answear', ... ],
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


def convert_data_to_dicts(data):
    questions = {}
    for row in data:
        header = row[0]
        questions[header] = collections.defaultdict(int)
        for responses in row[1:]:
            for response in responses.split("|"):
                questions[header][response] += 1
            questions[header][TOTAL_COUNT] += 1
    return questions


def print_data(data):
    for question, responses in data.items():
        print(f"Question: {question}")
        all_responses = responses.pop(TOTAL_COUNT)
        print(f"Total number of responses: {all_responses}")
        table = PrettyTable(
            [RESPONSE_TITLE, COUNT_TITLE, PERCENTAGE_TITLE])
        table._max_width = {
            RESPONSE_TITLE: 100,
            COUNT_TITLE: 10,
            PERCENTAGE_TITLE: 20}
        table.align[RESPONSE_TITLE] = "l"
        table.align[COUNT_TITLE] = "c"
        table.align[PERCENTAGE_TITLE] = "c"

        for response, counter in responses.items():
            percentage = "{:.0f}".format(100 * counter / all_responses)
            table.add_row([response, counter, percentage])
        print(table)


if __name__ == '__main__':
    csv_file = sys.argv[1]
    data_lists = get_data_in_lists(csv_file)
    data_dict = convert_data_to_dicts(data_lists)
    print_data(data_dict)
