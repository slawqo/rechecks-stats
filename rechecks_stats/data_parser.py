import datetime
import re

from rechecks_stats import printer


class DataParser(object):

    _points = None

    def __init__(self, config, data):
        self.printer = printer.get_printer(config)
        self.config = config
        self.data = data

    @property
    def points(self):
        if self._points is None:
            self._points = self._get_points()
        return self._points

    def _get_submission_timestamp(self, patch):
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

    def _get_points(self):
        points = []
        ps_regex = re.compile(r"Patch Set (\d+)\:")

        for patch in self.data:
            last_ps = int(patch['currentPatchSet']['number'])
            counter = 0
            for comment in patch['comments']:
                if comment['reviewer']['name'].lower() != 'zuul':
                    continue
                msg = comment['message']
                re_ps = re.search(ps_regex, msg)
                if not re_ps:
                    self.printer.log_debug("No patch set found for comment: %s" % msg)
                    continue
                if int(re_ps.group(1)) != last_ps:
                    self.printer.log_debug("Comment was not for last patch set. Skipping")
                    continue

                if self._regex.search(msg):
                    counter += 1

            points.append(
                {'id': patch['id'],
                 'merged': self._get_submission_timestamp(patch),
                 'counter': counter,
                 'project': patch['project'],
                 'url': patch['url'],
                 'subject': patch['subject']})
        points = sorted(points, key = lambda i: i['merged'])

        if not points:
            error = 'Could not parse points from data. It is likely that the ' \
                    'createdOn timestamp of the patches found is bogus.'
            self.printer.print_error(error)
            sys.exit(1)

        return points


class AvgDataParser(DataParser):

    def __init__(self, config, data):
        super(AvgDataParser, self).__init__(config, data)
        self._avg_data_points = None
        self._regex = re.compile(r"Build failed \((check|gate) pipeline\)")

    def get_avg_number_or_rechecks(self):
        build_failures = 0
        for point in self.points:
            build_failures += point['counter']
        return build_failures / len(self.points)

    def get_avg_failures(self):
        if self.config.time_window == 'week':
            return self._get_avg_failures_per_week()
        elif self.config.time_window == 'month':
            return self._get_avg_failures_per_month()
        else:
            return self._get_avg_failures_per_year()

    def _get_avg_failures_per_week(self):
        if self._avg_data_points is None:
            data = {}
            for point in self.points:
                point_date = datetime.date.fromtimestamp(point['merged'])
                point_year, point_week, _ = point_date.isocalendar()
                point_key = "%s-%s" % (point_year, point_week)
                self.printer.log_debug("Patch %s merged %s (week %s)" % (
                    point['id'], point_date, point_key))
                if point_key not in data.keys():
                    data[point_key] = [point['counter']]
                else:
                    data[point_key].append(point['counter'])

            self._avg_data_points = {k: sum(v)/len(v) for k, v in data.items()}

        return self._avg_data_points

    def _get_avg_failures_per_month(self):
        if self._avg_data_points is None:
            data = {}
            for point in self.points:
                point_date = datetime.date.fromtimestamp(point['merged'])
                point_key = "%s-%s" % (point_date.year, point_date.month)
                self.printer.log_debug("Patch %s merged %s (week %s)" % (
                    point['id'], point_date, point_key))
                if point_key not in data.keys():
                    data[point_key] = [point['counter']]
                else:
                    data[point_key].append(point['counter'])

            self._avg_data_points = {k: sum(v)/len(v) for k, v in data.items()}

        return self._avg_data_points

    def _get_avg_failures_per_year(self):
        if self._avg_data_points is None:
            data = {}
            for point in self.points:
                point_date = datetime.date.fromtimestamp(point['merged'])
                point_key = point_date.year
                self.printer.log_debug("Patch %s merged %s (week %s)" % (
                    point['id'], point_date, point_key))
                if point_key not in data.keys():
                    data[point_key] = [point['counter']]
                else:
                    data[point_key].append(point['counter'])

            self._avg_data_points = {k: sum(v)/len(v) for k, v in data.items()}

        return self._avg_data_points



