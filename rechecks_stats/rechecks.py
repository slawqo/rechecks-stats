#!/usr/bin/env python3

import datetime
import json
import os
import re
import sys

import matplotlib.pyplot as plt
from prettytable import PrettyTable

from rechecks_stats import config
from rechecks_stats import gerrit
from rechecks_stats import printer

# Script based on Assaf Muller's script
# https://github.com/assafmuller/gerrit_time_to_merge/blob/master/time_to_merge.py

def get_submission_timestamp(patch):
    try:
        # Not all patches have approvals data
        approvals = patch['currentPatchSet']['approvals']
    except KeyError:
        return patch['lastUpdated']

    # Weirdly enough some patches don't have submission data.
    # Take lastUpdated instead.
    return next(
        (approval['grantedOn'] for approval in approvals if
         approval['type'] == 'SUBM'), patch['lastUpdated'])


def get_points_from_data(data):

    points = []
    build_failed_regex = re.compile(
        r"Build failed \((check|gate) pipeline\)")
    ps_regex = re.compile(r"Patch Set (\d+)\:")

    for patch in data:
        last_ps = int(patch['currentPatchSet']['number'])
        build_failures = 0
        for comment in patch['comments']:
            if comment['reviewer']['name'].lower() != 'zuul':
                continue
            msg = comment['message']
            re_ps = re.search(ps_regex, msg)
            if not re_ps:
                printer.log_debug("No patch set found for comment: %s" % msg)
                continue
            if int(re_ps.group(1)) != last_ps:
                printer.log_debug("Comment was not for last patch set. Skipping")
                continue

            if build_failed_regex.search(msg):
                build_failures += 1

        points.append(
            {'id': patch['id'],
             'merged': get_submission_timestamp(patch),
             'build_failures': build_failures,
             'project': patch['project'],
             'url': patch['url'],
             'subject': patch['subject']})
    points = sorted(points, key = lambda i: i['merged'])
    return points


AVG_DATA_POINTS = None


def get_avg_failures(points, time_window):
    if time_window == 'week':
        return get_avg_failures_per_week(points)
    elif time_window == 'month':
        return get_avg_failures_per_month(points)
    else:
        return get_avg_failures_per_year(points)


def get_avg_failures_per_week(points):
    global AVG_DATA_POINTS
    if AVG_DATA_POINTS is None:
        data = {}
        for point in points:
            point_date = datetime.date.fromtimestamp(point['merged'])
            point_year, point_week, _ = point_date.isocalendar()
            point_key = "%s-%s" % (point_year, point_week)
            printer.log_debug("Patch %s merged %s (week %s)" % (
                point['id'], point_date, point_key))
            if point_key not in data.keys():
                data[point_key] = [point['build_failures']]
            else:
                data[point_key].append(point['build_failures'])

        AVG_DATA_POINTS = {k: sum(v)/len(v) for k, v in data.items()}

    return AVG_DATA_POINTS


def get_avg_failures_per_month(points):
    global AVG_DATA_POINTS
    if AVG_DATA_POINTS is None:
        data = {}
        for point in points:
            point_date = datetime.date.fromtimestamp(point['merged'])
            point_key = "%s-%s" % (point_date.year, point_date.month)
            printer.log_debug("Patch %s merged %s (week %s)" % (
                point['id'], point_date, point_key))
            if point_key not in data.keys():
                data[point_key] = [point['build_failures']]
            else:
                data[point_key].append(point['build_failures'])

        AVG_DATA_POINTS = {k: sum(v)/len(v) for k, v in data.items()}

    return AVG_DATA_POINTS


def get_avg_failures_per_year(points):
    global AVG_DATA_POINTS
    if AVG_DATA_POINTS is None:
        data = {}
        for point in points:
            point_date = datetime.date.fromtimestamp(point['merged'])
            point_key = point_date.year
            printer.log_debug("Patch %s merged %s (week %s)" % (
                point['id'], point_date, point_key))
            if point_key not in data.keys():
                data[point_key] = [point['build_failures']]
            else:
                data[point_key].append(point['build_failures'])

        AVG_DATA_POINTS = {k: sum(v)/len(v) for k, v in data.items()}

    return AVG_DATA_POINTS


