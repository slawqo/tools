#!/bin/env python3

import sys
import yaml


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Path to the projects.yaml file is required.")
        sys.exit(1)
    projects_yaml_path = sys.argv[1]
    with open(projects_yaml_path, "r") as projects_yaml:
        try:
            projects = yaml.safe_load(projects_yaml)
        except yaml.YAMLError as err:
            print(err)
            sys.exit(2)

    repos = set()
    for project in projects.values():
        for deliverable in project.get('deliverables', {}).values():
            deliverable_repos = deliverable.get('repos')
            for repo in deliverable_repos:
                repos.add(repo)

    for repo in repos:
        print(repo)
