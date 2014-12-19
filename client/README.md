
Mutable deployments
===================


In the case of mutable deployments during a scaling action the following environment variables are available for the user hook scripts

```
SLIPSTREAM_SCALING_NODE # node name
SLIPSTREAM_SCALING_VMS  # space separated list of node instance names (<nodename>.<id>)
```

They are intended to be used in the following way (Bash example).


```bash
#!/bin/bash
set -e
set -x

# Example:
# In a deployment with A, B, C node types, where A depends on changes in B and C,
# on a node instance of a type A one would use the following pattern

function on_B() {
    # Do something specific for the node instances of type B
    for INSTANCE_NAME in $SLIPSTREAM_SCALING_VMS; do
        echo Processing $INSTANCE_NAME
        # Do something here. Example:
        ss-get $INSTANCE_NAME:ready
        host_name=$(ss-get $INSTANCE_NAME:hostname)
        echo "New instance of $SLIPSTREAM_SCALING_NODE: $INSTANCE_NAME, $host_name"
    done
}

function on_C() {
    # Do something specific for the node instances of type C
    for NAME in $SLIPSTREAM_SCALING_VMS; do
        # Do the needful
    done
}

case $SLIPSTREAM_SCALING_NODE in
    "B" )
        on_B ;;
    "C" )
        on_C ;;
esac
```
