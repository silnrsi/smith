#!/bin/bash

asciidoctor -t -v -b xhtml5 -n -a toc=left -a source-highlighter=rouge manual.adoc


