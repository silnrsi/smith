#!/bin/bash
set -e
stat_gid=$(stat --printf '%g' /smith)
stat_uid=$(stat --printf '%u' /smith)
groupadd -f -g ${BUILDER_GID:=${stat_gid/#0/1000}} builder
useradd -m builder -u ${BUILDER_UID:=${stat_uid/#0/1000}} -g $BUILDER_GID
CMND="$@"
echo Welcome to the smith interactive font build system.
cd /smith
exec runuser builder --pty --command="exec $CMND"
