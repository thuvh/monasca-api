# Copyright 2018 SUSE
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
CLI interface for monasca status commands.
https://governance.openstack.org/tc/goals/stein/upgrade-checkers.html
"""

from __future__ import print_function
import sys
import textwrap
import traceback

# enum comes from the enum34 package if python < 3.4, else it's stdlib
import enum
import prettytable

# TODO(joadavis): when it makes sense and has been refined, consider using the
# oslo_upgradecheck which started from Nova and was split out through
# https://github.com/cybertron/oslo.upgradecheck/tree/master/oslo_upgradecheck

def _(message):
    # TODO(joadavis): dummy out localization for now
    return message


class UpgradeCheckCode(enum.IntEnum):
    """These are the status codes for the monasca-status upgrade check command
    and internal check commands.
    """

    # All upgrade readiness checks passed successfully and there is
    # nothing to do.
    SUCCESS = 0

    # At least one check encountered an issue and requires further
    # investigation. This is considered a warning but the upgrade may be OK.
    WARNING = 1

    # There was an upgrade status check failure that needs to be
    # investigated. This should be considered something that stops an upgrade.
    FAILURE = 2


UPGRADE_CHECK_MSG_MAP = {
    UpgradeCheckCode.SUCCESS: _('Success'),
    UpgradeCheckCode.WARNING: _('Warning'),
    UpgradeCheckCode.FAILURE: _('Failure'),
}


class UpgradeCheckResult(object):
    """Class used for 'monasca-status upgrade check' results.

    The 'code' attribute is an UpgradeCheckCode enum.
    The 'details' attribute is a translated message generally only used for
    checks that result in a warning or failure code. The details should provide
    information on what issue was discovered along with any remediation.
    """

    def __init__(self, code, details=None):
        super(UpgradeCheckResult, self).__init__()
        self.code = code
        self.details = details


class UpgradeCommands(object):
    """Commands related to upgrades.

    Initial set of checks are very simple, but can grow over time
    to check items like database schema and other dependencies.
    """
    def _check_nothing(self):
        # TODO(joadavis): what is a useful check?
        return UpgradeCheckResult(UpgradeCheckCode.SUCCESS)


    # The format of the check functions is to return an UpgradeCheckResult
    # object with the appropriate UpgradeCheckCode and details set. If the
    # check hits warnings or failures then those should be stored in the
    # returned UpgradeCheckResult's "details" attribute. The summary will
    # be rolled up at the end of the check() function.
    _upgrade_checks = {
        # Added in Stein, stub for future checks
        _('Nothing'): _check_nothing,
    }

    def _get_details(self, upgrade_check_result):
        if upgrade_check_result.details is not None:
            # wrap the text on the details to 60 characters
            return '\n'.join(textwrap.wrap(upgrade_check_result.details, 60,
                                           subsequent_indent='  '))

    def check(self):
        """Performs checks to see if the deployment is ready for upgrade.

        These checks are expected to be run BEFORE services are restarted with
        new code. These checks also require access to potentially all of the
        Monasca services.

        :returns: UpgradeCheckCode
        """
        return_code = UpgradeCheckCode.SUCCESS
        # This is a list if 2-item tuples for the check name and it's results.
        check_results = []
        # Sort the checks by name so that we have predictable test results.
        for name in sorted(self._upgrade_checks.keys()):
            func = self._upgrade_checks[name]
            result = func(self)
            # store the result of the check for the summary table
            check_results.append((name, result))
            # we want to end up with the highest level code of all checks
            if result.code > return_code:
                return_code = result.code

        # We're going to build a summary table that looks like:
        # +----------------------------------------------------+
        # | Upgrade Check Results                              |
        # +----------------------------------------------------+
        # | Check: Cells v2                                    |
        # | Result: Success                                    |
        # | Details: None                                      |
        # +----------------------------------------------------+
        # | Check: Placement API                               |
        # | Result: Failure                                    |
        # | Details: There is no placement-api endpoint in the |
        # |          service catalog.                          |
        # +----------------------------------------------------+
        t = prettytable.PrettyTable([_('Upgrade Check Results')],
                                    hrules=prettytable.ALL)
        t.align = 'l'
        for name, result in check_results:
            cell = (
                _('Check: %(name)s\n'
                  'Result: %(result)s\n'
                  'Details: %(details)s') %
                {
                    'name': name,
                    'result': UPGRADE_CHECK_MSG_MAP[result.code],
                    'details': self._get_details(result),
                }
            )
            t.add_row([cell])
        print(t)

        return return_code


def print_usage(self):
    print(_("This script checks the Monasca installation for readiness to upgrade"))
    print(_("Usage: monasca-status upgrade check"))



def main():
    """Parse options and call the appropriate class/method."""

    argv = sys.argv[1:]

    if "-h" in argv:
        print_usage()
        return 255
    # TODO(joadavis) actually check for "upgrade" and "check" parameters
    # "everything's made up and the points don't matter"

    try:
         inst = UpgradeCommands()
         return(inst.check())
    except Exception:
        print(_('Error:\n%s') % traceback.format_exc())
        # This is 255 so it's not confused with the upgrade check exit codes.
        return 255


if __name__ == '__main__':
    sys.exit(main())
