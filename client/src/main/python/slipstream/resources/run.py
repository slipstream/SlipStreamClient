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

RUN_STATES = ('Initializing',
              'Provisioning',
              'Executing',
              'SendingReports',
              'Ready',
              'Finalizing',
              'Done',
              'Cancelled',
              'Aborted')

FINAL_STATES = ('Done',
                'Cancelled',
                'Aborted')


def run_url_to_uuid(run_url):
    return run_url.rsplit('/', 1)[-1]


def run_states_after(state):
    return RUN_STATES[RUN_STATES.index(state) + 1:]
