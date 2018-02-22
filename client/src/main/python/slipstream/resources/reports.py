"""
 SlipStream Client
 =====
 Copyright (C) 2016 SixSq Sarl (sixsq.com)
 =====
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""
from __future__ import print_function

import os
import errno
from datetime import datetime
import pprint

import slipstream.util as util
from slipstream.NodeDecorator import NodeDecorator

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


def is_newer(d1, d2, tf=TIME_FORMAT):
    return datetime.strptime(d1, tf) < datetime.strptime(d2, tf)


class ReportsGetter(object):

    def __init__(self, api, configHolder):
        """Expects an authenticated session provided with 'ch' config holder.
        The class uses url `domain`/`path` and the name of cookie to get it
        from the session and use in the downloading of the requested reports.
        """
        self.verboseLevel = 0
        self.output_dir = os.getcwd()
        self.components = ''
        self.no_orch = False
        configHolder.assign(self)
        self.api = api

    @staticmethod
    def latest_only(reports):
        reports_filtered = {}
        for report in reports:
            r = report.json
            node = r['component']
            del r['operations']
            del r['acl']
            del r['resourceURI']
            not_yet_added = node not in reports_filtered
            if not_yet_added:
                reports_filtered[node] = r
            else:
                # replace if newer
                if is_newer(reports_filtered[node]['created'], r['created']):
                    reports_filtered[r['component']] = r

        return reports_filtered.values()

    @staticmethod
    def remove_orch(reports):
        reports_no_orch = []
        for r in reports:
            if not NodeDecorator.is_orchestrator_name(r['component']):
                reports_no_orch.append(r)
        return reports_no_orch

    @staticmethod
    def components_only(reports, comps):
        reports_only = []

        for r in reports:
            name = r['component']
            if name.rsplit(NodeDecorator.NODE_MULTIPLICITY_SEPARATOR)[
                0] in comps or \
                    name in comps:
                reports_only.append(r)

        return reports_only

    def reports_path(self, run_uuid):
        return os.path.join(self.output_dir, run_uuid)

    def output_fullpath(self, run_uuid, name):
        return os.path.join(self.reports_path(run_uuid), name)

    @staticmethod
    def mkdir(_dir):
        try:
            os.makedirs(_dir, mode=0755)
        except OSError as ex:
            if ex.errno != errno.EEXIST:
                raise ex
        return _dir

    def get_reports(self, run_uuid, components=None, no_orch=False):
        if components is None:
            components = []
        reports_list_orig = self.api.cimi_search('externalObjects',
                                                 select='id, component, created',
                                                 filter='runUUID="{}" and state="ready"'
                                                 .format(run_uuid)).resources_list
        if len(reports_list_orig) == 0:
            self.info("::: WARNING: No reports available on %s :::" % run_uuid)
            return

        reports_list = self.latest_only(reports_list_orig)
        self.debug("::: Only latest reports are selected. :::", data=reports_list)

        if no_orch:
            reports_list = self.remove_orch(reports_list)

        if components:
            reports_list = self.components_only(reports_list, components)

        if not reports_list:
            self.info("::: No components or instances selected with your filter.")
            self.info("::: Options are: %s" % ', '.join(
                self._get_names(reports_list_orig)))
            return
        self._download_reports(reports_list, self.reports_path(run_uuid))

    def _download_reports(self, reports_list, reports_path):
        self.mkdir(reports_path)
        self.info("\n::: Downloading reports to '%s'" % reports_path)

        for r in reports_list:
            resp = self.api.cimi_operation(r['id'], 'http://sixsq.com/slipstream/1/action/download')
            furl = resp.json['uri']
            self.info('... {}: {}'.format(r['component'], furl))
            util.download_file(furl, os.path.join(reports_path, r['component'] + '.tgz'))

    @staticmethod
    def _get_names(reports):
        return set(map(lambda x: x.json['component'], reports))

    def info(self, msg, data=None):
        print(msg)
        if data:
            pprint.pprint(data)

    def debug(self, msg, data=None):
        if self.verboseLevel > 1:
            self.info(msg, data)

    def warn(self, msg, data=None):
        print("WARNING: %s" % msg)
        if data:
            pprint.pprint(data)
