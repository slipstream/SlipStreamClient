#!/bin/bash
set -e
project_build_dir=${1:?"Project build directory is not provided."}
cp -r ${project_build_dir}/slipstream-api/src/slipstream/api ${project_build_dir}/client/lib/slipstream
tar -zcf ${project_build_dir}/slipstreamclient.tgz -C ${project_build_dir}/client \
    bin lib sbin etc setup.cfg setup.py