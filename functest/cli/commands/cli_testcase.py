#!/usr/bin/env python
#
# jose.lausuch@ericsson.com
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
#

""" global variables """

import os

import click

import functest.ci.tier_builder as tb
import functest.utils.functest_utils as ft_utils
import functest.utils.functest_vacation as vacation
import functest.utils.functest_constants as ft_constants


class CliTestcase:

    def __init__(self):
        CI_INSTALLER_TYPE = ft_constants.CI_INSTALLER_TYPE
        CI_SCENARIO = ft_constants.CI_SCENARIO
        testcases = ft_constants.FUNCTEST_TESTCASES_YAML

        self.tiers = tb.TierBuilder(CI_INSTALLER_TYPE, CI_SCENARIO, testcases)

    def list(self):
        summary = ""
        for tier in self.tiers.get_tiers():
            for test in tier.get_tests():
                summary += (" %s\n" % test.get_name())
        click.echo(summary)

    def show(self, testname):
        description = self.tiers.get_test(testname)
        if description is None:
            click.echo("The test case '%s' does not exist or is not supported."
                       % testname)

        click.echo(description)

    def run(self, testname, noclean=False):
        if testname == 'vacation':
            vacation.main()
        elif not os.path.isfile(ft_constants.ENV_FILE):
            click.echo("Functest environment is not ready. "
                       "Run first 'functest env prepare'")
        else:
            if noclean:
                cmd = ("python %s/functest/ci/run_tests.py "
                       "-n -t %s" % (ft_constants.FUNCTEST_REPO_DIR, testname))
            else:
                cmd = ("python %s/functest/ci/run_tests.py "
                       "-t %s" % (ft_constants.FUNCTEST_REPO_DIR, testname))
            ft_utils.execute_command(cmd)
