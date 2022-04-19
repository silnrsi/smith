#!/usr/bin/env bash

# A provisioning script for Vagrant to make it easier to get the latest smith and its dependencies from the PPAs and/or source.
# This is designed to be called by the Vagrantfile wich expects this file to be in the same directory by default.

# debug
set +xv

# This is for Ubuntu jammy/22.04 LTS

# configure things for non-interactive and sdtin
sudo ex +"%s@DPkg@//DPkg" -cwq /etc/apt/apt.conf.d/70debconf
sudo dpkg-reconfigure debconf -f noninteractive -p critical

export DEBIAN_FRONTEND=noninteractive

# debugging 
# set -x	


echo " "
echo " "
echo "Installing smith and its dependencies"
echo " "
echo " "

#
# Configuration options:
#

# set to True to compile Graphite and harfbuzz from source (including tracing):
graphiteFromSource=True
# graphiteFromSource=False

# set to True to compile opentype-sanitiser/ots from source
otsFromSource=True
# otsFromSource=False

# set to True to compile FontValidator from source
FontValFromSource=True
# FontValFromSource=False

# set to True to include the sklearn module
includeSklearn=True
#includeSklearn=False

# to pin particular version of fontTools, set that version number here, else set to empty
# fontToolsHoldVersion=4.17.1
fontToolsHoldVersion=

# set to True to compile ttfautohint source:
# ttfautohintFromSource=True
ttfautohintFromSource=False


# End of configuration options


# the official smith PPA
sudo add-apt-repository -s -y ppa:silnrsi/smith-py3 

# the current git PPA
sudo add-apt-repository -s -y ppa:git-core/ppa 

# set git params in ~/.gitconfig
git config --global pull.rebase false


# the official SILE PPA
sudo add-apt-repository -s -y ppa:sile-typesetter/sile 

sudo apt-get update -y -qq
sudo apt-get upgrade -y -qq -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -o Dpkg::Options::="--force-overwrite" -u -V --with-new-pkgs

# toolchain components currently built from source or retrieved via pypi
# according to the features you need you can fill in the variables above or comment/uncomment accordingly before reprovisionning


# install pip3 
sudo apt-get install python3-pip -y -qq
python3 -m pip install --upgrade pip --user  --no-warn-script-location 

# config
pip config set install.no-warn-script-location false
pip config set global.disable-pip-version-check true


# generic toolchain
sudo apt-get install build-essential cmake gcc g++ automake libtool pkg-config icu-devtools libicu-dev  -y -qq

python3 -m pip install --upgrade setuptools-git-ls-files setuptools-scm

# checking if we already have local checkouts 
 if [ -d $HOME/srcbuilds ]
then
    echo " "
    echo "You already have previous builds, it's easier to delete them and start afresh. "
    echo " "
    echo "Deleting srcbuilds folder... "
    echo " "
    sudo rm -rf $HOME/srcbuilds
fi

mkdir -p $HOME/srcbuilds




# Graphite and Harfbuzz

if [ "$graphiteFromSource" == "True" ]; then
	echo " "
	echo " "
	echo "Installing Graphite from source"
	echo " "
	echo " "


	sudo apt-get install build-essential cmake gcc g++ automake libtool pkg-config -y -qq
	cd $HOME/srcbuilds
	git clone --depth 1 https://github.com/silnrsi/graphite.git
	cd graphite
	mkdir build
	cd build
	cmake -G "Unix Makefiles" .. -DGRAPHITE2_COMPARE_RENDERER:BOOL=OFF -DGRAPHITE2_NTRACING:BOOL=OFF  -DPYTHON_EXECUTABLE=python3
	make
	sudo make install
	cd ..
	python3 setup.py -v install --user
	sudo ldconfig  

	echo " "
	echo " "
	echo "Installing Graphite-enabled HarfBuzz from source"
	echo " "
	sudo apt-get install pkg-config gcc ragel gcovr gtk-doc-tools libfreetype6-dev libglib2.0-dev libcairo2-dev libicu-dev libgraphite2-dev python3-setuptools gobject-introspection libgirepository1.0-dev -y -qq
	cd $HOME/srcbuilds
	git clone --depth 1 https://github.com/harfbuzz/harfbuzz.git
	cd harfbuzz

	python3 -m pip install --upgrade git+https://github.com/mesonbuild/meson.git@master#egg=meson --user
	sudo python3 -m pip install --upgrade ninja
	meson build -Db_coverage=true --auto-features=enabled -Dgraphite=enabled  --buildtype=debugoptimized --wrap-mode=nodownload -Dexperimental_api=true -Dchafa=disabled
	ninja -C build
	sudo ninja install -C build
	sudo ldconfig 

	# crude chown because Harfbuzz wants write-access to optimize runs of its utilities
	sudo chmod -R 776 $HOME/srcbuilds
	sudo chown -R vagrant:vagrant $HOME/srcbuilds
