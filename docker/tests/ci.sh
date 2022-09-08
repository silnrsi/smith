#!/bin/sh

configure() {
  smith distclean
  smith configure
}

build() { 
  smith build 
}

tests() {
  smith pdfs      
  smith test      
  smith xtest     
  smith waterfall 
  smith xfont     
  smith ftml      
  smith ots
  smith ttfchecks       
  smith sile
}

sileftml_tests() {
  smith sileftml;
}

lint() {
  smith validate  
  smith ots       
  smith fontlint
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
configure
build
tests 
#sileftml_tests

#lint
#coverage
bundle
buildinfo
release
cd -
