#!/bin/sh

configure() {
  smith distclean
  smith configure
}

build() { 
  smith build $CI_MODE
}

tests() {
  smith pdfs $CI_MODE
  smith test $CI_MODE
  smith xtest $CI_MODE
  smith waterfall $CI_MODE
  smith xfont $CI_MODE
  smith ftml
  smith ots
  smith ttfchecks
  smith -j1 sile
}

sileftml_tests() {
  smith -j1 sileftml
}

lint() {
  smith validate  
  #smith ots       
  #smith fontlint
}
  
coverage() { 
  smith pyfontaine 
}

bundle() {
  smith zip    
  smith tarball
}

buildinfo() {
  smith buildinfo
}

release() { 
  smith release
}

cd "$1"
git clean -f
configure
build
tests 
#sileftml_tests
lint
#coverage
bundle
buildinfo
release
cd -
