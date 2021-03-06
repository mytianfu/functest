#!/usr/bin/env python
#
# Copyright (c) 2015 Orange
# guyrodrigue.koffi@orange.com
# morgan.richomme@orange.com
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
#
# 0.1 (05/2015) initial commit
# 0.2 (28/09/2015) extract Tempest, format json result, add ceilometer suite
# 0.3 (19/10/2015) remove Tempest from run_rally
# and push result into test DB
#
""" tests configuration """

import json
import os
import re
import subprocess
import time

import argparse
import iniparse
import yaml

import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils
import functest.utils.openstack_utils as os_utils
import functest.utils.functest_constants as ft_constants

tests = ['authenticate', 'glance', 'cinder', 'heat', 'keystone',
         'neutron', 'nova', 'quotas', 'requests', 'vm', 'all']
parser = argparse.ArgumentParser()
parser.add_argument("test_name",
                    help="Module name to be tested. "
                         "Possible values are : "
                         "[ {d[0]} | {d[1]} | {d[2]} | {d[3]} | {d[4]} | "
                         "{d[5]} | {d[6]} | {d[7]} | {d[8]} | {d[9]} | "
                         "{d[10]} ] "
                         "The 'all' value "
                         "performs all possible test scenarios"
                         .format(d=tests))

parser.add_argument("-d", "--debug", help="Debug mode", action="store_true")
parser.add_argument("-r", "--report",
                    help="Create json result file",
                    action="store_true")
parser.add_argument("-s", "--smoke",
                    help="Smoke test mode",
                    action="store_true")
parser.add_argument("-v", "--verbose",
                    help="Print verbose info about the progress",
                    action="store_true")
parser.add_argument("-n", "--noclean",
                    help="Don't clean the created resources for this test.",
                    action="store_true")
parser.add_argument("-z", "--sanity",
                    help="Sanity test mode, execute only a subset of tests",
                    action="store_true")

args = parser.parse_args()


if args.verbose:
    RALLY_STDERR = subprocess.STDOUT
else:
    RALLY_STDERR = open(os.devnull, 'w')

""" logging configuration """
logger = ft_logger.Logger("run_rally-cert").getLogger()

RALLY_DIR = os.path.join(ft_constants.FUNCTEST_REPO_DIR,
                         ft_constants.RALLY_RELATIVE_PATH)
RALLY_SCENARIO_DIR = os.path.join(RALLY_DIR, "scenario")
SANITY_MODE_DIR = os.path.join(RALLY_SCENARIO_DIR, "sanity")
FULL_MODE_DIR = os.path.join(RALLY_SCENARIO_DIR, "full")
TEMPLATE_DIR = os.path.join(RALLY_SCENARIO_DIR, "templates")
SUPPORT_DIR = os.path.join(RALLY_SCENARIO_DIR, "support")
TEMP_DIR = os.path.join(RALLY_DIR, "var")
BLACKLIST_FILE = os.path.join(RALLY_DIR, "blacklist.txt")

FLAVOR_NAME = "m1.tiny"
USERS_AMOUNT = 2
TENANTS_AMOUNT = 3
ITERATIONS_AMOUNT = 10
CONCURRENCY = 4

RESULTS_DIR = os.path.join(ft_constants.FUNCTEST_RESULTS_DIR, 'rally')
TEMPEST_CONF_FILE = os.path.join(ft_constants.FUNCTEST_RESULTS_DIR,
                                 'tempest/tempest.conf')

RALLY_PRIVATE_NET_NAME = ft_constants.RALLY_PRIVATE_NET_NAME
RALLY_PRIVATE_SUBNET_NAME = ft_constants.RALLY_PRIVATE_SUBNET_NAME
RALLY_PRIVATE_SUBNET_CIDR = ft_constants.RALLY_PRIVATE_SUBNET_CIDR
RALLY_ROUTER_NAME = ft_constants.RALLY_ROUTER_NAME

