# rrun — copy there and back again for smith

## Introduction

When using a virtual machine (VM) to run smith, it can be convenient to keep the project files in a shared folder so they can be accessed and modified from your host environment, and then use the VM to build the project.

However, keeping the project in shared folders costs in performance: on a Windows host, building the project directly in the shared folders is two to five times slower than if the project folder were in the VM's emulated drive (or, better yet, a ramdrive).

`rrun` provides a way to have both the convenience of shared folders and the performance of a ramdrive. `rrun` will efficiently copy (via `rsync`) the project files from the shared drive to a ramdrive within the VM, run smith (or any arbitrary command) on that copy, and then copy any new or changed files back (again, using `rsync`). Even with the overhead of the rsync commands, it often comes out ahead, especially with disk-intensive commands.

## Installation

Within the smith VM, download or copy `rrun` to some place on your PATH such as `~/bin`. If `~/bin` doesn't exist, create it, copy `rrun` to it, and then log out and back in for the PATH to be updated. Make sure `rrun` is executable if it isn't already (`chmod 755 rrun`) and has Linux (not Windows) line endings.

## Simple usage

```
cd myProjectRoot
smith distclean
smith configure
rrun smith build
```

The first time you use `rrun` will take longer because it has to sync the entire project to the emulated drive in the VM. Subsequent runs are faster because it has to sync only changes. Similarly, any time there are major changes to the project tree, e.g., after running `smith distclean`, the next `rrun` will take more time.

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

  -v          increase verbosity; first occurance just displays ramdisk location
  -c          skip based on checksum, not mod-time & size
  -n          perform a trial run with no changes made
  -C          auto-ignore files in the same way CVS does
  -f RULE     add a file-filtering RULE
  -F          same as: -f 'dir-merge /.rsync-filter'
              repeated: -f '- .rsync-filter' (CAUTION: not recommended with rrun)
  -i          output a change-summary for all updates

See rsync manpage for more information about these options.
```

### Where is the ramdrive?

Whenever you use `rrun`, the name of the ramdrive folder to be used is calculated from the name of the current working directory. This has two implications to remember:

- Every smith project will have its own separate ramdrive folder (this is a good thing).
- If you descend into a subfolder of your project and use `rrun` from there, you will be using a _different_ ramdrive folder than you would be from the root of your project (this might not be what you wanted).

Sometimes it is helpful to be able to inspect the relevant ramdrive folder. To find out where it is, include the `-v`. In fact you can use this option all by itself:

```
$ rrun -v
ramdisk location: /dev/shm/rrun/07fd622383d2f0c59829b2e3611adc38
```

### Omitting specific files and folders

If there are files or folders in the project tree that do not need to be copied, you can make `rrun` even more efficiently by using `-f` or `-F` commands to filter them out from the `rsync` commands.

For example to exclude any folder named `backups` use `-f` as follows:

```
rrun -f '- backups/' smith build
```

To exclude multiple files or folders, either supply multiple `-f` options or, to save typing, use a external merge file, for example:

```
rrun -f '. rsync-filter.txt' smith build
```

where the `rsync-filter.txt` file can contain multiple filter rules. For example, if it contained:

```
- backups/
- instances/
- .git/
```

then all folders named `backups`, `instances` or `.git` anywhere in the tree would be excluded.

Merge files are so handy that if you name your merge file `.rsync-filter` then there is a short cut for the corresponding `-f '. .rsync-filter'` option, just specify `-F`:

```
rrun -F smith build
```

`dot.rsync-filter` included in this repo is a sample filter file that is useful for smith projects. If you want to use it, copy it to the root of your project and rename it `.rsync-filter`. Then simply use the `-F` option

## Caveats and Cautions

### Shell control operators

When using any of the shell control operators `(`, `)`, `;`, `|`, or `&` (or combinations of such) within the command string, they must be escaped _and_ isolated from other parameters by whitespace. For example:

```
rrun smith clean \; smith build
```

The following will not work a expected:

```
rrun smith clean ; smith build   # unescaped semicolon ends the rrun command
rrun smith clean\; smith build   # must have spaces before and after escaped semicolon
```

### Changing project tree while `rrun` is running

It is not advisable to make modifications to the shared folder, for example from your host, while `rrun` is executing since there is a risk that such changes may be lost when the rsync copies the results back.

### rsync paramters and filter rules are used both ways

`rrun` does _two_ rsync commands:
- before executing the command, rsync _from_ current folder _to_ the ramdrive
- after executing the command, rsync _from_ ramdrive back _to_ the current folder

It is important to remember this when writing filter rules and using other advanced options. Also, if a filter mergefile is used, be sure it is included in the first rsync so it is available for the second one — and for this reason using `-F` twice is probably not a good idea.

### VM reboots

By their nature, ramdrive contents do not survive a VM reboot. So if the VM is halted and restarted, the initial `rrun` will again need to copy everything.

## Authors

Martin Hosken, Tim Eves, Bob Hallissy
