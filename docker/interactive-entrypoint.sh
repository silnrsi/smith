#!/bin/bash
set -e
echo Welcome to the smith interactive font build system.
useradd -m builder -u $BUILDER -U
CMND="$@"
exec runuser builder --pty --command="exec $CMND"
