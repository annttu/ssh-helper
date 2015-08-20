#!/usr/bin/env python3

"""

Parse ssh command and set proper environment variables for ssh command

"""

import sys
import os
import subprocess
import argparse


SSH="/usr/local/bin/ssh"
SSH_AGENT="/usr/local/bin/ssh-agent"
SSH_ADD="/usr/local/bin/ssh-add"
AGENTS_DIR=os.path.expanduser("~/.ssh/agents")

def get_agent_socket(key):
    return os.path.join(AGENTS_DIR, key)

def start_agent(key):
    # Copy agent binary to alter binary name in keychain.
    agent_socket = get_agent_socket(key)
    agent = os.path.join(AGENTS_DIR, "ssh-agent-%s" % key)
    infile = open(SSH_AGENT, 'rb')
    outfile = open(agent, 'wb')
    outfile.write(infile.read())
    infile.close()
    outfile.close()
    os.chmod(agent, 0o0700)
    p = subprocess.Popen([agent, '-a', agent_socket])
    p.wait()
    if p.returncode != 0:
        print("Failed to initialize agent!")
        sys.exit(1)

def agent_alive(key):
    agent_socket = get_agent_socket(key)
    env = os.environ.copy()
    env['SSH_AUTH_SOCK'] = agent_socket
    p = subprocess.Popen([SSH_ADD, '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    p.wait()
    if p.returncode != 0:
        print("Agent is dead!")
        return False
    return True

def clear_environment():
    if "SSH_AUTH_SOCK" in os.environ:
        del os.environ["SSH_AUTH_SOCK"]

def set_environment(key):
    agent_socket = get_agent_socket(key)
    os.environ["SSH_AUTH_SOCK"] = agent_socket

def get_or_start_agent(key):
    key = os.path.basename(key)
    if not os.path.isdir(AGENTS_DIR):
        os.mkdir(AGENTS_DIR)
    agent_socket = get_agent_socket(key)

    if not os.path.exists(agent_socket):
        start_agent(key)
    else:
        # Test agent is alive
        if not agent_alive(key):
            start_agent(key)
    set_environment(key)

def get_key_from_config(filehandle, hostname):
    hostname = hostname.lower()
    found = False
    for line in filehandle.readlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("host "):
            if hostname in line[5:].lower().split():
                found = True
                continue
            else:
                found = False
                continue
        if not found:
            continue
        if line.lower().startswith("identityfile "):
            return line.split()[1]

def get_key_from_commandline():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i')
    parser.add_argument('-o')
    parser.add_argument('hostname')

    args = parser.parse_known_args()

    if args[0].i:
        return args[0].i

    config_file = os.path.expanduser("~/.ssh/config")

    if not os.path.isfile(config_file):
        return

    f = open(config_file, 'r')
    hostname = args[0].hostname
    if '@' in hostname:
        hostname = hostname.split('@')[-1]
    return get_key_from_config(f, hostname)


def get_key():
    keyfile = get_key_from_commandline()
    if keyfile:
        get_or_start_agent(keyfile)


if __name__ == '__main__':

    clear_environment()

    get_key()



    args = ("ssh",) + tuple(sys.argv[1:])
    os.execv(SSH, args)


