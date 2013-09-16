#!/bin/bash

sourcefile=/tmp/slipstream/slipstream.custom.env.conf

if [ -e $sourcefile ]; then
    echo "Sourcing custom environment file: $sourcefile"
    source $sourcefile
fi

/opt/slipstream/client/scripts/slipstream.bootstrap
