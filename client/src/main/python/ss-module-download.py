#!/usr/bin/env python
"""
 SlipStream Client
 =====
 Copyright (C) 2014 SixSq Sarl (sixsq.com)
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

import sys

from slipstream.command.ModuleDownloadCommand import ModuleDownloadCommand


class MainProgram(ModuleDownloadCommand):
    """Recursively download SlipStream modules as XML from server."""

    def __init__(self):
        super(MainProgram, self).__init__()

    def parse(self):
        usage = '''usage: %prog [options] <module-uri>

<module-uri>    Name of the root module.'''

        self.parser.usage = usage

        self.add_authentication_options()
        self.add_endpoint_option()

        self.parser.add_option('--remove-cloud-specific', dest='remove_clouds',
                               help='Remove all cloud specific elements (image ids, cloud parameters, ...)',
                               default=False, action='store_true')

        self.parser.add_option('--dump-image-ids', dest='dump_image_ids',
                               help='Store image IDs found in image modules into per module files.',
                               default=False, action='store_true')

        self.parser.add_option('--dump-image-ids-dir',
                               dest='dump_image_ids_dir',
                               help='Path to the directory to store the image IDs files. Default: current directory.',
                               default='.')

        self.parser.add_option('--remove-group-members',
                               dest='remove_group_members',
                               help='Remove members of the group in the authorizations',
                               default=False, action='store_true')

        self.parser.add_option('--reset-commit-message',
                               dest='reset_commit_message',
                               help='Replace the commit message by "Initial version of this module"',
                               default=False, action='store_true')

        self.parser.add_option('--flat', dest='flat_export',
                               help='Download without creating subdirectories',
                               default=False, action='store_true')

        self.options, self.args = self.parser.parse_args()

        self._check_args()

    def _check_args(self):
        if len(self.args) == 1:
            self.module_uri = self.args[0]
        if len(self.args) < 1:
            self.usageExitTooFewArguments()
        if len(self.args) > 1:
            self.usageExitTooManyArguments()

    def do_work(self):
        queue = [self.module_uri]
        while len(queue) > 0:
            module_uri = queue.pop(0)
            print('Processing: %s' % module_uri)

            root = self._retrieve_module_as_xml(module_uri)
            self._remove_transient_elements(root)
            if self._is_image(root) and self.options.dump_image_ids:
                self._dump_image_ids(root, self.options.dump_image_ids_dir)
            if self.options.remove_clouds:
                self._remove_clouds(root)
            if self.options.remove_group_members:
                self._remove_group_members(root)
            if self.options.reset_commit_message:
                self._reset_commit_message(root)
            self._write_module_as_xml(root, module_uri, self.options.flat_export)

            for child in self._get_module_children(module_uri, root):
                queue.append(child)


if __name__ == "__main__":
    try:
        MainProgram()
    except KeyboardInterrupt:
        print('\n\nExecution interrupted by the user... goodbye!')
        sys.exit(-1)
