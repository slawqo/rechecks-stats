import copy
import datetime
import re
import sys
import time

import yaml

from rechecks_stats import printer


class DataParser(object):

    _points = None

    def __init__(self, config, data, check_only_last_ps, comment_authors=None):
        self.printer = printer.get_printer(config)
        self.config = config
        self.data = data
        self.check_only_last_ps = check_only_last_ps
        self.merge_timestamp_limit = int(self.config.newer_than) * 86400  # [s]
        self.comment_authors = []
        if comment_authors:
            self.comment_authors = [
                author.lower() for author in comment_authors]

    @property
    def points(self):
        if self._points is None:
            self._points = self._get_points()
        return self._points

    def _load_repos_to_teams_list(self):
        if not self.config.projects_file:
            return None
        with open(self.config.projects_file, "r") as projects_yaml:
            try:
                projects = yaml.safe_load(projects_yaml)
            except yaml.YAMLError as err:
                self.printer.log_error("Error: %s while loading projects.yaml "
                                       "file." % err)
                sys.exit(2)
        repos_to_teams_map = {}
        for project_name, project_data in projects.items():
            for deliverable in project_data.get('deliverables', {}).values():
                repos = deliverable.get('repos')
                for repo in repos:
                    repos_to_teams_map[repo] = project_name
        return repos_to_teams_map

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

    def _get_points(self, regex=None):
        points = []
        regex = regex or self._regex
        if self.check_only_last_ps:
            ps_regex = re.compile(r"Patch Set (\d+)\:")

        now = time.time()
        oldest_merge = now - self.merge_timestamp_limit
        for patch in self.data:
            patch_merge_date = self._get_submission_timestamp(patch)
            if patch_merge_date and (patch_merge_date < oldest_merge):
                self.printer.log_debug("Patch %s too old to be counted. "
                                       "Skipping." % patch['url'])
                continue
            if self.check_only_last_ps:
                last_ps = int(patch['currentPatchSet']['number'])
            counter = 0
            comments = copy.deepcopy(patch['comments'])
            if 'patchSets' in patch.keys():
                for ps in patch['patchSets']:
                    comments += [c for c in ps.get('comments', [])]
            for comment in comments:
                if self.comment_authors:
                    comment_author = comment['reviewer']['name'].lower()
                    if comment_author not in self.comment_authors:
                        continue
                msg = comment['message']
                if self.check_only_last_ps:
                    re_ps = re.search(ps_regex, msg)
                    if not re_ps:
                        self.printer.log_debug(
                            "No patch set found for comment: %s" % msg)
                        continue
                    if int(re_ps.group(1)) != last_ps:
                        self.printer.log_debug(
                            "Comment was not for last patch set. Skipping")
                        continue

                if regex.search(msg):
                    counter += 1

            points.append(
                {'id': patch['id'],
                 'merged': patch_merge_date,
                 'counter': counter,
                 'project': patch['project'],
                 'url': patch['url'],
                 'subject': patch['subject']})
        points = sorted(points, key=lambda i: i['merged'])

        if not points:
            error = ('Could not parse points from data. It is likely that the '
                     'createdOn timestamp of the patches found is bogus.')
            self.printer.print_error(error)
            sys.exit(1)

        return points


class AvgDataParser(DataParser):

    def __init__(self, config, data):
        super(AvgDataParser, self).__init__(config, data,
                                            check_only_last_ps=True,
                                            comment_authors=['zuul'])
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


