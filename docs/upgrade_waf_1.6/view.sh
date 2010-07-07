#! /bin/bash

dot -Teps -ocore.eps core.dot
a2x -L -a toc --icons-dir=.   -v   --icons -d article -f pdf upgrade_waf_1.6.txt && okular *.pdf

