#!/usr/bin/python
#
# Copyright (c) 2015 All rights reserved
# This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# 0.1: This script boots the VM1 and allocates IP address from Nova
# Later, the VM2 boots then execute cloud-init to ping VM1.
# After successful ping, both the VMs are deleted.
# 0.2: measure test duration and publish results under json format
# 0.3: add report flag to push results when needed
# 0.4: refactoring to match Test abstraction class

import argparse
import os
import sys
import time

import functest.core.testcase_base as testcase_base
import functest.utils.functest_constants as ft_constants
import functest.utils.functest_logger as ft_logger
import functest.utils.functest_utils as ft_utils


class DominoCases(testcase_base.TestcaseBase):
    DOMINO_REPO = ft_constants.DOMINO_REPO_DIR
    RESULTS_DIR = ft_constants.FUNCTEST_RESULTS_DIR
    logger = ft_logger.Logger("domino").getLogger()

    def __init__(self):
        super(DominoCases, self).__init__()
        self.project_name = "domino"
        self.case_name = "domino-multinode"

    def main(self, **kwargs):
        cmd = 'cd %s && ./tests/run_multinode.sh' % self.DOMINO_REPO
        log_file = os.path.join(self.RESULTS_DIR, "domino.log")
        start_time = time.time()

        ret = ft_utils.execute_command(cmd,
                                       output_file=log_file)

        stop_time = time.time()
        if ret == 0:
            self.logger.info("domino OK")
            status = 'PASS'
        else:
            self.logger.info("domino FAILED")
            status = "FAIL"

        # report status only if tests run (FAIL OR PASS)
        self.criteria = status
        self.start_time = start_time
        self.stop_time = stop_time
        self.details = {}

    def run(self):
        kwargs = {}
        return self.main(**kwargs)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--report",
                        help="Create json result file",
                        action="store_true")
    args = vars(parser.parse_args())
    domino = DominoCases()
    try:
        result = domino.main(**args)
        if result != testcase_base.TestcaseBase.EX_OK:
            sys.exit(result)
        if args['report']:
            sys.exit(domino.push_to_db())
    except Exception:
        sys.exit(testcase_base.TestcaseBase.EX_RUN_ERROR)