class BareRechecksDataParser(DataParser):

    def __init__(self, config, data):
        super(BareRechecksDataParser, self).__init__(config, data,
                                                     check_only_last_ps=False)
        self._avg_data_points = None
        self._bare_rechecks_regex = re.compile(
            r"(?i)^(Patch Set [0-9]+:)?( [\w\\+-]*)*(\n\n)?\s*recheck$",
            flags=re.IGNORECASE)
        self._all_rechecks_regex = re.compile(
            r"(?i)^(Patch Set [0-9]+:)?( [\w\\+-]*)*(\n\n)?\s*recheck",
            flags=re.IGNORECASE)
        self._all_rechecks = None
        self._bare_rechecks = None
        self._repos_to_teams_map = self._load_repos_to_teams_list()

    def _get_all_rechecks(self):
        if not self._all_rechecks:
            self._all_rechecks = {
                r['id']: r for r in
                self._get_points(regex=self._all_rechecks_regex)}
        return self._all_rechecks

    def _get_bare_rechecks(self):
        if not self._bare_rechecks:
            self._bare_rechecks = {
                r['id']: r for r in
                self._get_points(regex=self._bare_rechecks_regex)}
        return self._bare_rechecks

    def get_bare_rechecks_stats_per_patch(self):
        all_rechecks = self._get_all_rechecks()
        bare_rechecks = self._get_bare_rechecks()
        rechecks_stats = []
        for patch_id, stats in all_rechecks.items():
            p_stats = stats.copy()
            p_stats['bare_rechecks'] = bare_rechecks[patch_id]['counter']
            p_stats['all_rechecks'] = all_rechecks[patch_id]['counter']
            if p_stats['all_rechecks'] != 0:
                p_stats['bare_rechecks_percentage'] = (
                    p_stats['bare_rechecks'] / p_stats['all_rechecks']) * 100
            else:
                p_stats['bare_rechecks_percentage'] = 0
            rechecks_stats.append(p_stats)
        return rechecks_stats

    def get_bare_rechecks_stats_per_project(self):
        all_rechecks = self._get_all_rechecks()
        bare_rechecks = self._get_bare_rechecks()
        rechecks_stats = {}
        for patch_id in all_rechecks.keys():
            patch_stats = all_rechecks[patch_id]
            project = patch_stats['project']
            if project not in rechecks_stats:
                rechecks_stats[project] = {
                    'project': project,
                    'all_rechecks': all_rechecks[patch_id]['counter'],
                    'bare_rechecks': bare_rechecks[patch_id]['counter']}
            else:
                rechecks_stats[project]['all_rechecks'] += (
                        all_rechecks[patch_id]['counter'])
                rechecks_stats[project]['bare_rechecks'] += (
                        bare_rechecks[patch_id]['counter'])

            if self._repos_to_teams_map:
                rechecks_stats[project]['team'] = (
                    self._repos_to_teams_map.get(project))

        for project in rechecks_stats.keys():
            if rechecks_stats[project]['all_rechecks'] != 0:
                rechecks_stats[project]['bare_rechecks_percentage'] = (
                    rechecks_stats[project]['bare_rechecks'] /
                    rechecks_stats[project]['all_rechecks']) * 100
            else:
                rechecks_stats[project]['bare_rechecks_percentage'] = 0

        return sorted(
            rechecks_stats.values(),
            key=lambda i: i['bare_rechecks_percentage'],
            reverse=True)

    def get_bare_rechecks_stats_per_team(self):
        # TODO: this has to be implemented still
        all_rechecks = self._get_all_rechecks()
        bare_rechecks = self._get_bare_rechecks()
        rechecks_stats = {}
        for patch_id in all_rechecks.keys():
            patch_stats = all_rechecks[patch_id]
            project = patch_stats['project']
            team = self._repos_to_teams_map.get(project)
            if not team:
                self.printer.log_debug("Patch %s don't have team associated. "
                                       "Skipping." % patch_id)
                continue
            if team not in rechecks_stats:
                rechecks_stats[team] = {
                    'team': team,
                    'all_rechecks': all_rechecks[patch_id]['counter'],
                    'bare_rechecks': bare_rechecks[patch_id]['counter']}
            else:
                rechecks_stats[team]['all_rechecks'] += (
                        all_rechecks[patch_id]['counter'])
                rechecks_stats[team]['bare_rechecks'] += (
                        bare_rechecks[patch_id]['counter'])

        for team in rechecks_stats.keys():
            if rechecks_stats[team]['all_rechecks'] != 0:
                rechecks_stats[team]['bare_rechecks_percentage'] = (
                    rechecks_stats[team]['bare_rechecks'] /
                    rechecks_stats[team]['all_rechecks']) * 100
            else:
                rechecks_stats[team]['bare_rechecks_percentage'] = 0

        return sorted(
            rechecks_stats.values(),
            key=lambda i: i['bare_rechecks_percentage'],
            reverse=True)
