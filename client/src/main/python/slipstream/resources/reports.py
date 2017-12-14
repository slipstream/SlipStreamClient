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
import json
from datetime import datetime
from urlparse import urlparse
import pprint

import slipstream.util as util
from slipstream.NodeDecorator import NodeDecorator
from slipstream.HttpClient import get_cookie, DEFAULT_SS_COOKIE_NAME

TIME_FORMAT = '%Y-%m-%dT%H%M%SZ'
NO_SESSION_PROVIDED_MSG = "Session should have been provided along with " \
                          "config holder."


def is_newer(d1, d2, tf=TIME_FORMAT):
    return datetime.strptime(d1, tf) < datetime.strptime(d2, tf)


class ReportsGetter(object):

    def __init__(self, ch):
        """Expects an authenticated session provided with 'ch' config holder.
        The class uses url `domain`/`path` and the name of cookie to get it
        from the session and use in the downloading of the requested reports.
        """
        self.output_dir = os.getcwd()
        self.verboseLevel = 0
        self.endpoint = 'https://nuv.la'
        self.session = None

        ch.assign(self)

        if self.session is None:
            raise Exception(NO_SESSION_PROVIDED_MSG)

    @staticmethod
    def latest_only(reports):
        reports_filtered = {}
        for r in reports:
            not_yet_added = r['node'] not in reports_filtered
            if not_yet_added:
                reports_filtered[r['node']] = r
            else:
                # replace if newer
                if is_newer(reports_filtered[r['node']]['date'], r['date']):
                    reports_filtered[r['node']] = r

        return reports_filtered.values()

    @staticmethod
    def remove_orch(reports):
        reports_no_orch = []
        for r in reports:
            if not NodeDecorator.is_orchestrator_name(r['node']):
                reports_no_orch.append(r)
        return reports_no_orch

    @staticmethod
    def components_only(reports, comps):
        reports_only = []

        for r in reports:
            name = r['node']
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

    def run_reports_url(self, run_uuid):
        return self.endpoint + util.REPORTS_RESOURCE_PATH + "/" + run_uuid + "/"

    def list_reports(self, run_uuid):
        res = self.session.get(self.run_reports_url(run_uuid),
                               headers={'accept': 'application/json'})
        reports = json.loads(res.text)['files']
        self.debug("::: List of all reports. :::", reports)

        return reports

    def get_reports(self, run_uuid, components=None, no_orch=False):
        if components is None:
            components = []
        reports_list_orig = self.list_reports(run_uuid)
        if not reports_list_orig:
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

    def _get_cookie(self, url_str, name):
        url = urlparse(url_str)
        domain = url.netloc
        path = url.path
        return get_cookie(self.session.cookies, domain=domain, path=path,
                          name=name)

    def _download_reports(self, reports_list, reports_path):
        self.mkdir(reports_path)
        self.info("\n::: Downloading reports to '%s'" % reports_path)

        for f in reports_list:
            furl = f['uri']
            cookie = self._get_cookie(furl, DEFAULT_SS_COOKIE_NAME)
            if not cookie:
                self.warn("Skipping. Cookie not found for '%s' with name '%s'" %
                          (furl, DEFAULT_SS_COOKIE_NAME))
                continue
            self.info("... %s" % furl)
            self.debug("... cookie %s" % cookie)
            util.download_file(furl, os.path.join(reports_path, f['name']),
                               cookie)

    def _get_names(self, reports):
        return set(map(lambda x: x['node'], reports))

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
