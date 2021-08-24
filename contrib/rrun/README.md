# rrun - copy there and back again for smith

## Introduction

When using a virtual machine (VM) to run smith, it can be convenient to keep the project files in a shared folder so they can be accessed and modified from your host environment, and then use the VM to build the project.

However, keeping the project in shared folders costs in performance: on a Windows host, building the project directly in the shared folders is two to five times slower than if the project folder were in the VM's emulated drive (or, better yet, a ramdrive).

`rrun` provides a way to have both the convenience of shared folders and the performance of a ramdrive. `rrun` will rsync the project files from the shared drive to a ramdrive within the VM, run smith (or any arbitrary command) on that copy, and then rsync everything back. Even with the overhead of the rsync commands, it usually comes out ahead.

## Installation

Within the smith VM, download or copy `rrun` to some place on your path such as `~/bin`. If `~/bin` doesn't exist, create it, copy `rrun` to it, and restart your VM for the path to be updated. Make sure `rrun` is executable if it isn't already (`chmod 755 rrun`) and has Linux (not Windows) line endings.

## Simple usage

```
cd myProjectRoot
smith distclean
smith configure
rrun smith build
```

The first time you use `rrun`, it will take longer because it has to sync the entire project to the emulated drive in the VM. Subsequent runs are faster because it has to sync only changes. Similarly, any time there are major changes to the project tree, e.g., after running `smith distclean`, the initial rsync will take more time.

Mixing `smith some_command` and `rrun smith other_command` is safe, so for commands like `smith distclean` and `smith configure` that are quick to execute, you can:
```
smith distclean
smith configure
rrun smith build
```

Alternatively, multiple commands can be specified by escaping a `;` between them:
```
rrun smith distclean \; smith configure \; smith build ftml
```
## Advanced usage

Executing rrun without any command parameters will give the following usage message:

```
usage: rrun [ options ] cmd [args]

runs the command (with its args) by first rsyncing the current directory
to a ramdisk (/dev/shm), running the cmd, and then rsyncing everything back.

Any options supplied are passed on to both calls to rsync, and can be any of:

  -v          increase verbosity; also displays ramdisk location
  -c          skip based on checksum, not mod-time & size
  -n          perform a trial run with no changes made
  -C          auto-ignore files in the same way CVS does
  -f RULE     add a file-filtering RULE
  -F          same as: -f 'dir-merge /.rsync-filter'
              repeated: -f '- .rsync-filter'
  -i          output a change-summary for all updates

See rsync manpage for more information about these options.
```

`-f` is particularly helpful if there are subdirectories that need not be rsync'd back and forth. For example to exclude any folder named `backups` use:
```
rrun -f '- backups' smith build
```

To exclude multiple folders, supply multiple `-f` options or use a external merge file, e.g.:

```
rrun -f '. filter.rsync' smith buld
```
where the `filter.rsync` file might contain:
```
- .git
- backups
- instances
```

## Caveats

When using any of the shell control operators `(`, `)`, `;`, `|`, or `&` (or combinations of such) within the command string, they must be isolated from other parameters by whitespace. For example:
```
rrun smith clean \; smith build
```
The following will not work a expected:
```
rrun smith clean\; smith build
```

It is not advisable to make modifications to the shared folder, for example from your host, while `rrun` is executing since there is a risk that such changes may be lost when the rsync copies the results back.

By their nature, ramdrive contents do not survive a VM reboot. So if the VM is halted and restarted, the initial `rrun` will again need to copy everything.

## Authors
Martin Hosken, Tim Eves, Bob Hallissy