fi

# ots 
if [ "$otsFromSource" == "True" ];
then
	python3 -m pip install --upgrade git+https://github.com/mesonbuild/meson.git@master#egg=meson --user
	sudo python3 -m pip install --upgrade ninja
	python3 -m pip install --upgrade git+https://github.com/googlefonts/ots-python.git@main#egg=opentype-sanitizer --user

	# ots from main repo (debugging and graphite support on by default)
	sudo apt-get install libfreetype6-dev -y -qq
	cd $HOME/srcbuilds
	git clone --depth 1 --recurse-submodules https://github.com/khaledhosny/ots.git
	cd ots
	meson build
	ninja -C build
	sudo ninja install -C build

else
	python3 -m pip install --upgrade opentype-sanitizer --user
fi

# fontvalidator
if [ "$FontValFromSource" == "True" ];
then
	sudo apt-get install  --no-install-recommends mono-mcs libmono-corlib4.5-cil libmono-system-windows-forms4.0-cil libmono-system-web4.0-cil xsltproc xdg-utils binfmt-support -y -qq 
	cd $HOME/srcbuilds
git clone --depth 1 https://github.com/HinTak/Font-Validator.git fontval
	cd fontval
	make -s --quiet 2>&1 > /dev/null
	make gendoc --quiet  2>&1 > /dev/null
    mkdir -p ~/bin
	sudo cp bin/*.exe ~/bin/
	sudo cp bin/*.dll* ~/bin/
	sudo cp bin/*.xsl ~/bin/
	sudo cp bin/FontValidator.exe ~/bin/FontValidator
fi

# FontValidator shell script
cat > ~/bin/fontval <<'EOF'
#!/bin/bash
   
# running the validator from the usr/local/bin directory  
mono ~/bin/FontValidator.exe -quiet -all-tables -no-raster-tests -report-in-font-dir -file "$1" 
    
exit 0 
  
EOF
    
sudo chmod 755 ~/bin/fontval 



# toolchain components installed from packages (both main repositories and PPAs)

if [ "$graphiteFromSource" == "False" ]
then
	 # still provide the hb utilities even if you don't get the freshest hb from source
	 sudo apt-get install libharfbuzz-bin -y -qq
fi

if [ "$includeSklearn" == "True" ]
then
	# clustering tool needed for collision-avoidance-based kerning:
	python3 -m pip install --upgrade git+https://github.com/scikit-learn/scikit-learn.git@main#egg=scikit-learn --user 
fi


if [ "$fontToolsHoldVersion" == "" ]
then
	# show current version of fonttools installed
	python3 -m pip show fontTools
else
	# target specific version for (or downgrade) fonttools
	python3 -m pip install --upgrade fontTools==$fontToolsHoldVersion --user
fi


# ttfautohint 
if [ "$ttfautohintFromSource" == "True" ];
then
	sudo apt-get install build-essential pkg-config bison flex libfreetype6-dev libharfbuzz-dev libtool autoconf automake qtchooser -y -qq  
	cd $HOME/srcbuilds
	git clone --depth 1 https://repo.or.cz/ttfautohint.git
	cd ttfautohint
	./bootstrap
	./configure --with-qt=no --with-doc=no
	make 

else
	sudo apt-get install ttfautohint -y
fi



# pandoc, weasyprint + deps, Roboto fonts, for generating documentation (makedocs)
sudo apt-get install pandoc pandoc-data -y -qq
python3 -m pip install --upgrade weasyprint --user
python3 -m pip install --upgrade pillow --user
sudo apt-get install fonts-roboto -y -qq
sudo mkdir -p /usr/local/share/fonts/robotomono/
sudo wget --quiet --no-directories --no-parent --continue https://raw.githubusercontent.com/googlefonts/RobotoMono/main/fonts/ttf/RobotoMono-{Regular,Bold,Italic,BoldItalic,Light,LightItalic,Medium,MediumItalic,Thin,ThinItalic}.ttf -P /usr/local/share/fonts/robotomono/

# smith and manual dependencies
echo " "
echo " "
echo "Installing smith (downloading/updating the dependencies might take a few minutes)"
echo " "
echo " "

# smith and manual dependencies
python3 -m pip install --upgrade git+https://github.com/silnrsi/smith.git@master#egg=smith --user

# completion file
wget --quiet --no-directories --no-parent --continue  https://raw.githubusercontent.com/silnrsi/smith/master/bash_completion_smith -O ~/.bash_completion

# man page 
wget --quiet --no-directories --no-parent --continue  https://raw.githubusercontent.com/silnrsi/smith/master/docs/smith/smith.1 -P -O ~/.local/share/man/man1

# other deps 
python3 -m pip install --upgrade git+https://github.com/silnrsi/pysilfont.git@master#egg=pysilfont --user

sudo apt-get install ipython3 python3-gi -y  -qq

sudo apt-get install texlive-xetex --no-install-recommends -y -qq

sudo apt-get install perl-doc libaa-bin xz-utils libtext-unicode-equivalents-perl libtext-pdf-perl libio-string-perl libfont-ttf-scripts-perl libfont-ttf-perl libalgorithm-diff-perl libxml-parser-perl grcompiler libjson-perl libtext-csv-perl  -y -qq


# fontmake deps 
python3 -m pip install --upgrade git+https://github.com/fonttools/fonttools.git@main --user
python3 -m pip install --upgrade git+https://github.com/python-lz4/python-lz4.git@master --user
python3 -m pip install --upgrade git+https://github.com/googlefonts/cu2qu.git@main --user
python3 -m pip install --upgrade git+https://github.com/googlefonts/ufo2ft.git@main --user
python3 -m pip install --upgrade git+https://github.com/robotools/defcon.git@master --user
python3 -m pip install --upgrade git+https://github.com/googlefonts/compreffor.git@main --user
python3 -m pip install --upgrade git+https://github.com/typemytype/booleanOperations.git@master --user
python3 -m pip install --upgrade git+https://github.com/robotools/fontMath.git@master --user
python3 -m pip install --upgrade git+https://github.com/LettError/MutatorMath.git@master --user
python3 -m pip install --upgrade git+https://github.com/eea/odfpy.git@master --user
python3 -m pip install --upgrade git+https://github.com/robotools/fontParts.git@master --user

# other python components and their dependencies 
python3 -m pip install --upgrade git+https://github.com/googlefonts/fontbakery.git@main#egg=fontbakery --user
python3 -m pip install --upgrade git+https://github.com/googlefonts/GlyphsLib.git@main#egg=glyphsLib --user
python3 -m pip install --upgrade git+https://github.com/googlefonts/pyfontaine.git@main#egg=fontaine --user

# other deps from source repo directly?
# brotli ufoLib2 zopfli unicodedata2 beziers

# Palaso + deps 
python3 -m pip install --upgrade git+https://github.com/silnrsi/palaso-python.git@master#egg=palaso --user
python3 -m pip install --upgrade git+https://gitlab.pyicu.org/main/pyicu@main#egg=pyicu  --user
python3 -m pip install --upgrade tabulate freetype-py --user

# install sile 
sudo apt-get install sile -y -qq

# extra packages needed for fontproof
sudo apt-get install wamerican wbritish -y -qq

# install sile extensions: fontproof
echo "removing older versions of the fontproof SILE extension if any" 
sudo rm -rf /usr/share/sile/packagemanager/fontproof/
sudo sile -e 'installPackage("fontproof");os.exit()'


echo " "
echo " "
echo "Done!"
echo " "
echo " "
echo "smith is now ready to use"
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