GLANCE_IMAGE_NAME = ft_constants.GLANCE_IMAGE_NAME
GLANCE_IMAGE_FILENAME = ft_constants.GLANCE_IMAGE_FILENAME
GLANCE_IMAGE_FORMAT = ft_constants.GLANCE_IMAGE_FORMAT
GLANCE_IMAGE_PATH = os.path.join(ft_constants.FUNCTEST_DATA_DIR,
                                 GLANCE_IMAGE_FILENAME)
CINDER_VOLUME_TYPE_NAME = "volume_test"


class GlobalVariables:
    SUMMARY = []
    neutron_client = None
    network_dict = {}


def get_task_id(cmd_raw):
    """
    get task id from command rally result
    :param cmd_raw:
    :return: task_id as string
    """
    taskid_re = re.compile('^Task +(.*): started$')
    for line in cmd_raw.splitlines(True):
        line = line.strip()
        match = taskid_re.match(line)
        if match:
            return match.group(1)
    return None


def task_succeed(json_raw):
    """
    Parse JSON from rally JSON results
    :param json_raw:
    :return: Bool
    """
    rally_report = json.loads(json_raw)
    for report in rally_report:
        if report is None or report.get('result') is None:
            return False

        for result in report.get('result'):
            if result is None or len(result.get('error')) > 0:
                return False

    return True


def live_migration_supported():
    config = iniparse.ConfigParser()
    if (config.read(TEMPEST_CONF_FILE) and
            config.has_section('compute-feature-enabled') and
            config.has_option('compute-feature-enabled', 'live_migration')):
        return config.getboolean('compute-feature-enabled', 'live_migration')

    return False


def build_task_args(test_file_name):
    task_args = {'service_list': [test_file_name]}
    task_args['image_name'] = GLANCE_IMAGE_NAME
    task_args['flavor_name'] = FLAVOR_NAME
    task_args['glance_image_location'] = GLANCE_IMAGE_PATH
    task_args['glance_image_format'] = GLANCE_IMAGE_FORMAT
    task_args['tmpl_dir'] = TEMPLATE_DIR
    task_args['sup_dir'] = SUPPORT_DIR
    task_args['users_amount'] = USERS_AMOUNT
    task_args['tenants_amount'] = TENANTS_AMOUNT
    task_args['use_existing_users'] = False
    task_args['iterations'] = ITERATIONS_AMOUNT
    task_args['concurrency'] = CONCURRENCY

    if args.sanity:
        task_args['smoke'] = True
    else:
        task_args['smoke'] = args.smoke

    ext_net = os_utils.get_external_net(GlobalVariables.neutron_client)
    if ext_net:
        task_args['floating_network'] = str(ext_net)
    else:
        task_args['floating_network'] = ''

    net_id = GlobalVariables.network_dict['net_id']
    task_args['netid'] = str(net_id)

    auth_url = ft_constants.OS_AUTH_URL
    if auth_url is not None:
        task_args['request_url'] = auth_url.rsplit(":", 1)[0]
    else:
        task_args['request_url'] = ''

    return task_args


def get_output(proc, test_name):
    result = ""
    nb_tests = 0
    overall_duration = 0.0
    success = 0.0
    nb_totals = 0

    while proc.poll() is None:
        line = proc.stdout.readline()
        if args.verbose:
            result += line
        else:
            if ("Load duration" in line or
                    "started" in line or
                    "finished" in line or
                    " Preparing" in line or
                    "+-" in line or
                    "|" in line):
                result += line
            elif "test scenario" in line:
                result += "\n" + line
            elif "Full duration" in line:
                result += line + "\n\n"

        # parse output for summary report
        if ("| " in line and
                "| action" not in line and
                "| Starting" not in line and
                "| Completed" not in line and
                "| ITER" not in line and
                "|   " not in line and
                "| total" not in line):
            nb_tests += 1
        elif "| total" in line:
            percentage = ((line.split('|')[8]).strip(' ')).strip('%')
            try:
                success += float(percentage)
            except ValueError:
                logger.info('Percentage error: %s, %s' % (percentage, line))
            nb_totals += 1
        elif "Full duration" in line:
            duration = line.split(': ')[1]
            try:
                overall_duration += float(duration)
            except ValueError:
                logger.info('Duration error: %s, %s' % (duration, line))

    overall_duration = "{:10.2f}".format(overall_duration)
    if nb_totals == 0:
        success_avg = 0
    else:
        success_avg = "{:0.2f}".format(success / nb_totals)

    scenario_summary = {'test_name': test_name,
                        'overall_duration': overall_duration,
                        'nb_tests': nb_tests,
                        'success': success_avg}
    GlobalVariables.SUMMARY.append(scenario_summary)

    logger.debug("\n" + result)

    return result


