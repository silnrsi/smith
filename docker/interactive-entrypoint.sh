#!/bin/bash
set -e

stat_gid=$(stat --printf '%g' /smith)
stat_uid=$(stat --printf '%u' /smith)
groupadd -f -g ${BUILDER_GID:=${stat_gid/#0/1000}} builder
useradd -m builder -o -u ${BUILDER_UID:=${stat_uid/#0/1000}} -g $BUILDER_GID
CMND="$@"
release=$(grep "RELEASE" /etc/lsb-release | cut -d "=" -f2 )
codename=$(grep "CODENAME" /etc/lsb-release | cut -d "=" -f2)
echo "Welcome to smith: font development, testing and release ($codename - $release)".
cd /smith
exec runuser builder --pty --command="exec $CMND"
