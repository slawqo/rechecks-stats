import sys

from rechecks_stats import config
from rechecks_stats import data_parser
from rechecks_stats import gerrit
from rechecks_stats import printer


def main():
    args = config.get_bare_rechecks_parser()
    _printer = printer.get_printer(args)

    if args.stats_per_team and not args.projects_file:
        _printer.log_error(
            "Path to the projects.yaml file from the "
            "https://git.openstack.org/openstack/governance/ is required "
            "when stats per team are requested.")
        sys.exit(1)

    g = gerrit.Gerrit(args, all_patch_sets=True)

    data = g.get_json_data()
    dp = data_parser.BareRechecksDataParser(args, data)

    if args.project:
        _printer.print_project_bare_rechecks(
            dp.get_bare_rechecks_stats_per_patch())
    else:
        if args.stats_per_team:
            _printer.print_global_bare_rechecks(
                dp.get_bare_rechecks_stats_per_team())
        else:
            _printer.print_global_bare_rechecks(
                dp.get_bare_rechecks_stats_per_project())