def get_cmd_output(proc):
    result = ""

    while proc.poll() is None:
        line = proc.stdout.readline()
        result += line

    return result


def excl_scenario():
    black_tests = []

    try:
        with open(BLACKLIST_FILE, 'r') as black_list_file:
            black_list_yaml = yaml.safe_load(black_list_file)

        installer_type = ft_constants.CI_INSTALLER_TYPE
        deploy_scenario = ft_constants.CI_SCENARIO
        if (bool(installer_type) * bool(deploy_scenario)):
            if 'scenario' in black_list_yaml.keys():
                for item in black_list_yaml['scenario']:
                    scenarios = item['scenarios']
                    installers = item['installers']
                    if (deploy_scenario in scenarios and
                            installer_type in installers):
                        tests = item['tests']
                        black_tests.extend(tests)
    except:
        logger.debug("Scenario exclusion not applied.")

    return black_tests


def excl_func():
    black_tests = []
    func_list = []

    try:
        with open(BLACKLIST_FILE, 'r') as black_list_file:
            black_list_yaml = yaml.safe_load(black_list_file)

        if not live_migration_supported():
            func_list.append("no_live_migration")

        if 'functionality' in black_list_yaml.keys():
            for item in black_list_yaml['functionality']:
                functions = item['functions']
                for func in func_list:
                    if func in functions:
                        tests = item['tests']
                        black_tests.extend(tests)
    except:
        logger.debug("Functionality exclusion not applied.")

    return black_tests


def apply_blacklist(case_file_name, result_file_name):
    logger.debug("Applying blacklist...")
    cases_file = open(case_file_name, 'r')
    result_file = open(result_file_name, 'w')

    black_tests = list(set(excl_func() + excl_scenario()))

    include = True
    for cases_line in cases_file:
        if include:
            for black_tests_line in black_tests:
                if re.search(black_tests_line, cases_line.strip().rstrip(':')):
                    include = False
                    break
            else:
                result_file.write(str(cases_line))
        else:
            if cases_line.isspace():
                include = True

    cases_file.close()
    result_file.close()


def prepare_test_list(test_name):
    test_yaml_file_name = 'opnfv-{}.yaml'.format(test_name)
    scenario_file_name = os.path.join(RALLY_SCENARIO_DIR, test_yaml_file_name)

    if not os.path.exists(scenario_file_name):
        if args.sanity:
            scenario_file_name = os.path.join(SANITY_MODE_DIR,
                                              test_yaml_file_name)
        else:
            scenario_file_name = os.path.join(FULL_MODE_DIR,
                                              test_yaml_file_name)

        if not os.path.exists(scenario_file_name):
            logger.info("The scenario '%s' does not exist."
                        % scenario_file_name)
            exit(-1)

    logger.debug('Scenario fetched from : {}'.format(scenario_file_name))
    test_file_name = os.path.join(TEMP_DIR, test_yaml_file_name)

    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    apply_blacklist(scenario_file_name, test_file_name)
    return test_file_name


def file_is_empty(file_name):
    try:
        if os.stat(file_name).st_size > 0:
            return False
    except:
        pass

    return True


