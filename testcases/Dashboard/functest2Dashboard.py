#!/usr/bin/python
#
# Copyright (c) 2015 Orange
# morgan.richomme@orange.com
#
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# This script is used to get data from test DB
# and format them into a json format adapted for a dashboard
#
# v0.1: basic example
#
import logging
import argparse
import pprint
import dashboard_utils
import os
import yaml

pp = pprint.PrettyPrinter(indent=4)

parser = argparse.ArgumentParser()
parser.add_argument("repo_path", help="Path to the repository")
parser.add_argument("-d", "--debug", help="Debug mode",  action="store_true")
args = parser.parse_args()

""" logging configuration """
logger = logging.getLogger('config_functest')
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
if args.debug:
    ch.setLevel(logging.DEBUG)
else:
    ch.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s -\
                                 %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

if not os.path.exists(args.repo_path):
    logger.error("Repo directory not found '%s'" % args.repo_path)
    exit(-1)

with open(args.repo_path+"testcases/config_functest.yaml") as f:
    functest_yaml = yaml.safe_load(f)
f.close()

""" global variables """
# Directories
HOME = os.environ['HOME']+"/"
REPO_PATH = args.repo_path
TEST_DB = functest_yaml.get("results").get("test_db_url")


def main():
    try:
        logger.info("Functest test result generation for dashboard")

        # TODO create the loop to provide all the json files
        logger.debug("Retrieve all the testcases from DB")
        test_cases = dashboard_utils.get_testcases(TEST_DB, "functest")

        # TODO to be refactor once graph for Tempest, rally and ODL ready
        # Do it only for vPing in first stage
        for case in test_cases:
            logger.debug("Generate " + case + " json files")
            dashboard_utils.generateJson('functest', case, TEST_DB)

        logger.info("Functest json files for dashboard successfully generated")
    except:
        logger.error("Impossible to generate json files for dashboard")


if __name__ == '__main__':
    main()