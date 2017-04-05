
# Scalable deployments


In the case of mutable deployments during a scaling action the following 
environment variables are available for the user hook scripts (`OnVmAdd`, `OnVmRemove`, 
`Pre-Scale`, `Post-Scale`).

```
SLIPSTREAM_SCALING_NODE   # node name
SLIPSTREAM_SCALING_VMS    # space separated list of node instance names (<nodename>.<id>)
SLIPSTREAM_SCALING_ACTION # name of the scaling action <vm_resize|disk_attach|disk_detach|vm_remove>
```


## Horizontal scalability

If required, the script should be defined in the image module's `OnVmAdd` and/or `OnVmRemove` 
targets. `SLIPSTREAM_SCALING_NODE` and `SLIPSTREAM_SCALING_VMS` are intended to be used in 
the following way (`Bash` example).

```bash
#!/bin/bash
set -e

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


## Vertical and horizontal scalability

If required, the scripts should be defined in the image module's `Pre-Scale` and/or `Post-Scale` 
targets and are intended to be used before and/or after the scaling up/down actions.  The scripts
are only executed on the VMs that are subject to the current scaling action.  Below are the 
example scripts for `Bash`.

`Pre-Scale` script.  Note that it can be used on VM remove horizontal scalability action.

```bash
#!/bin/bash
set -e

# Pre-scale: intended to be ran before any vertical scaling and horizontal downscaling action. 

function before_vm_remove() { echo "Before VM remove"; }
function before_vm_resize() { echo "Before VM resize"; }
function before_disk_attach() { echo "Before disk attach"; }
function before_disk_detach() { echo "Before disk detach"; }

case $SLIPSTREAM_SCALING_ACTION in
  vm_remove)
      before_vm_remove ;;
  vm_resize)
      before_vm_resize ;;
  disk_attach)
      before_disk_attach ;;
  disk_detach)
      before_disk_detach ;;
esac
```


`Post-Scale` script. Note: only for vertical scaling actions.

```bash
#!/bin/bash
set -e

# Post-Scale: intended to be ran after vertical scaling action. 

function after_vm_resize() { echo "After VM resize"; }
function after_disk_attach() { echo "After disk attach"; }
function after_disk_detach() { echo "After disk detach"; }

case $SLIPSTREAM_SCALING_ACTION in
  vm_resize)
      after_vm_resize ;;
  disk_attach)
      after_disk_attach ;;
  disk_detach)
      after_disk_detach ;;
esac
```

