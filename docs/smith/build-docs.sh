#!/bin/bash

# Metadata of the smith source tree
revdate=$(git log -n 1 | grep "Date" | cut -d : -f 2-)
revauthor=$(git log -n 1 | grep "Author" | cut -d : -f 2-)

# Make and install the manual
echo revdate: $revdate 
echo revauthor: $revauthor

a2x -f pdf -L --dblatex-opts=" -s asciidoc-dblatex.sty" -a revdate="$revdate" -a author="$revauthor" manual.txt
a2x -f xhtml manual.txt
