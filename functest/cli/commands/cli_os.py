#!/usr/bin/env python
#
# jose.lausuch@ericsson.com
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
#


import os

import click

import functest.utils.functest_utils as ft_utils
import functest.utils.openstack_clean as os_clean
import functest.utils.openstack_snapshot as os_snapshot
import functest.utils.functest_constants as ft_constants


OPENSTACK_RC_FILE = ft_constants.OPENSTACK_CREDS
OPENSTACK_SNAPSHOT_FILE = ft_constants.OPENSTACK_SNAPSHOT_FILE


class CliOpenStack:

    def __init__(self):
        self.os_auth_url = ft_constants.OS_AUTH_URL
        self.endpoint_ip = None
        self.endpoint_port = None
        if self.os_auth_url is not None:
            self.endpoint_ip = self.os_auth_url.rsplit("/")[2].rsplit(":")[0]
            self.endpoint_port = self.os_auth_url.rsplit("/")[2].rsplit(":")[1]

    def ping_endpoint(self):
        if self.os_auth_url is None:
            click.echo("Source the OpenStack credentials first '. $creds'")
            exit(0)
        response = os.system("ping -c 1 " + self.endpoint_ip + ">/dev/null")
        if response == 0:
            return 0
        else:
            click.echo("Cannot talk to the endpoint %s\n" % self.endpoint_ip)
            exit(0)

    def show_credentials(self):
        for key, value in os.environ.items():
            if key.startswith('OS_'):
                click.echo("{}={}".format(key, value))

    def fetch_credentials(self):
        if os.path.isfile(OPENSTACK_RC_FILE):
            answer = raw_input("It seems the RC file is already present. "
                               "Do you want to overwrite it? [y|n]\n")
            while True:
                if answer.lower() in ["y", "yes"]:
                    break
                elif answer.lower() in ["n", "no"]:
                    return
                else:
                    answer = raw_input("Invalid answer. Please type [y|n]\n")

        CI_INSTALLER_TYPE = ft_constants.CI_INSTALLER_TYPE
        if CI_INSTALLER_TYPE is None:
            click.echo("The environment variable 'INSTALLER_TYPE' is not"
                       "defined. Please export it")
        CI_INSTALLER_IP = ft_constants.CI_INSTALLER_IP
        if CI_INSTALLER_IP is None:
            click.echo("The environment variable 'INSTALLER_IP' is not"
                       "defined. Please export it")
        cmd = ("%s/releng/utils/fetch_os_creds.sh -d %s -i %s -a %s"
               % (ft_constants.REPOS_DIR,
                  OPENSTACK_RC_FILE,
                  CI_INSTALLER_TYPE,
                  CI_INSTALLER_IP))
        click.echo("Fetching credentials from installer node '%s' with IP=%s.."
                   % (CI_INSTALLER_TYPE, CI_INSTALLER_IP))
        ft_utils.execute_command(cmd, verbose=False)

    def check(self):
        self.ping_endpoint()
        cmd = ft_constants.FUNCTEST_REPO_DIR + "/functest/ci/check_os.sh"
        ft_utils.execute_command(cmd, verbose=False)

    def snapshot_create(self):
        self.ping_endpoint()
        if os.path.isfile(OPENSTACK_SNAPSHOT_FILE):
            answer = raw_input("It seems there is already an OpenStack "
                               "snapshot. Do you want to overwrite it with "
                               "the current OpenStack status? [y|n]\n")
            while True:
                if answer.lower() in ["y", "yes"]:
                    break
                elif answer.lower() in ["n", "no"]:
                    return
                else:
                    answer = raw_input("Invalid answer. Please type [y|n]\n")

        click.echo("Generating Openstack snapshot...")
        os_snapshot.main()

    def snapshot_show(self):
        if not os.path.isfile(OPENSTACK_SNAPSHOT_FILE):
            click.echo("There is no OpenStack snapshot created. To create "
                       "one run the command "
                       "'functest openstack snapshot-create'")
            return
        with open(OPENSTACK_SNAPSHOT_FILE, 'r') as yaml_file:
            click.echo("\n%s"
                       % yaml_file.read())

    def clean(self):
        self.ping_endpoint()
        if not os.path.isfile(OPENSTACK_SNAPSHOT_FILE):
            click.echo("Not possible to clean OpenStack without a snapshot. "
                       "This could cause problems. "
                       "Run first the command "
                       "'functest openstack snapshot-create'")
            return
        os_clean.main()
