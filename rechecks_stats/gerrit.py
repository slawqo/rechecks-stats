import json
import os
import subprocess
import sys
from pathlib import Path

from rechecks_stats import printer


CACHE_DIR_NAME = ".rechecks_cache"


# Script based on Assaf Muller's script
# https://github.com/assafmuller/gerrit_time_to_merge/blob/master/time_to_merge.py


class Gerrit(object):

    def __init__(self, config, status=None, all_patch_sets=False):
        self.config = config
        self.status = status
        self.all_patch_sets = all_patch_sets
        self.printer = printer.get_printer(config)
        self._build_query(config)
        self._cache_dir = "%s/%s" % (Path.home(), CACHE_DIR_NAME)

    def _build_query(self, config):
        self.query = "branch:%s " % config.branch
        if self.status:
            self.query += 'status:%s ' % self.status
        if config.project:
            self.query += 'project:%s ' % config.project
        if config.newer_than:
            self.query += ' -- -age:%dd' % int(config.newer_than)
        self.printer.log_debug("Query: %s" % self.query)

    def _ensure_cache_dir_exists(self):
        try:
            os.mkdir(self._cache_dir)
        except OSError:
            pass

    def _get_file_from_query(self):
        return self.query.replace('/', '_')

    def _get_json_data_from_cache(self):
        self._ensure_cache_dir_exists()
        query_file_name = self._get_file_from_query()
        if query_file_name in os.listdir(self._cache_dir):
            with open('%s/%s' % (self._cache_dir, query_file_name)) as f:
                return json.load(f)

    def _put_json_data_in_cache(self, data):
        self._ensure_cache_dir_exists()
        query_file_name = self._get_file_from_query()
        with open('%s/%s' % (self._cache_dir, query_file_name), 'w') as f:
            json.dump(data, f)

    def _exec_cmd(self, command):
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=True)
        output, error = process.communicate()

        return output, error

    def _get_json_data_from_query(self):
        data = []
        start = 0

        while True:
            gerrit_cmd = (
                'ssh -p 29418 review.opendev.org gerrit query --format=json '
                '--current-patch-set --comments ')
            if self.all_patch_sets:
                gerrit_cmd += '--patch-sets '

            gerrit_cmd += '--start %(start)s %(query)s' % {'start': start,
                                                           'query': self.query}
            result, error = self._exec_cmd(gerrit_cmd)

            if error:
                self.printer.log_error(error)
                sys.exit(1)

            result = result.decode('utf-8')
            lines = result.split('\n')[:-2]
            data += [json.loads(line) for line in lines]

            if not data:
                self.printer.log_error('No patches found!')
                sys.exit(1)

            self.printer.log_debug(
                'Found metadata for %s more patches, %s total so far' %
                (len(lines), len(data)))
            start += len(lines)
            more_changes = json.loads(result.split('\n')[-2])['moreChanges']
            if not more_changes:
                break

        data = sorted(data, key=lambda x: x['createdOn'])
        return data

    def get_json_data(self):
        data = None
        if not self.config.no_cache:
            data = self._get_json_data_from_cache()
        if not data:
            data = self._get_json_data_from_query()
            self._put_json_data_in_cache(data)
        return data
