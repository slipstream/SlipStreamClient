"""
 SlipStream Client
 =====
 Copyright (C) 2013 SixSq Sarl (sixsq.com)
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

import tarfile
import zipfile
import tempfile

import os


def collectResultInfo(path, prefix="", subdirs=[], results=[]):
    full_path, relative_path = getPaths(path, prefix, subdirs)

    if os.path.isfile(full_path):
        results.append([full_path, relative_path])
    else:
        if os.path.isdir(full_path):
            for child in os.listdir(full_path):
                subdirs.append(child)
                collectResultInfo(path, prefix, subdirs, results)
                subdirs.pop()

    return results


def getPaths(root, prefix, elements):
    full_path = root
    relative_path = prefix
    for element in elements:
        full_path = os.path.join(full_path, element)
        relative_path = os.path.join(relative_path, element)
    return full_path, relative_path


def archiveResultsAsTarball(archive_name, results):
    tarball = os.path.join(tmpdir, archive_name + '.tar.gz')
    with tarfile.open(tarball, 'w|gz') as tar:
        for result in results:
            name, altname = result
            tar.add(name, arcname=altname)
    return tarball


def archiveResultsAsZipArchive(archive_name, results):
    tmpdir = tempfile.mkdtemp()
    ziparchive = os.path.join(tmpdir, archive_name + '.zip')
    with zipfile.ZipFile(ziparchive, 'w') as zip:
        for result in results:
            name, altname = result
            zip.write(name, arcname=altname)
    return ziparchive


def createResultsTarball(rootdirs, archive_name, prefix):
    results = []
    for rootdir in rootdirs:
        results = collectResultInfo(rootdir, prefix, [], results)
    return archiveResultsAsTarball(archive_name, results)


def createResultsZipArchive(rootdir, archive_name, prefix):
    results = []
    for rootdir in rootdirs:
        results = collectResultInfo(rootdir, prefix, [], results)
    return archiveResultsAsZipArchive(archive_name, results)
