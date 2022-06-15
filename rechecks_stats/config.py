import argparse


rechecks_stats_parser = None
bare_rechecks_parser = None


def get_rechecks_stats_parser():
    global rechecks_stats_parser
    if rechecks_stats_parser is None:
        rechecks_stats_parser = argparse.ArgumentParser(
            description='Get from gerrit informations about how many builds '
                        'failed on patches before it was finally merged.'
                        'Note that the app uses a caching system - Query '
                        'results are stored in the cache dir with no timeout. '
                        'Subsequent runs of the app against the same project '
                        'and time will not query Gerrit, but will use the '
                        'local results. As the cache has no timeout, '
                        'its contents must be deleted manually to get a fresh '
                        'query.')
        rechecks_stats_parser.add_argument(
            '--newer-than',
            help='Only look at patches merged in the last so and so days.')
        rechecks_stats_parser.add_argument(
            '--time-window',
            default='week',
            help='Count average number of recheck per "week" (default), '
                 '"month" or "year".')
        rechecks_stats_parser.add_argument(
            '--all-patches',
            action='store_true',
            help='If this is set, number of rechecks for each patch '
                 'separately is returned. Please note that when this is flag '
                 'is used, "--time-window" option has no effect.')
        rechecks_stats_parser.add_argument(
            '--only-average',
            action='store_true',
            help='If this is set, only average number of rechecks in '
                 'specified time period will be returned. '
                 'When this is set, options like "--all-patches", "--plot" '
                 'and "--time-window" have no effect.')
        rechecks_stats_parser.add_argument(
            '--no-cache',
            action='store_true',
            help="Don't use cached results, always download new ones.")
        rechecks_stats_parser.add_argument(
            '--verbose',
            action='store_true',
            help='Be more verbose.')
        rechecks_stats_parser.add_argument(
            '--plot',
            action='store_true',
            help='Generate graphs directly by script.')
        rechecks_stats_parser.add_argument(
            '--report-format',
            default='human',
            help=('Format in which results will be printed. '
                  'Default value: "human" '
                  'Possible values: "human", "csv"'))
        rechecks_stats_parser.add_argument(
            '--branch',
            default='master',
            help='Branch to check. For example stable/stein.')
        rechecks_stats_parser.add_argument(
            '--project',
            default=None,
            help='The OpenStack project to query. '
                 'For example openstack/neutron.')

    return rechecks_stats_parser.parse_args()


def get_bare_rechecks_parser():
    global bare_rechecks_parser
    if bare_rechecks_parser is None:
        bare_rechecks_parser = argparse.ArgumentParser(
            description='Get stats of the rechecks without any reason done '
                        'in the project(s).')
        bare_rechecks_parser.add_argument(
            '--newer-than',
            help='Only look at patches merged in the last so and so days.')
        bare_rechecks_parser.add_argument(
            '--no-cache',
            action='store_true',
            help="Don't use cached results, always download new ones.")
        bare_rechecks_parser.add_argument(
            '--verbose',
            action='store_true',
            help='Be more verbose.')
        bare_rechecks_parser.add_argument(
            '--branch',
            default='master',
            help='Branch to check. For example stable/stein.')
        bare_rechecks_parser.add_argument(
            '--project',
            default=None,
            help='The OpenStack project to query. '
                 'For example openstack/neutron.')

    return bare_rechecks_parser.parse_args()
