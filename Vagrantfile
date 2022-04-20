# -*- mode: ruby -*-
# vi: set ft=ruby :
# Vagrant file config to get the latest smith and its dependencies 
# put this in your project folder along with the provision.sh file referenced below.


Vagrant.configure("2") do |config|
  config.vm.provider :docker do |d|
     d.build_dir = "."
     build_args = "--type=interactive"
     d.remains_running = true
     d.has_ssh = true
  end



  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  # config.vm.synced_folder ".", "/smith", type: "virtualbox"
  config.vm.synced_folder "/home/nico/repos/wstechfonts/", "/smith",  docker_consistency: "delegated"

  # set up a distinguishable hostname
  config.vm.hostname = "smith-docker"
end
