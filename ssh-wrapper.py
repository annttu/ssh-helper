#!/usr/bin/env python3

"""

Parse ssh command and set proper environment variables for ssh command

"""
import os

# --- Configuration begins ---

SSH="/usr/local/bin/ssh"
SSH_AGENT="/usr/local/bin/ssh-agent"
SSH_ADD="/usr/local/bin/ssh-add"
AGENTS_DIR=os.path.expanduser("~/.ssh/agents")

# --- Configuration ends ---


import sys
import os.path
import subprocess
import argparse

def debug(msg):
    sys.stderr.write(msg)
    sys.stderr.write("\n")
    sys.stderr.flush()


def get_agent_socket(key):
    return os.path.join(AGENTS_DIR, key)

def start_agent(key):
    # Copy agent binary to alter binary name in keychain.
    agent_socket = get_agent_socket(key)
    if os.path.exists(agent_socket):
        os.remove(agent_socket)
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
        debug("Failed to initialize agent!")
        sys.exit(1)

def agent_alive(key):
    agent_socket = get_agent_socket(key)
    env = os.environ.copy()
    env['SSH_AUTH_SOCK'] = agent_socket
    p = subprocess.Popen([SSH_ADD, '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    p.wait()
    if p.returncode == 2:
        debug("Agent is dead!")
        return False
    elif p.returncode == 1:
        # No keys, but alive
        return True
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

def get_key_from_config(hostname):
    hostname = hostname.lower()
    found = False
    config_p = subprocess.Popen([SSH, '-G', hostname], stdout=subprocess.PIPE)
    (stdout, stderr) = config_p.communicate()
    retval = config_p.wait()
    if retval != 0:
        debug("Unexpected error occured with %s -G %s" % (SSH, hostname))
        return None
    for line in stdout.decode("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("identityfile "):
            return line.split()[1]

def get_key_from_commandline():
    parser = argparse.ArgumentParser()
    # Arguments with value
    for arg in 'bcDEeFiILlMmOopQRSWw':
        parser.add_argument('-%s' % arg)
    parser.add_argument('hostname')

    args = parser.parse_known_args()

    if args[0].i:
        return args[0].i

    hostname = args[0].hostname
    if '@' in hostname:
        hostname = hostname.split('@')[-1]
    return get_key_from_config(hostname)


def get_key():
    keyfile = get_key_from_commandline()
    if keyfile:
        if not os.path.exists(keyfile):
            debug("Key %s does not exist" % keyfile)
            return
        get_or_start_agent(keyfile)


if __name__ == '__main__':

    clear_environment()

    get_key()



    args = ("ssh",) + tuple(sys.argv[1:])
    os.execv(SSH, args)


