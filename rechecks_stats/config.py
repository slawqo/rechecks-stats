import argparse


parser = None

def get_parser():
    global parser
    if parser is None:
        parser = argparse.ArgumentParser(
            description='Get from gerrit informations about how many builds '
                        'failed on patches before it was finally merged.'
                        'Note that the app uses a caching system - Query '
                        'results are stored in the cache dir with no timeout. '
                        'Subsequent runs of the app against the same project '
                        'and time will not query Gerrit, but will use the '
                        'local results. As the cache has no timeout, '
                        'its contents must be deleted manually to get a fresh '
                        'query.')
        parser.add_argument(
            '--newer-than',
            help='Only look at patches merged in the last so and so days.')
        parser.add_argument(
            '--time-window',
            default='week',
            help='Count average number of recheck per "week" (default), '
                 '"month" or "year".')
        parser.add_argument(
            '--all-patches',
            action='store_true',
            help='If this is set, number of rechecks for each patch '
                 'separately is returned. Please note that when this is flag '
                 'is used, "--time-window" option has no effect.')
        parser.add_argument(
            '--only-average',
            action='store_true',
            help='If this is set, only average number of rechecks in '
                 'specified time period will be returned. '
                 'When this is set, options like "--all-patches", "--plot" '
                 'and "--time-window" have no effect.')
        parser.add_argument(
            '--no-cache',
            action='store_true',
            help="Don't use cached results, always download new ones.")
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Be more verbose.')
        parser.add_argument(
            '--plot',
            action='store_true',
            help='Generate graphs directly by script.')
        parser.add_argument(
            '--report-format',
            default='human',
            help=('Format in which results will be printed. '
                  'Default value: "human" '
                  'Possible values: "human", "csv"'))
        parser.add_argument(
            '--branch',
            default='master',
            help='Branch to check. For example stable/stein.')
        parser.add_argument(
            '--project',
            default=None,
            help='The OpenStack project to query. '
                 'For example openstack/neutron.')

    return parser.parse_args()
