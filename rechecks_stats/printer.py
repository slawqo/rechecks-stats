from prettytable import PrettyTable

PRINTER = None


def get_printer(config):
    global PRINTER
    if PRINTER is None:
        PRINTER = Printer(config)
    return PRINTER


class Printer(object):

    def __init__(self, config):
        self.config = config

    def print_msg(self, msg):
        print(msg)

    def log_error(self, msg):
        self.print_msg(msg)

    def log_debug(self, msg):
        if self.config.verbose:
            self.print_msg(msg)

    @staticmethod
    def _get_table():
        table = PrettyTable()
        table.align = "l"
        return table

    def _print_avg_as_csv(self, points):
        self.print_msg("%s,Average number of failed builds" %
                       self.config.time_window)
        for week, value in points.items():
            self.print_msg('%s,%s' % (week, value))

    def _print_avg_as_human_readable(self, points):
        table = self._get_table()
        table.field_names = [self.config.time_window, "Rechecks"]
        for week, value in points.items():
            table.add_row([week, round(value, 2)])
        self.print_msg(table)

    def print_avg_rechecks(self, plot_points):
        if self.config.report_format == 'csv':
            self._print_avg_as_csv(plot_points)
        else:
            self._print_avg_as_human_readable(plot_points)

    def print_patch_rechecks(self, points, avg):
        points = sorted(points, key=lambda x: x['counter'], reverse=True)
        if self.config.report_format == 'csv':
            self._print_rechecks_as_csv(points)
        else:
            self._print_rechecks_as_human_readable(points, avg)

    def _print_rechecks_as_csv(self, points):
        self.print_msg("%s,Average number of failed builds" %
                       self.config.time_window)
        for patch_data in points:
            self.print_msg('%s,%s,%s,%s' % (patch_data['subject'],
                                            patch_data['url'],
                                            patch_data['project'],
                                            patch_data['counter']))

    def _print_rechecks_as_human_readable(self, points, avg):
        table = self._get_table()
        table.field_names = ['Subject', 'URL', 'Project', 'Rechecks']
        avg_marker_drawed = False
        for patch_data in points:
            # Data is already sorted so we can draw marker in single place
            # in table
            if (not avg_marker_drawed and
                    patch_data['counter'] < avg):
                table.add_row(
                    ["AVERAGE NUMBER OF RECHECKS",
                     "====================================",
                     "=================",
                     round(avg, 2)])
                avg_marker_drawed = True
            table.add_row(
                [patch_data['subject'],
                 patch_data['url'],
                 patch_data['project'],
                 round(patch_data['counter'], 2)])
        self.print_msg(table)

    def print_project_bare_rechecks(self, points, print_all_rows=False):
        table = self._get_table()
        table.field_names = [
            'Subject', 'URL', 'Project',
            'Bare rechecks', 'All Rechecks', 'Bare rechecks [%]']
        for patch_data in points:
            if print_all_rows or patch_data['all_rechecks'] != 0:
                table.add_row(
                    [patch_data['subject'],
                     patch_data['url'],
                     patch_data['project'],
                     patch_data['bare_rechecks'],
                     patch_data['all_rechecks'],
                     round(patch_data['bare_rechecks_percentage'], 2)])
        self.print_msg(table)

    def print_global_bare_rechecks(self, points, print_all_rows=False):
        table = self._get_table()
        field_names = []
        project_field_included = False
        team_field_included = False
        if 'project' in points[0].keys():
            field_names.append('Project')
            project_field_included = True
        if 'team' in points[0].keys():
            field_names.append('Team')
            team_field_included = True
        field_names += [
            'Bare rechecks', 'All Rechecks', 'Bare rechecks [%]']
        table.field_names = field_names
        for patch_data in points:
            if print_all_rows or patch_data['all_rechecks'] != 0:
                row_data = []
                if project_field_included:
                    row_data.append(patch_data['project'])
                if team_field_included:
                    row_data.append(patch_data['team'])
                row_data += [patch_data['bare_rechecks'],
                             patch_data['all_rechecks'],
                             round(patch_data['bare_rechecks_percentage'], 2)]
                table.add_row(row_data)
        self.print_msg(table)

    def print_reacheck_reasons(self, points):
        table = self._get_table()
        table.field_names = [
            "Recheck comment", "Number of occurences"]
        for reason, counter in points.items():
            reason = reason.replace("\n", "")
            table.add_row([reason, counter])
        self.print_msg(table)