import json
import os
import sys

from pathlib import Path
import subprocess

from rechecks_stats import printer


CACHE_DIR_NAME = ".rechecks_cache"


class Gerrit(object):

    def __init__(self, config):
        self.config = config
        self.printer = printer.get_printer(config)
        self._build_query(config)
        self._cache_dir = "%s/%s" % (Path.home(), CACHE_DIR_NAME)

    def _build_query(self, config):
        self.query = "status:merged branch:%s " % config.branch
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
            with open('%s/%s' % (self._cache_dir, query_file_name)
                    ) as query_file:
                return json.load(query_file)

    def _put_json_data_in_cache(self, data):
        self._ensure_cache_dir_exists(cache_dir)
        query_file_name = self._get_file_from_query()
        with open('%s/%s' % (cache_dir, query_file_name), 'w'
                ) as query_file:
            json.dump(data, query_file)

    def _exec_cmd(self, command):
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, error = process.communicate()

        return output, error

    def _get_json_data_from_query(self):
        data = []
        start = 0

        while True:
            gerrit_cmd = (
                'ssh -p 29418 review.opendev.org gerrit query --format=json '
                '--current-patch-set --comments --start %(start)s %(query)s' %
                {'start': start,
                 'query': query})
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
        if not self.config.no_cache:
            data = self._get_json_data_from_cache()
        if not data:
            data = self._get_json_data_from_query()
            self._put_json_data_in_cache(data)
        return data