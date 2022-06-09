#!/usr/bin/env python3

import sys

from rechecks_stats import config
from rechecks_stats import data_parser
from rechecks_stats import gerrit
from rechecks_stats import plotter
from rechecks_stats import printer


def main():
    args = config.get_parser()
    _printer = printer.get_printer(args)
    _plotter = plotter.get_plotter(args)

    g = gerrit.Gerrit(args)
    data = g.get_json_data()

    # this will go to the new class/module, something like rechecks_data:
    avg_dp = data_parser.AvgDataParser(args, data)

    # this too
    if args.only_average:
        avg_rechecks = round(avg_dp.get_avg_number_or_rechecks(), 2)
        _printer.print_msg(avg_rechecks)
        sys.exit(0)

    # and that
    if args.all_patches:
        if args.plot:
            _plotter.plot_patch_rechecks(avg_dp.points)
        avg_rechecks = round(avg_dp.get_avg_number_or_rechecks(), 2)
        _printer.print_patch_rechecks(avg_dp.points, avg_rechecks)
    else:
        plot_points = avg_dp.get_avg_failures()
        if args.plot:
            _plotter.plot_avg_rechecks(plot_points)
        _printer.print_avg_rechecks(plot_points)
