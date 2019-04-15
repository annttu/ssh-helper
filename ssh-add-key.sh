#!/bin/bash

export SSH_AUTH_SOCK_BASE=~/.ssh/agents

function help() {
	echo "$0 <key>"
	exit 0
}

key=$1

test -z "$key" && help

keyname="$(basename $key)"
full_path="$(cd $(dirname $key) && pwd)/${keyname}"

if [ ! -f "$full_path" ]
then
	echo "Key $full_path does not exist"
	exit 1
fi

export SSH_AUTH_SOCK="${SSH_AUTH_SOCK_BASE}/${keyname}"

AGENT="${SSH_AUTH_SOCK_BASE}/ssh-agent-${keyname}"

test ! -f $AGENT && ln -s /usr/local/bin/ssh-agent $AGENT

ssh-add -l
if [ "$?" == 2 ]
then
	echo restarting agent
	$AGENT -a $SSH_AUTH_SOCK
fi

PASSITEM="$(security find-generic-password -a "$full_path")"

if [ ! -z "$PASSITEM" ]
then
    GETPASS="${SSH_AUTH_SOCK_BASE}/get_pass_keyname.sh"
    cat > "${GETPASS}"<<EOF
#!/bin/bash
security find-generic-password -a "$full_path" -w
EOF
    chmod 700 "${GETPASS}"
    export DISPLAY=:0.0
    export SSH_ASKPASS="${GETPASS}"
    ssh-add $full_path &
    wait
else
    ssh-add $full_path
fi

