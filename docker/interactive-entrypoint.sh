#!/bin/bash
set -e
groupadd -f -g ${BUILDER_GID:=$(stat --printf '%g' /smith)} builder
useradd -o -m builder -u ${BUILDER_UID:=$(stat --printf '%u' /smith)} -g $BUILDER_GID
CMND="$@"
echo Welcome to the smith interactive font build system.
exec runuser builder --pty --command="exec $CMND"