def run_task(test_name):
    #
    # the "main" function of the script who launch rally for a task
    # :param test_name: name for the rally test
    # :return: void
    #
    logger.info('Starting test scenario "{}" ...'.format(test_name))
    start_time = time.time()

    task_file = os.path.join(RALLY_DIR, 'task.yaml')
    if not os.path.exists(task_file):
        logger.error("Task file '%s' does not exist." % task_file)
        exit(-1)

    file_name = prepare_test_list(test_name)
    if file_is_empty(file_name):
        logger.info('No tests for scenario "{}"'.format(test_name))
        return

    cmd_line = ("rally task start --abort-on-sla-failure " +
                "--task {} ".format(task_file) +
                "--task-args \"{}\" ".format(build_task_args(test_name)))
    logger.debug('running command line : {}'.format(cmd_line))

    p = subprocess.Popen(cmd_line, stdout=subprocess.PIPE,
                         stderr=RALLY_STDERR, shell=True)
    output = get_output(p, test_name)
    task_id = get_task_id(output)
    logger.debug('task_id : {}'.format(task_id))

    if task_id is None:
        logger.error('Failed to retrieve task_id, validating task...')
        cmd_line = ("rally task validate " +
                    "--task {} ".format(task_file) +
                    "--task-args \"{}\" ".format(build_task_args(test_name)))
        logger.debug('running command line : {}'.format(cmd_line))
        p = subprocess.Popen(cmd_line, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, shell=True)
        output = get_cmd_output(p)
        logger.error("Task validation result:" + "\n" + output)
        return

    # check for result directory and create it otherwise
    if not os.path.exists(RESULTS_DIR):
        logger.debug('{} does not exist, we create it.'.format(RESULTS_DIR))
        os.makedirs(RESULTS_DIR)

    # write html report file
    report_html_name = 'opnfv-{}.html'.format(test_name)
    report_html_dir = os.path.join(RESULTS_DIR, report_html_name)
    cmd_line = "rally task report {} --out {}".format(task_id,
                                                      report_html_dir)

    logger.debug('running command line : {}'.format(cmd_line))
    os.popen(cmd_line)

    # get and save rally operation JSON result
    cmd_line = "rally task results %s" % task_id
    logger.debug('running command line : {}'.format(cmd_line))
    cmd = os.popen(cmd_line)
    json_results = cmd.read()
    report_json_name = 'opnfv-{}.json'.format(test_name)
    report_json_dir = os.path.join(RESULTS_DIR, report_json_name)
    with open(report_json_dir, 'w') as f:
        logger.debug('saving json file')
        f.write(json_results)

    with open(report_json_dir) as json_file:
        json_data = json.load(json_file)

    """ parse JSON operation result """
    status = "FAIL"
    if task_succeed(json_results):
        logger.info('Test scenario: "{}" OK.'.format(test_name) + "\n")
        status = "PASS"
    else:
        logger.info('Test scenario: "{}" Failed.'.format(test_name) + "\n")

    # Push results in payload of testcase
    if args.report:
        stop_time = time.time()
        logger.debug("Push Rally detailed results into DB")
        ft_utils.push_results_to_db("functest",
                                    "Rally_details",
                                    start_time,
                                    stop_time,
                                    status,
                                    json_data)


