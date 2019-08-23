#!/usr/bin/env bash
# A provisioning script for Vagrant to make it easier to get the latest smith and its dependencies from the PPAs and/or source.
# This is designed to be called by the Vagrantfile wich expects this file to be in the same directory by default.

# This is for Ubuntu bionic/18.04 LTS

# configure things for non-interactive and sdtin
ex +"%s@DPkg@//DPkg" -cwq /etc/apt/apt.conf.d/70debconf
dpkg-reconfigure debconf -f noninteractive -p critical


echo " "
echo " "
echo "Installing smith and its dependencies"
echo " "
echo " "


# the official smith PPA
add-apt-repository -s -y ppa:silnrsi/smith-py3

# the TexLive 2019 backports PPA
add-apt-repository -s -y ppa:jonathonf/texlive-2019

# the current git PPA
add-apt-repository -s -y ppa:git-core/ppa

apt-get update -y -q
apt-get upgrade -y -q -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-overwrite" -u -V --with-new-pkgs

# toolchain components currently built from source
# these are now commented out as the corresponding items are available as packages or on the CI
# if you need certain features you can uncomment them and reprovision. 


# install pip3 and fontbakery 
apt-get install python3-pip -y 
pip3 install --upgrade git+https://github.com/googlefonts/fontbakery.git@master#egg=fontbakery


# checking if we already have local checkouts 
# if [ -d /usr/local/builds/ ]
# then
#     echo " "
#     echo "You already have previous builds, it's easier to delete them and start afresh. "
#     echo " "
#     echo "Deleting /usr/local/builds... "
#     echo " "
#     rm -rf /usr/local/builds
# fi
# 
# mkdir -p /usr/local/builds
# 
# chmod -R 766 /usr/local/builds 
# 
# # graphite
# echo " "
# echo " "
# echo "Installing graphite from source"
# echo " "
# echo " "
# 
# 
# apt-get install build-essential cmake gcc g++ automake libtool pkg-config -y -q
# cd /usr/local/builds
# git clone --depth 1 https://github.com/silnrsi/graphite.git
# cd graphite
# mkdir build
# cd build
# cmake -G "Unix Makefiles" --build .. -DGRAPHITE2_COMPARE_RENDERER:BOOL=OFF
# make
# make install
# ldconfig 
# 
# 
# echo " "
# echo " "
# echo "Installing Graphite-enabled HarfBuzz from source"
# echo " "
# apt-get install build-essential cmake gcc g++ libfreetype6-dev libglib2.0-dev libcairo2-dev automake libtool pkg-config ragel gtk-doc-tools -y -q
# cd /usr/local/builds
# git clone --depth 1 https://github.com/harfbuzz/harfbuzz.git
# cd harfbuzz
# ./autogen.sh --with-graphite2 
# make
# make install
# ldconfig 
# 
# 

# toolchain components installed from packages (both main repositories and PPAs)
apt-get install libharfbuzz-bin -y -q

# smith itself (only the font side of things)
echo " "
echo " "
echo "Installing smith (downloading/updating the dependencies might take a few minutes)"
echo " "
echo " "

apt-get install smith-font --no-install-recommends -y -q

# smith options
# none for now

echo " "
echo " "
echo "Done!"
echo " "
echo " "
echo "smith is now ready to use:"
echo " "
echo "Smith version: "
apt-cache show smith | grep Version: | grep snapshot
echo " "
echo " "

echo "To go to the shared folder to run smith commands on your project(s), type:" 
echo " "
echo "vagrant ssh"
echo "cd /smith"
echo "cd <folder of my project(s)>"
echo "smith distclean"
echo "smith configure"
echo "smith build"
echo "smith alltests"
echo "smith zip"
echo "smith tarball"
echo "smith release"
echo "for more details type: man smith"
echo "or refer to the smith manual in /usr/share/doc/python3-smith/ or https://github.com/silnrsi/smith/tree/master/docs/smith"
echo " "


