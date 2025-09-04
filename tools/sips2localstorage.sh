#!/bin/bash

# sips2localstorage.sh
#
# A tool for submitting one or more SIPS to the local edepot instance.
# Uses rsync.

REPOSITORY_ID="nl-wbdrazu"
LOCAL_EDEPOT_BASEDIR="/mnt/nas/edepot/"

# do we know where the sips are stored?
if [ $# -eq 0 ]; then
    echo "Stores the contents of a SIP in the local edepot at ${LOCAL_EDEPOT_BASEDIR}"
    echo
    echo "Usage: $0 <sipsdir>"
    exit 1
fi
sipsdir="$1"

# do specified folders exist?
if [ ! -d "$sipsdir" ]; then
    echo "Error: Directory '$sipsdir' does not exist"
    exit 1
fi

if [ ! -d "${LOCAL_EDEPOT_BASEDIR}" ]; then
    echo "Error: Directory '${LOCAL_EDEPOT_BASEDIR}' does not exist"
    exit 1
fi

# sync each sip:
pushd "$sipsdir"
for dir in `ls -d */${REPOSITORY_ID}/` ; do   # this a simple sanity check
    cd $dir
    cd ..
    bucket=`ls ${REPOSITORY_ID}/`
    pwd
    if [ -n "$bucket" ]; then
        echo "Synchronizing collection $dir to ${bucket} in ${LOCAL_EDEPOT_BASEDIR}" | sed "s@/${REPOSITORY_ID}/@@"
        rsync -r --info=stats2 ${REPOSITORY_ID} ${LOCAL_EDEPOT_BASEDIR}${bucket}/
    else
        echo "Skipping collection $dir: empty bucket" | sed "s@/${REPOSITORY_ID}/@@"
    fi
    cd "$sipsdir"
done
popd 

echo "Ready."
exit 0
