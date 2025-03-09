#!/bin/bash

# Path to the JSON config file
CONFIG_FILE="env-config.json"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required to parse JSON. Please install it."
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file '$CONFIG_FILE' not found."
    exit 1
fi

# Read hosts from JSON file into an array (compatible with older Bash)
HOSTS=()
while IFS= read -r host; do
    HOSTS+=("$host")
done < <(jq -r '.hosts[]' "$CONFIG_FILE")

# Check if HOSTS array is populated
if [ ${#HOSTS[@]} -eq 0 ]; then
    echo "Error: No hosts found in '$CONFIG_FILE'."
    exit 1
fi

# Array of ports (unchanged from your original)
PORTS=(
    9999 9988 9977 9944 9945 9954 9955 9998 30390
    2000 9954 3490 2001 4545 3000 9954 4490 3001 4546
)
PORTS=($(printf "%s\n" "${PORTS[@]}" | sort -nu))

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Starting port connectivity test..."
echo "Testing ports: ${PORTS[*]}"
echo "Hosts (from $CONFIG_FILE): ${HOSTS[*]}"
echo "--------------------------------"

# Function to test connection
test_connection() {
    local host=$1
    local port=$2
    if timeout 2 bash -c "exec 3>/dev/tcp/$host/$port" 2>/dev/null; then
        echo -e "${GREEN}SUCCESS${NC}: $host:$port is open"
        exec 3>&-
    else
        if timeout 2 bash -c "exec 3>/dev/tcp/$host/$port 2>&1" | grep -qi "Connection refused"; then
            echo -e "${RED}ERROR${NC}: $host:$port - Connection refused"
        else
            echo -e "${YELLOW}FAILED${NC}: $host:$port - Closed or unreachable"
        fi
    fi
}

# Test each port on each host
for host in "${HOSTS[@]}"; do
    echo -e "\nTesting host: $host"
    echo "----------------"
    for port in "${PORTS[@]}"; do
        test_connection "$host" "$port"
        sleep 0.5
    done
done

echo -e "\nTest completed!"
