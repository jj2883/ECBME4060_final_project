#!/bin/bash
#
# Download some published MHC I ligand data
#
#
set -e
set -x

DOWNLOAD_NAME=data_published
SCRATCH_DIR=${TMPDIR-/tmp}/mhcflurry-downloads-generation
SCRIPT_ABSOLUTE_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"

mkdir -p "$SCRATCH_DIR"
rm -rf "$SCRATCH_DIR/$DOWNLOAD_NAME"
mkdir "$SCRATCH_DIR/$DOWNLOAD_NAME"

# Send stdout and stderr to a logfile included with the archive.
exec >  >(tee -ia "$SCRATCH_DIR/$DOWNLOAD_NAME/LOG.txt")
exec 2> >(tee -ia "$SCRATCH_DIR/$DOWNLOAD_NAME/LOG.txt" >&2)

# Log some environment info
date
pip freeze
# git rev-parse HEAD
git status

cd $SCRATCH_DIR/$DOWNLOAD_NAME

# Download kim2014 data
wget --quiet https://github.com/openvax/mhcflurry/releases/download/pre-1.1/bdata.2009.mhci.public.1.txt
wget --quiet https://github.com/openvax/mhcflurry/releases/download/pre-1.1/bdata.20130222.mhci.public.1.txt
wget --quiet https://github.com/openvax/mhcflurry/releases/download/pre-1.1/bdata.2013.mhci.public.blind.1.txt

# Download abelin et al 2017 data
wget --quiet https://github.com/openvax/mhcflurry/releases/download/pre-1.1/abelin2017.hits.csv.bz2

cp $SCRIPT_ABSOLUTE_PATH .
bzip2 LOG.txt
tar -cjf "../${DOWNLOAD_NAME}.tar.bz2" *

echo "Created archive: $SCRATCH_DIR/$DOWNLOAD_NAME.tar.bz2"
