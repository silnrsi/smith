#!/bin/bash

revdate=$(date)
echo revdate: $revdate 

a2x -v -f pdf -L --dblatex-opts=" -s asciidoc-dblatex.sty" -a revdate="$revdate" manual.asc
a2x -v -f xhtml manual.asc
a2x -v -f epub -d book manual.asc 