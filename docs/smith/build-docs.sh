#!/bin/bash

#a2x -v -f xhtml manual.asc
asciidoctor -t -v -b xhtml5 -n -a toc=left -a source-highlighter=pygments manual.adoc


