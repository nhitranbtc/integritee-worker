#!/usr/bin/env python3
import subprocess
import json
import os
import sys
import time
from datetime import datetime

# Define command templates
INTEGRITEE_CLI = "./target/release/integritee-cli"
ASSETHUB_CMD = f"{INTEGRITEE_CLI} -u ws://127.0.0.1 -p 9954"
MRENCLAVE = "EfeNBuBgHm872ANAbYn5kztDMfDAzthsE51WXw6UzHMH"
INCOGNITEE_CMD = f"{INTEGRITEE_CLI} -p 9954 -P 2000 -u ws://127.0.0.1 -U wss://127.0.0.1 trusted --mrenclave {MRENCLAVE}"

# Constants for waiting and tolerance
UNIT = 10 ** 12
FEE_TOLERANCE = 10 ** 11
WAIT_INTERVAL_SECONDS = 10
WAIT_ROUNDS = 20

def format_balance(balance, decimals=12):
    """Convert a raw balance to a human-readable format with specified decimals."""
    try:
        return f"{int(balance) / (10 ** decimals):,.2f}"
    except (ValueError, TypeError):
        return f"Invalid balance: {balance}"

def run_command(command):
    """Execute a shell command and return its output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.stderr:
            return f"Error: {result.stderr.strip()}"
        return result.stdout.strip() if result.stdout else "Command executed successfully"
    except Exception as e:
        return f"Error: {str(e)}"

def get_shard_vault():
    """Retrieve the shard vault value."""
    cmd = f"{INCOGNITEE_CMD} get-shard-vault"
    vault = run_command(cmd)
    if vault.startswith("Error"):
        return f"Failed to retrieve vault: {vault}"
    return vault

def wait_assert_balance(account, expected, label, is_incognitee=True):
    """Poll and assert the account balance matches the expected value within tolerance."""
    cmd = f"{INCOGNITEE_CMD if is_incognitee else ASSETHUB_CMD} balance {account}"
    for _ in range(WAIT_ROUNDS):
        time.sleep(WAIT_INTERVAL_SECONDS)
        raw_result = run_command(cmd)
        try:
            state = int(raw_result)
            if abs(state - expected) < FEE_TOLERANCE:
                print(f"* Wait and assert {label} balance... {format_balance(state)} tokens ✔ ok")
                return state
        except ValueError:
            print(f"Error querying balance for {label}: {raw_result}")
    print(f"Assert {label} balance failed, expected = {format_balance(expected)}, actual = {raw_result}, tolerance = {format_balance(FEE_TOLERANCE)}")
    sys.exit(1)

def query_initial_balances(balance_commands):
    """Query and return initial balances for all tracked accounts."""
    initial_balances = {}
    print("Querying initial balances...")
    balance_details = []
    for label, cmd in balance_commands.items():
        raw_result = run_command(cmd)
        formatted_result = format_balance(raw_result) + " tokens"
        initial_balances[label] = int(raw_result) if raw_result.isdigit() else 0
        balance_details.append({"account": label, "balance": formatted_result, "raw": raw_result})
        print(f"{label}: {formatted_result}")
    return initial_balances, balance_details

def generate_report(steps=None):
    # Read VAULT from incognitee get-shard-vault
    VAULT = get_shard_vault()
    if VAULT.startswith("Failed"):
        print(VAULT)
        return

    # Define the transfer commands as a list for ordered execution
    transfer_commands = [
        ("AssetHub Transfer (Alice to Laura)", f"{ASSETHUB_CMD} transfer //Alice //Laura 100000000000000"),
        ("AssetHub Transfer (Laura to Vault)", f"{ASSETHUB_CMD} transfer //Laura {VAULT} 50000000000000"),
        ("Incognitee Transfer (Laura to Julian)", f"{INCOGNITEE_CMD} transfer //Laura //Julian 10000000000000"),
        ("Incognitee Unshield (Julian to Edward)", f"{INCOGNITEE_CMD} unshield-funds //Julian //Edward 9000000000000"),
        ("AssetHub Transfer (Edward to Julian)", f"{ASSETHUB_CMD} transfer //Edward //Julian 9000000000000"),
    ]

    # Define the balance commands, including Vault
    balance_commands = {
        "AssetHub Balance (Alice)": f"{ASSETHUB_CMD} balance //Alice",
        "AssetHub Balance (Laura)": f"{ASSETHUB_CMD} balance //Laura",
        "Incognitee Balance (Laura)": f"{INCOGNITEE_CMD} balance //Laura",
        "AssetHub Balance (Julian)": f"{ASSETHUB_CMD} balance //Julian",
        "Incognitee Balance (Julian)": f"{INCOGNITEE_CMD} balance //Julian",
        "AssetHub Balance (Edward)": f"{ASSETHUB_CMD} balance //Edward",
        "Incognitee Balance (Edward)": f"{INCOGNITEE_CMD} balance //Edward",
        "AssetHub Balance (Vault)": f"{ASSETHUB_CMD} balance {VAULT}",
    }

    # Initialize results dictionary with clearer structure
    results = {
        "metadata": {
            "mrenclave": MRENCLAVE,
            "vault": VAULT,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "executed_steps": []
        },
        "initial_balances": [],
        "transfers": [],
        "final_balances": []
    }

    # Always query initial balances
    initial_balances, initial_balance_details = query_initial_balances(balance_commands)
    results["initial_balances"] = initial_balance_details
    results["metadata"]["executed_steps"].append("0")

    # Parse steps
    if steps:
        try:
            step_list = [int(s.strip()) for s in steps.split(",")]
            valid_range = range(0, len(transfer_commands) + 1)
            invalid_steps = [s for s in step_list if s not in valid_range]
            if invalid_steps:
                print(f"Error: Steps {invalid_steps} are out of range. Valid steps are 0 to {len(transfer_commands)}.")
                return

            transfer_steps = [s - 1 for s in step_list if s > 0]
            if transfer_steps:
                print("\nExecuting specified transfers...")
                for idx in transfer_steps:
                    label, cmd = transfer_commands[idx]
                    step_num = idx + 1
                    print(f"\nStep {step_num}: {label}")
                    print(f"Command: {cmd}")
                    result = run_command(cmd)
                    results["transfers"].append({
                        "step": step_num,
                        "description": label,
                        "command": cmd,
                        "result": result
                    })
                    results["metadata"]["executed_steps"].append(str(step_num))
                    print(f"Result: {result}")

                    # Assertions based on step
                    if step_num == 1:
                        wait_assert_balance("//Alice", initial_balances["AssetHub Balance (Alice)"] - 100 * UNIT, "AssetHub Alice", False)
                        wait_assert_balance("//Laura", initial_balances["AssetHub Balance (Laura)"] + 100 * UNIT, "AssetHub Laura", False)
                    elif step_num == 2:
                        wait_assert_balance("//Laura", initial_balances["AssetHub Balance (Laura)"] - 50 * UNIT, "AssetHub Laura", False)
                        wait_assert_balance(VAULT, initial_balances["AssetHub Balance (Vault)"] + 50 * UNIT, "AssetHub Vault", False)
                    elif step_num == 3:
                        wait_assert_balance("//Laura", initial_balances["Incognitee Balance (Laura)"] - 10 * UNIT, "Incognitee Laura")
                        wait_assert_balance("//Julian", initial_balances["Incognitee Balance (Julian)"] + 10 * UNIT, "Incognitee Julian")
                    elif step_num == 4:
                        wait_assert_balance("//Julian", initial_balances["Incognitee Balance (Julian)"] - 9 * UNIT, "Incognitee Julian")
                        wait_assert_balance("//Edward", initial_balances["AssetHub Balance (Edward)"] + 9 * UNIT, "AssetHub Edward", False)
                    elif step_num == 5:
                        wait_assert_balance("//Edward", initial_balances["AssetHub Balance (Edward)"] - 9 * UNIT, "AssetHub Edward", False)
                        wait_assert_balance("//Julian", initial_balances["AssetHub Balance (Julian)"] + 9 * UNIT, "AssetHub Julian", False)

                print("\nChecking balances after transfers...")
                for label, cmd in balance_commands.items():
                    raw_result = run_command(cmd)
                    formatted_result = format_balance(raw_result) + " tokens"
                    results["final_balances"].append({
                        "account": label,
                        "balance": formatted_result,
                        "raw": raw_result
                    })
                    print(f"{label}: {formatted_result}")
            else:
                print("\nNo transfers executed, only initial balances recorded.")

        except ValueError:
            print("Error: Please provide valid step numbers (e.g., '0', '1', '1,2,3').")
            return
    else:
        print("\nNo steps specified. Running all transfers...")
        for idx, (label, cmd) in enumerate(transfer_commands, 1):
            print(f"\nStep {idx}: {label}")
            print(f"Command: {cmd}")
            result = run_command(cmd)
            results["transfers"].append({
                "step": idx,
                "description": label,
                "command": cmd,
                "result": result
            })
            results["metadata"]["executed_steps"].append(str(idx))
            print(f"Result: {result}")

            # Assertions for all steps
            if idx == 1:
                wait_assert_balance("//Alice", initial_balances["AssetHub Balance (Alice)"] - 100 * UNIT, "AssetHub Alice", False)
                wait_assert_balance("//Laura", initial_balances["AssetHub Balance (Laura)"] + 100 * UNIT, "AssetHub Laura", False)
            elif idx == 2:
                wait_assert_balance("//Laura", initial_balances["AssetHub Balance (Laura)"] - 50 * UNIT, "AssetHub Laura", False)
                wait_assert_balance(VAULT, initial_balances["AssetHub Balance (Vault)"] + 50 * UNIT, "AssetHub Vault", False)
            elif idx == 3:
                wait_assert_balance("//Laura", initial_balances["Incognitee Balance (Laura)"] - 10 * UNIT, "Incognitee Laura")
                wait_assert_balance("//Julian", initial_balances["Incognitee Balance (Julian)"] + 10 * UNIT, "Incognitee Julian")
            elif idx == 4:
                # wait_assert_balance("//Julian", initial_balances["Incognitee Balance (Julian)"] - 9 * UNIT, "Incognitee Julian")
                # wait_assert_balance("//Edward", initial_balances["AssetHub Balance (Edward)"] + 9 * UNIT, "AssetHub Edward", False)
                pass
            elif idx == 5:
                # wait_assert_balance("//Edward", initial_balances["AssetHub Balance (Edward)"] - 9 * UNIT, "AssetHub Edward", False)
                # wait_assert_balance("//Julian", initial_balances["AssetHub Balance (Julian)"] + 9 * UNIT, "AssetHub Julian", False)
                pass

        print("\nChecking balances after transfers...")
        for label, cmd in balance_commands.items():
            raw_result = run_command(cmd)
            formatted_result = format_balance(raw_result) + " tokens"
            results["final_balances"].append({
                "account": label,
                "balance": formatted_result,
                "raw": raw_result
            })
            print(f"{label}: {formatted_result}")

    # JSON file handling
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file_path = os.path.join(script_dir, "demo-accounts.json")
    existing_data = {}
    if os.path.exists(json_file_path):
        with open(json_file_path, "r") as json_file:
            try:
                existing_data = json.load(json_file)
            except json.JSONDecodeError:
                print("Warning: Existing JSON file is corrupted. Starting fresh.")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    existing_data[timestamp] = results
    with open(json_file_path, "w") as json_file:
        json.dump(existing_data, json_file, indent=4)

    print(f"\nResults appended to {json_file_path} under timestamp {timestamp}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_report(sys.argv[1])
    else:
        generate_report()
