import sys

from rechecks_stats import config
from rechecks_stats import data_parser
from rechecks_stats import gerrit
from rechecks_stats import printer


def main():
    args = config.get_rechecks_reasons_parser()
    _printer = printer.get_printer(args)

    g = gerrit.Gerrit(args, all_patch_sets=True)

    data = g.get_json_data()
    dp = data_parser.RechecksReasonsDataParser(args, data)
    _printer.print_reacheck_reasons(dp.get_rechecks_reasons())