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
import functest.utils.functest_constants as ft_constants


class CliTier:

    def __init__(self):
        CI_INSTALLER_TYPE = ft_constants.CI_INSTALLER_TYPE
        CI_SCENARIO = ft_constants.CI_SCENARIO
        testcases = ft_constants.FUNCTEST_TESTCASES_YAML
        self.tiers = tb.TierBuilder(CI_INSTALLER_TYPE, CI_SCENARIO, testcases)

    def list(self):
        summary = ""
        for tier in self.tiers.get_tiers():
            summary += ("    - %s. %s:\n\t   %s\n"
                        % (tier.get_order(),
                           tier.get_name(),
                           tier.get_test_names()))
        click.echo(summary)

    def show(self, tiername):
        tier = self.tiers.get_tier(tiername)
        if tier is None:
            tier_names = self.tiers.get_tier_names()
            click.echo("The tier with name '%s' does not exist. "
                       "Available tiers are:\n  %s\n" % (tiername, tier_names))
        else:
            click.echo(self.tiers.get_tier(tiername))

    def gettests(self, tiername):
        tier = self.tiers.get_tier(tiername)
        if tier is None:
            tier_names = self.tiers.get_tier_names()
            click.echo("The tier with name '%s' does not exist. "
                       "Available tiers are:\n  %s\n" % (tiername, tier_names))
        else:
            tests = tier.get_test_names()
            click.echo("Test cases in tier '%s':\n %s\n" % (tiername, tests))

    def run(self, tiername, noclean=False):
        if not os.path.isfile(ft_constants.ENV_FILE):
            click.echo("Functest environment is not ready. "
                       "Run first 'functest env prepare'")
        else:
            if noclean:
                cmd = ("python %s/functest/ci/run_tests.py "
                       "-n -t %s" % (ft_constants.FUNCTEST_REPO_DIR, tiername))
            else:
                cmd = ("python %s/functest/ci/run_tests.py "
                       "-t %s" % (ft_constants.FUNCTEST_REPO_DIR, tiername))
            ft_utils.execute_command(cmd)