def main():

    GlobalVariables.nova_client = os_utils.get_nova_client()
    GlobalVariables.neutron_client = os_utils.get_neutron_client()
    cinder_client = os_utils.get_cinder_client()

    start_time = time.time()

    # configure script
    if not (args.test_name in tests):
        logger.error('argument not valid')
        exit(-1)

    GlobalVariables.SUMMARY = []

    volume_types = os_utils.list_volume_types(cinder_client,
                                              private=False)
    if not volume_types:
        volume_type = os_utils.create_volume_type(
            cinder_client, CINDER_VOLUME_TYPE_NAME)
        if not volume_type:
            logger.error("Failed to create volume type...")
            exit(-1)
        else:
            logger.debug("Volume type '%s' created succesfully..."
                         % CINDER_VOLUME_TYPE_NAME)
    else:
        logger.debug("Using existing volume type(s)...")

    image_exists, image_id = os_utils.get_or_create_image(GLANCE_IMAGE_NAME,
                                                          GLANCE_IMAGE_PATH,
                                                          GLANCE_IMAGE_FORMAT)
    if not image_id:
        exit(-1)

    logger.debug("Creating network '%s'..." % RALLY_PRIVATE_NET_NAME)
    GlobalVariables.network_dict = \
        os_utils.create_shared_network_full(RALLY_PRIVATE_NET_NAME,
                                            RALLY_PRIVATE_SUBNET_NAME,
                                            RALLY_ROUTER_NAME,
                                            RALLY_PRIVATE_SUBNET_CIDR)
    if not GlobalVariables.network_dict:
        exit(1)

    if args.test_name == "all":
        for test_name in tests:
            if not (test_name == 'all' or
                    test_name == 'vm'):
                run_task(test_name)
    else:
        logger.debug("Test name: " + args.test_name)
        run_task(args.test_name)

    report = ("\n"
              "                                                              "
              "\n"
              "                     Rally Summary Report\n"
              "\n"
              "+===================+============+===============+===========+"
              "\n"
              "| Module            | Duration   | nb. Test Run  | Success   |"
              "\n"
              "+===================+============+===============+===========+"
              "\n")
    payload = []
    stop_time = time.time()

    # for each scenario we draw a row for the table
    total_duration = 0.0
    total_nb_tests = 0
    total_success = 0.0
    for s in GlobalVariables.SUMMARY:
        name = "{0:<17}".format(s['test_name'])
        duration = float(s['overall_duration'])
        total_duration += duration
        duration = time.strftime("%M:%S", time.gmtime(duration))
        duration = "{0:<10}".format(duration)
        nb_tests = "{0:<13}".format(s['nb_tests'])
        total_nb_tests += int(s['nb_tests'])
        success = "{0:<10}".format(str(s['success']) + '%')
        total_success += float(s['success'])
        report += ("" +
                   "| " + name + " | " + duration + " | " +
                   nb_tests + " | " + success + "|\n" +
                   "+-------------------+------------"
                   "+---------------+-----------+\n")
        payload.append({'module': name,
                        'details': {'duration': s['overall_duration'],
                                    'nb tests': s['nb_tests'],
                                    'success': s['success']}})

    total_duration_str = time.strftime("%H:%M:%S", time.gmtime(total_duration))
    total_duration_str2 = "{0:<10}".format(total_duration_str)
    total_nb_tests_str = "{0:<13}".format(total_nb_tests)

    if len(GlobalVariables.SUMMARY):
        success_rate = total_success / len(GlobalVariables.SUMMARY)
    else:
        success_rate = 100
    success_rate = "{:0.2f}".format(success_rate)
    success_rate_str = "{0:<10}".format(str(success_rate) + '%')
    report += "+===================+============+===============+===========+"
    report += "\n"
    report += ("| TOTAL:            | " + total_duration_str2 + " | " +
               total_nb_tests_str + " | " + success_rate_str + "|\n")
    report += "+===================+============+===============+===========+"
    report += "\n"

    logger.info("\n" + report)
    payload.append({'summary': {'duration': total_duration,
                                'nb tests': total_nb_tests,
                                'nb success': success_rate}})

    if args.sanity:
        case_name = "rally_sanity"
    else:
        case_name = "rally_full"

    # Evaluation of the success criteria
    status = ft_utils.check_success_rate(case_name, success_rate)

    exit_code = -1
    if status == "PASS":
        exit_code = 0

    if args.report:
        logger.debug("Pushing Rally summary into DB...")
        ft_utils.push_results_to_db("functest",
                                    case_name,
                                    start_time,
                                    stop_time,
                                    status,
                                    payload)
    if args.noclean:
        exit(exit_code)

    if not image_exists:
        logger.debug("Deleting image '%s' with ID '%s'..."
                     % (GLANCE_IMAGE_NAME, image_id))
        if not os_utils.delete_glance_image(GlobalVariables.nova_client,
                                            image_id):
            logger.error("Error deleting the glance image")

    if not volume_types:
        logger.debug("Deleting volume type '%s'..."
                     % CINDER_VOLUME_TYPE_NAME)
        if not os_utils.delete_volume_type(cinder_client, volume_type):
            logger.error("Error in deleting volume type...")

    exit(exit_code)


if __name__ == '__main__':
    main()
