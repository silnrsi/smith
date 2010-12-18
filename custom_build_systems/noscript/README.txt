This example demonstrates the creation of a particular build tool which compiles
specific files directly, for example:

main.c includes foo.h
foo.h has a corresponding foo.c file
foo.c includes bar.h
bar.h has a corresponding bar.c file

Calling './dbd build' will then compile and link 'main.c', 'foo.c' and 'bar.c' into the program 'app'

To create the build tool:
   ./create_it.sh

To use on the file bbit which creates a program out of main.c:
   ./cbd clean build

