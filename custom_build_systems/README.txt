The new "concurrent.futures" module from Python 3.2 will make it
easier to execute tasks concurrently:
http://www.python.org/dev/peps/pep-3148/

Many developers will be tempted to create new build systems, but all these tools
will suffer from quite a few shortcomings such as:

* adding support for python versions < 3.2
* reinventing a system for handling commands and command-line options
* adding a system of (task) order and dependencies
* creating an extension system for new programming languages

There is quite a lot of work behind all these tasks, and the new tools
can fall easily in design errors that may lead to poor performance
or to poor extensibility.

Re-using the Waf framework is certainly smarter than starting from scratch,
and will leave more time to work on the user-visible areas: providing
a new programming language, creating an intuitive XML/YAML/JSON schema, or
extracting commands and dependencies to create Makefiles/Visual studio files...

The examples in this folder are:
* overview: how to create a custom file using the waf framework to perform a simple build
* ...

