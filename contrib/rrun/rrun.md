# rrun - copy there and back again for smith

## Introduction

When using a virtual machine (VM) to run smith, it can be convenient to keep the project files in a shared folder so they can be accessed and modified from your host environment, and then use the VM to build the project.

However, keeping the project in shared folders costs in performance: building the project directly in the shared folders is two to three times slower than if the project folder were in the VM's emulated drive.

There is a way to have both the convenience of shared folders and the performance of the emulated drive. `rrun` will rsync the project files from the shared drive to the emulated drive, run smith on that on that copy, and then rsync everything back. Even with the overhead of the rsync commands, you come out ahead.

## Installation

Copy `rrun` to some place on your path such as `~/bin`. Make it executable if it isn't already (`chmod 755 rrun`).

## Usage

```
cd myProjectRoot
smith distclean
smith configure
rrun smith build
```

`rrun` first uses `rsync` to copy/sync the entire current directory to a folder in the VM. It then, using that copy, runs whatever command was provided as parameters, then uses rsync to copy any changes back. 

The first time you use `rrun`, it will take longer because it has to sync the entire project to the emulated drive in the VM. Subsequent runs are faster because it has to sync only changes. Similarly, any time there are major changes to the source tree, e.g., after running `smith distclean`, the initial rsync will take more time.

Note that mixing `smith some_command` and `rrun smith other_command` is safe, so for commands like `smith distclean` and `smith configure` that are quick to execute, it is more efficient to run those directly rather than via `rrun`.

## Caveats

It is not advisable to make modifications to the shared folder, for example from your host, while `rrun` is executing since there is a risk that such changes may be lost when the rsync copies the results back.

## Authors
Martin Hosken, Tim Eves
