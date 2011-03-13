#! /bin/bash

# make a copy of a waf directory with the same name
#

rm -rf tmp
mkdir tmp

pushd c
waf configure build
popd
cp -R c tmp/c

cd tmp/c
waf configure build

