#!/usr/bin/env python3

"""

Parse ssh command and set proper environment variables for ssh command

"""
import os
from shutil import which


# --- Configuration begins ---

SSH="/usr/local/bin/ssh"
SSH_AGENT="/usr/local/bin/ssh-agent"
SSH_ADD="/usr/local/bin/ssh-add"
SSH_ADD_KEY=which("ssh-add-key")
AGENTS_DIR=os.path.expanduser("~/.ssh/agents")

# --- Configuration ends ---


import sys
import os.path
import subprocess
import argparse
import time

config_cache = {}

hostname = None

def debug(msg):
    sys.stderr.write(msg)
    sys.stderr.write("\n")
    sys.stderr.flush()


def get_agent_socket(key):
    return os.path.join(AGENTS_DIR, key)

def start_agent(keyfile):
    key = os.path.basename(keyfile)
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
    time.sleep(1)
    p = subprocess.Popen([SSH_ADD_KEY, keyfile], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p.wait()
    if p.returncode != 0:
        debug("Failed to add key to agent")
        debug(p.stdout.read().decode("utf-8"))
        debug(p.stderr.read().decode("utf-8"))

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

def get_or_start_agent(keyfile):
    key = os.path.basename(keyfile)
    if not os.path.isdir(AGENTS_DIR):
        os.mkdir(AGENTS_DIR)
    agent_socket = get_agent_socket(key)

    if not os.path.exists(agent_socket):
        start_agent(keyfile)
    else:
        # Test agent is alive
        if not agent_alive(key):
            start_agent(keyfile)
    set_environment(key)

def get_config(hostname):
    if hostname not in config_cache:
        config_p = subprocess.Popen([SSH, '-G', hostname], stdout=subprocess.PIPE)
        (stdout, stderr) = config_p.communicate()
        retval = config_p.wait()
        if retval != 0:
            debug("Unexpected error occured with %s -G %s" % (SSH, hostname))
            return None
        lines = {}
        for line in stdout.decode("utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            k, v = line.split(None,1)
            lines[k] = v

        config_cache[hostname] = lines
    return config_cache[hostname]


def get_key_from_config(hostname):
    hostname = hostname.lower()
    found = False
    config = get_config(hostname)
    if not config:
        debug("Unexpected error occured with get_config")
        return None
    return config.get('identityfile', None)

def get_localcommand(hostname):
    if not hostname:
        return
    hostname = hostname.lower()
    found = False
    config = get_config(hostname)
    if not config:
        debug("Unexpected error occured with get_config")
        return None
    return config.get('localcommand', None)


def parse_commandline():
    parser = argparse.ArgumentParser()
    # Arguments with value
    for arg in 'bcDEeFiILlMmOopQRSWw':
        parser.add_argument('-%s' % arg)
    parser.add_argument('hostname')
    # Arguments without value
    for arg in '46':
        parser.add_argument("-%s" % arg, action="store_true")

    args = parser.parse_known_args()


    hostname = args[0].hostname
    print("\033k%s\033\\" % hostname)
    if '@' in hostname:
        hostname = hostname.split('@')[-1]
    args[0].hostname = hostname
    return args[0]


def get_key_from_commandline():
    global hostname
    parser = argparse.ArgumentParser()
    # Arguments with value
    for arg in 'bcDEeFiIJLlMmOopQRSWw':
        parser.add_argument('-%s' % arg)
    parser.add_argument('hostname')
    # Arguments without value
    for arg in '46':
        parser.add_argument("-%s" % arg, action="store_true")

    args = parser.parse_known_args()

    if args[0].i:
        return args[0].i

    hostname = args[0].hostname
    print("\033k%s\033\\" % hostname)
    if '@' in hostname:
        hostname = hostname.split('@')[-1]
    return get_key_from_config(hostname)

def get_key():
    keyfile = get_key_from_commandline()
    if keyfile:
        if not os.path.exists(os.path.expanduser(keyfile)):
            debug("Key %s does not exist" % keyfile)
            return
        keyfile = os.path.expanduser(keyfile)
        get_or_start_agent(keyfile)


if __name__ == '__main__':

    clear_environment()

    get_key()


    localcommand = get_localcommand(hostname)
    if localcommand:
        print("Calling local command")
        out = subprocess.check_output(localcommand, shell=True)

    hostname = parse_commandline().hostname
    args = ("ssh-%s" % hostname,) + tuple(sys.argv[1:])
    os.execv(SSH, args)


