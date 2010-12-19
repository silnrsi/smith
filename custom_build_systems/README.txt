The new "concurrent.futures" module from Python 3.2 will make it
easier to execute tasks concurrently:
http://www.python.org/dev/peps/pep-3148/

It may be tempting to try to create a new build system by trying to
extend the executor, but quite a few complicated tasks are still ahead:

* reinventing a system for handling commands and command-line options
* adding a system of (task) order and dependencies
* creating an extension system for new programming languages
* adding support for python versions < 3.2

This represents a lot of work, and there are of course the risks of making
typical design mistakes which may lead to poor usability, poor extensibility,
and poor performance.

These pitfalls and many others are already solved in the Waf build system, which
also enables the re-use of its components into new build tools. Re-using the
components also means much more time to work on the interesting problems such as
creating an intuitive XML/YAML/JSON schema or creating a domain-specific programming
language (make-like, cmake-like, ...), or extracting commands and dependencies to
create derivated files (Makefiles, Visual studio, ..)

A few examples are provided to show the range of possibilities:
* overview:        how to create a custom file using the waf framework to perform a simple build
* parser:          how to add a parser for a domain-specific language
* noscript:        infer what to build from given files, use no script file
* makefile_dumper: create a makefile corresponding to the current build, extracting as many dependencies as possible

Thomas Nagy, 2010
