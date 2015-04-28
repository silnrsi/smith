#!/bin/bash

# Metadata of the smith source tree
revnumber=`hg tip | grep "changeset" | cut -d : -f 2-`
revdate=`hg tip | grep "date" | cut -d : -f 2-`
revremark=`hg tip | grep -A2 "description" | cut -d : -f 2-`
revrelease=`hg tags | sed -n '2p'`

# Make and install the manual
echo revnumber: $revnumber
echo revremark: $revremark
echo revdate: $revdate 
echo revrelease: $revrelease

a2x -f pdf -L --dblatex-opts=" -s asciidoc-dblatex.sty" -a revnumber="release: $revrelease" -a revdate="$revdate" -a revremark="last commit log: $revremark"  -a author="$revauthour" manual.txt
a2x -f xhtml manual.txt
