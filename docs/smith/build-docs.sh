#!/bin/bash

revdate=$(date)
echo revdate: $revdate 

a2x -f pdf -L --dblatex-opts=" -s asciidoc-dblatex.sty" -a revdate="$revdate" manual.asc
a2x -f xhtml manual.asc
