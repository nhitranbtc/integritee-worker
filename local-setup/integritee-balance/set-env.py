#!/usr/bin/env python3

import subprocess
import os
import sys

def get_mrenclave():
    """Get MRENCLAVE value by running integritee-cli command"""
    try:
        # Execute the command and capture output
        cmd = "./target/release/integritee-cli -p 9954 -P 2000 -u ws://127.0.0.1 -U ws://localhost:2000 list-workers"
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()

        # Check if command was successful
        if process.returncode != 0:
            print(f"Error getting MRENCLAVE: {stderr}")
            return None

        # Parse MRENCLAVE from output (equivalent to awk command)
        for line in stdout.split('\n'):
            if "MRENCLAVE:" in line:
                mrenclave = line.split("MRENCLAVE:")[1].strip().split()[0]
                return mrenclave

        print("MRENCLAVE not found in output")
        return None

    except Exception as e:
        print(f"Error executing command: {e}")
        return None

def set_aliases(mrenclave):
    """Set the aliases as environment variables"""
    aliases = {
        "integritee": "./target/release/integritee-cli -p 9954 -P 2000 -u ws://127.0.0.1 -U ws://127.0.0.1",
        "assethub": "./target/release/integritee-cli -u ws://127.0.0.1 -p 9954",
        "incognitee": f"./target/release/integritee-cli -p 9954 -P 2000 -u ws://127.0.0.1 -U wss://127.0.0.1 trusted --mrenclave {mrenclave}"
    }

    # Set environment variables
    for name, value in aliases.items():
        os.environ[name] = value

    return aliases

def main():
    # Get MRENCLAVE
    mrenclave = get_mrenclave()
    if mrenclave:
        print(f"MRENCLAVE set to: {mrenclave}")
    else:
        print("Failed to get MRENCLAVE, using empty string as fallback")
        mrenclave = ""

    # Set aliases
    aliases = set_aliases(mrenclave)

    # Print confirmation
    print("\nAliases have been set:")
    for name, value in aliases.items():
        print(f"{name}: {value}")

if __name__ == "__main__":
    main()