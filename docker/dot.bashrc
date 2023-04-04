# skel bashrc to make the smith prompt more useful 

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# automatically correct small filename typos...
shopt -s cdspell

# append to the history file, don't overwrite it
shopt -s histappend

# case insensitive globbing (i.e. ls *.pdf) 
shopt -s nocaseglob   
shopt -s extglob
shopt -s no_empty_cmd_completion 

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac


force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
    if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
        # We have color support; assume it's compliant with Ecma-48
        # (ISO/IEC-6429). (Lack of such support is extremely rare, and such
        # a case would tend to support setf rather than setaf.)
        color_prompt=yes
    else
        color_prompt=
    fi
fi

if [ "$color_prompt" = yes ]; then
    PS1=' 🐳  ${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\H\[\033[00m\]:\[\033[01;34m\]\ w\ [\033[00m\]\$ '
else
    PS1=' 🐳  ${debian_chroot:+($debian_chroot)}\u@\H: \w \$ '
fi
unset color_prompt force_color_prompt

# If this is an xterm set the title to user@host:dir
case "$TERM" in
xterm*|rxvt*)
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\H: \w\a\]$PS1"
    ;;
*)
    ;;
esac

PROMPT_COMMAND='echo -ne "\033]0; $(basename $PWD) \007"; history -a;'


# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    #alias dir='dir --color=auto'
    #alias vdir='vdir --color=auto'

    alias grep='grep --color=auto'
    alias fgrep='fgrep --color=auto'
    alias egrep='egrep --color=auto'
fi




# colored GCC warnings and errors
export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# Aliases

alias ls='ls --color=auto'

alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias l="lt"
alias lx='ls -XBh'
alias lt='ls -XBth'
alias ll="ls -lBkh"
alias lsd="ls -d */"
alias lg='ls -1'


# list only hidden files
alias l.='ls -d .[[:alnum:]]* 2> /dev/null || echo "No hidden files here..."'

# list only backup files
alias lb='ls -d [[:alnum:]]*~ 2> /dev/null || echo "No backup files here..."'


alias rm='rm -i'			# file removal verbosity 
alias cp='cp -i'			# file copy verbosity
alias mv='mv -iv'			# file moving verbosity
alias s='cd ..'				# move one directory up
alias p='cd -'				# move to the previous directory
alias chmod='chmod -c'			# show only effective changes


# functions

# "Find File": Quick and easy file name search: recursive and case-insensitive
 ff() { find . -iname '*'$1'*' | grep -v .git ; }

# "Find Text": Find a string of text (each match will show "filename":"line number" ; binaries are also looked up)
 ft()  { egrep -insr "$1" * | grep -v .git ;   } 


# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

export STARSHIP_CONFIG='/etc/starship.toml'
eval "$(starship init bash)"


