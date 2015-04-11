#!/bin/bash

# Metadata of the smith source tree
revnumber=`hg tip | grep "changeset" | cut -d : -f 2-`
revremark=`hg tip | grep -A2 "description" | cut -d : -f 2-`
revdate=`hg tip | grep "date" | cut -d : -f 2-`
revauthor=`hg tip | grep "user" | cut -d : -f 2-`
revrelease=`hg tags | tail -n1`

# Make and install the manual
echo revnumber: $revnumber
echo revremark: $revremark
echo revdate: $revdate 
echo revauthor: $revauthor
echo revrelease: $revrelease

a2x -f pdf -L --dblatex-opts=" -s asciidoc-dblatex.sty" -a revnumber="Current revision: $revnumber" -a revremark="Last commit log:'$revremark'. Current realease: $revrelease" -a revdate="$revdate" -a author="revauthor"  manual.txt
a2x -f xhtml manual.txt