def plot_patch_rechecks(points):
    x_values = [patch['id'] for patch in points]
    y_values = [patch['build_failures'] for patch in points]
    plt.plot(x_values, y_values,
             label='Number of failed builds before patch merge')
    plt.xlabel('patch merge time')
    plt.ylabel('number of failed builds')
    plt.legend()
    plt.show()


def get_avg_number_or_rechecks(points):
    build_failures = 0
    for point in points:
        build_failures += point['build_failures']
    return build_failures / len(points)


def print_patch_rechecks(points, report_format):
    points = sorted(points, key=lambda x: x['build_failures'], reverse=True)
    if report_format == 'csv':
        print_rechecks_as_csv(points)
    else:
        print_rechecks_as_human_readable(points)


def print_rechecks_as_csv(points):
    print("%s,Average number of failed builds" % time_window)
    for patch_data in points:
        print('%s,%s,%s,%s' % (patch_data['subject'],
                            patch_data['url'],
                            patch_data['project'],
                            patch_data['build_failures']))


def print_rechecks_as_human_readable(points):
    table = PrettyTable()
    table.field_names = ['Subject', 'URL', 'Project', 'Rechecks']
    avg_build_failures = get_avg_number_or_rechecks(points)
    avg_marker_drawed = False
    for patch_data in points:
        # Data is already sorted so we can draw marker in single place in table
        if (not avg_marker_drawed and
                patch_data['build_failures'] < avg_build_failures):
            table.add_row(
                ["AVERAGE NUMBER OF RECHECKS",
                 "====================================",
                 "=================",
                 round(avg_build_failures, 2)])
            avg_marker_drawed = True
        table.add_row(
            [patch_data['subject'],
             patch_data['url'],
             patch_data['project'],
             round(patch_data['build_failures'], 2)])
    print(table)

def plot_avg_rechecks(points, time_window):
    plot_points = get_avg_failures(points, time_window)
    x_values = list(plot_points.keys())
    y_values = list(plot_points.values())
    plt.plot(x_values, y_values,
             label=('Average number of failed builds '
                    'before patch merge per %s' % time_window))
    plt.xlabel('patch merge time')
    plt.ylabel('number of failed builds')
    plt.legend()
    plt.xticks(x_values, x_values, rotation='vertical')
    plt.show()


def print_avg_rechecks(points, time_window, report_format):
    plot_points = get_avg_failures(points, time_window)
    if report_format == 'csv':
        print_avg_as_csv(plot_points, time_window)
    else:
        print_avg_as_human_readable(plot_points, time_window)


def print_avg_as_csv(points, time_window):
    print("%s,Average number of failed builds" % time_window)
    for week, value in points.items():
        print('%s,%s' % (week, value))


def print_avg_as_human_readable(points, time_window):
    table = PrettyTable()
    table.field_names = [time_window, "Rechecks"]
    for week, value in points.items():
        table.add_row([week, round(value, 2)])
    print(table)



def main():
    args = config.get_parser()
    global printer
    printer = printer.get_printer(args)

    g = gerrit.Gerrit(args)
    data = g.get_json_data()

    points = get_points_from_data(data)

    if not points:
        error = 'Could not parse points from data. It is likely that the ' \
                'createdOn timestamp of the patches found is bogus.'
        printer.print_error(error)
        sys.exit(1)

    if args.only_average:
        print(round(get_avg_number_or_rechecks(points), 2))
        sys.exit(0)

    if args.all_patches:
        if args.plot:
            plot_patch_rechecks(points)
        print_patch_rechecks(points, args.report_format)
    else:
        if args.plot:
            plot_avg_rechecks(points, args.time_window)
        print_avg_rechecks(points, args.time_window, args.report_format)
