# shellcheck shell=sh

# extend PATH to include standard folder containing extra utilities to run within the smith toolchain environment
if [ -d "/smith/bin" ] ; then 
		PATH="/smith/bin:$PATH"
fi
