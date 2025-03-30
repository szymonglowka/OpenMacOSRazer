#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hid  # pip install hidapi
import sys
import platform
import time # Added for potential sleep, although currently commented out
from typing import List, Tuple, Dict, Any, Optional, Union

# --- Configuration ---
RAZER_VID: int = 0x1532

# --- Device PIDs Extracted from Driver Headers ---
# Source: Derived from Razer driver headers (e.g., razerkbd_driver.h, razermouse_driver.h)
# Filtered to include only devices parameterized in this script's command logic.
RAZER_DEVICES: Dict[int, str] = {
    # Mice (Parameterized)
    0x00B9: "Razer Basilisk V3 X HyperSpeed",

    # Keyboards (Parameterized)
    0x025A: "Razer BlackWidow V3 Pro Wired",
    0x025C: "Razer BlackWidow V3 Pro Wireless",    # Dongle 2.4GHz
}

# --- Razer Report Constants ---
REPORT_LEN: int = 90
VARSTORE: int = 0x01  # Variable Storage identifier in command arguments

# -- Constants for Basilisk V3 X HyperSpeed (Mouse) --
MOUSE_TARGET_PID: int = 0x00B9
MOUSE_SCROLL_WHEEL_LED: int = 0x01
MOUSE_CMD_CLASS: int = 0x0F
MOUSE_CMD_ID: int = 0x02
MOUSE_EFFECT_STATIC: int = 0x01
MOUSE_TRANSACTION_ID: int = 0x1F
MOUSE_DATA_SIZE: int = 9

# -- Constants for BlackWidow V3 Pro (Keyboard) --
BW3PRO_WIRELESS_PID: int = 0x025C # Dongle 2.4GHz
BW3PRO_WIRED_PID: int = 0x025A    # Wired
KBD_BACKLIGHT_LED: int = 0x05
KBD_CMD_CLASS: int = 0x0F
KBD_CMD_ID: int = 0x02
KBD_EFFECT_STATIC: int = 0x01
KBD_WIRELESS_TRANSACTION_ID: int = 0x9F # For 0x025C
KBD_WIRED_TRANSACTION_ID: int = 0x3F    # For 0x025A
KBD_DATA_SIZE: int = 9

# -----------------------------------------------------------------------------
# --- Helper Functions ---
# -----------------------------------------------------------------------------

def calculate_crc(report_data: bytes) -> int:
    """Calculates the CRC checksum (XOR sum) for the Razer report."""
    crc = 0
    # CRC is calculated over bytes 2 to 87 (inclusive)
    for i in range(2, 88):
        if i < len(report_data):
            crc ^= report_data[i]
    return crc

def construct_razer_report(transaction_id: int, command_class: int, command_id: int,
                           data_size: int, arguments: List[int]) -> bytes:
    """Constructs the 90-byte Razer HID feature report."""
    if len(arguments) > 80:
        raise ValueError("Argument list is too long (max 80 bytes)")

    report = bytearray(REPORT_LEN)
    report[0] = 0x00  # Report ID (will be stripped by send_feature_report sometimes, but structure expects it)
    report[1] = transaction_id & 0xFF
    report[2] = 0x00 # Status / Remaining packets (high byte)
    report[3] = 0x00 # Remaining packets (low byte)
    report[4] = 0x00 # Protocol type
    report[5] = data_size & 0xFF
    report[6] = command_class & 0xFF
    report[7] = command_id & 0xFF

    # Copy arguments into the report buffer (bytes 8 to 87)
    arg_len = min(len(arguments), 80)
    report[8 : 8 + arg_len] = bytes(arguments)

    # Calculate and set CRC (byte 88)
    crc_val = calculate_crc(report)
    report[88] = crc_val

    report[89] = 0x00 # Reserved

    return bytes(report)

def get_color_from_user() -> Tuple[int, int, int]:
    """Prompts the user for RGB values (0-255) and returns them."""
    while True:
        try:
            r_str = input("Enter value for Red (R, 0-255): ")
            r = int(r_str)
            g_str = input("Enter value for Green (G, 0-255): ")
            g = int(g_str)
            b_str = input("Enter value for Blue (B, 0-255): ")
            b = int(b_str)

            if 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255:
                return (r, g, b)
            else:
                print("ERROR: Values must be between 0 and 255.", file=sys.stderr)
        except ValueError:
            print("ERROR: Please enter valid integers.", file=sys.stderr)
        except EOFError:
            print("\nOperation cancelled by user.", file=sys.stderr)
            sys.exit(0)

# -----------------------------------------------------------------------------
# --- Main Script Logic ---
# -----------------------------------------------------------------------------

def main():
    """Main function to find parameterized Razer devices and send color commands."""
    if platform.system() != "Darwin":
        print("Warning: This script is primarily tested on macOS.", file=sys.stderr)
        print("It might work on Linux, but may require root/sudo permissions.", file=sys.stderr)

    print("-" * 60)
    print(" Razer Device Control Script (Python + hidapi)")
    print(" (Attempts to set mouse scroll wheel OR keyboard backlight color for specific devices)")
    print("-" * 60)

    found_devices_grouped: Dict[Tuple[Optional[str], Optional[str], int], Dict[str, Any]] = {}

    try:
        print("Scanning for Razer devices...")
        # Enumerate all Razer devices first
        all_enumerated_devices = hid.enumerate(RAZER_VID, 0x0)
        if not all_enumerated_devices:
            print("ERROR: No Razer devices found.", file=sys.stderr)
            sys.exit(1)

        # Filter for parameterized devices
        parameterized_pids = set(RAZER_DEVICES.keys())
        enumerated_devices = [dev for dev in all_enumerated_devices if dev['product_id'] in parameterized_pids]

        if not enumerated_devices:
            print(f"Found {len(all_enumerated_devices)} Razer HID interface(s), but none match the parameterized PIDs:")
            for pid in parameterized_pids:
                print(f"  - 0x{pid:04X}: {RAZER_DEVICES.get(pid, 'Unknown Name')}")
            print("Exiting.", file=sys.stderr)
            sys.exit(1)

        print(f"Found {len(enumerated_devices)} HID interface(s) belonging to parameterized Razer devices.")

        # Group interfaces by physical device (using serial, product string, and PID as key)
        for dev_info in enumerated_devices:
            pid = dev_info['product_id']
            # Get name from our filtered list
            device_name = RAZER_DEVICES.get(pid, f"Unknown Parameterized Razer Device (PID: 0x{pid:04X})")
            interface_num = dev_info.get('interface_number', -1) # Not always available or reliable
            path = dev_info['path'] # Path is the most reliable way to open
            serial = dev_info.get('serial_number', 'N/A')
            prod_string = dev_info.get('product_string', 'N/A')

            # Use a tuple of potentially identifying info as the key
            device_key = (serial, prod_string, pid)

            if device_key not in found_devices_grouped:
                found_devices_grouped[device_key] = {
                    'name': device_name,
                    'pid': pid,
                    'serial': serial,
                    'product_string': prod_string,
                    'interfaces': []
                }
            found_devices_grouped[device_key]['interfaces'].append({
                'path': path,
                'interface_number': interface_num
            })

    except hid.HIDException as e:
        print(f"ERROR: HID enumeration failed: {e}", file=sys.stderr)
        print("Check if hidapi is installed correctly and you have permissions.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error during enumeration: {e}", file=sys.stderr)
        sys.exit(1)

    if not found_devices_grouped:
        # This case should be caught earlier by the parameterized check, but as a safeguard
        print("No identifiable parameterized Razer devices found after grouping.", file=sys.stderr)
        sys.exit(1)

    # Convert dict to list for indexed selection
    device_list = list(found_devices_grouped.values())

    print("\nFound Parameterized Razer Devices:")
    for i, dev_data in enumerate(device_list):
        name_display = dev_data['name'] # Name already includes '(Bluetooth?)' if applicable from dict
        interface_count = len(dev_data['interfaces'])
        print(f"{i+1}: {name_display} (PID: 0x{dev_data['pid']:04X}) - {interface_count} HID interface(s)")

    # --- User Device Selection ---
    selected_device_data = None
    while selected_device_data is None:
        try:
            choice_str = input(f"Select device number to control (1-{len(device_list)}): ")
            choice_idx = int(choice_str) - 1
            if 0 <= choice_idx < len(device_list):
                selected_device_data = device_list[choice_idx]
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")
        except EOFError:
            print("\nOperation cancelled by user.", file=sys.stderr)
            sys.exit(0)

    selected_pid = selected_device_data['pid']
    print(f"\nSelected: {selected_device_data['name']} (PID: 0x{selected_pid:04X})")

    # --- Get Target Color ---
    target_color_rgb = get_color_from_user()
    print(f"Selected RGB Color: {target_color_rgb}")

    # --- Prepare Device-Specific Command ---
    report_to_send: Optional[bytes] = None
    command_desc: str = "Unknown command"
    arguments: List[int] = []

    # Common arguments for static color effect
    static_effect_args_base = [
        VARSTORE,
        0x00, # Placeholder for LED ID
        KBD_EFFECT_STATIC, # Assuming static effect command is often the same
        0x00, 0x00, 0x01, # Parameters for static effect (likely count/index)
    ]
    static_effect_args_color = list(target_color_rgb) # R, G, B

    if selected_pid == MOUSE_TARGET_PID:
        command_desc = f"Set mouse scroll wheel (LED ID {MOUSE_SCROLL_WHEEL_LED}) to RGB {target_color_rgb}"
        print(f"\nConstructing report for {selected_device_data['name']}: {command_desc}...")
        arguments = static_effect_args_base[:1] + [MOUSE_SCROLL_WHEEL_LED] + static_effect_args_base[2:] + static_effect_args_color
        report_to_send = construct_razer_report(
            MOUSE_TRANSACTION_ID, MOUSE_CMD_CLASS, MOUSE_CMD_ID, MOUSE_DATA_SIZE, arguments
        )

    elif selected_pid == BW3PRO_WIRED_PID:
        command_desc = f"Set keyboard backlight (LED ID {KBD_BACKLIGHT_LED}) to RGB {target_color_rgb}"
        print(f"\nConstructing report for {selected_device_data['name']} (Wired): {command_desc}...")
        arguments = static_effect_args_base[:1] + [KBD_BACKLIGHT_LED] + static_effect_args_base[2:] + static_effect_args_color
        report_to_send = construct_razer_report(
            KBD_WIRED_TRANSACTION_ID, KBD_CMD_CLASS, KBD_CMD_ID, KBD_DATA_SIZE, arguments
        )

    elif selected_pid == BW3PRO_WIRELESS_PID:
        command_desc = f"Set keyboard backlight (LED ID {KBD_BACKLIGHT_LED}) to RGB {target_color_rgb}"
        print(f"\nConstructing report for {selected_device_data['name']} (Wireless Dongle): {command_desc}...")
        arguments = static_effect_args_base[:1] + [KBD_BACKLIGHT_LED] + static_effect_args_base[2:] + static_effect_args_color
        report_to_send = construct_razer_report(
            KBD_WIRELESS_TRANSACTION_ID, KBD_CMD_CLASS, KBD_CMD_ID, KBD_DATA_SIZE, arguments
        )

    # --- Send Command ---
    if report_to_send:
        try:
            print(f"Constructed Report ({len(report_to_send)} bytes): {report_to_send.hex()}")
            # Prepend Report ID 0x00 for send_feature_report
            # Note: hidapi might handle this automatically depending on platform/backend,
            # but explicitly adding it is often required or safer.
            report_with_id = b'\x00' + report_to_send
            success_on_any_interface = False

            print("\nAttempting to send command to device interfaces...")
            for interface_info in selected_device_data['interfaces']:
                hid_device: Optional[hid.device] = None
                interface_path: Union[str, bytes] = interface_info['path']
                interface_num_str = f"Interface Num: {interface_info['interface_number']}" if interface_info['interface_number'] != -1 else "Interface Num: N/A"
                # Decode path if it's bytes for printing
                path_str = interface_path.decode('utf-8', errors='replace') if isinstance(interface_path, bytes) else interface_path

                print(f"\n--- Trying Interface: {path_str} ({interface_num_str}) ---")

                try:
                    print("  Opening interface...")
                    hid_device = hid.device()
                    hid_device.open_path(interface_path)
                    print("  Interface opened.")

                    # Some devices might need a slight pause after opening
                    # time.sleep(0.05)

                    print(f"  Sending Feature Report ({len(report_with_id)} bytes with ID 0x00): {report_with_id.hex()}")
                    bytes_written = hid_device.send_feature_report(report_with_id)

                    if bytes_written == len(report_with_id):
                        # Technically, send_feature_report often returns byte count *including* the report ID.
                        # Success means it didn't return -1 and potentially wrote the expected number.
                        print(f"  SUCCESS: Sent {bytes_written} bytes to this interface.")
                        print(f"  Effect '{command_desc}' should be visible if this is the correct control interface.")
                        success_on_any_interface = True
                        # Optionally break here if success on one interface is enough
                        # break
                    elif bytes_written == -1:
                        error_msg = hid_device.error() or "Unknown HIDAPI Error"
                        print(f"  ERROR: send_feature_report failed (returned -1).", file=sys.stderr)
                        print(f"  HIDAPI Error Message: {error_msg}", file=sys.stderr)
                        print(f"  Possible reasons: Insufficient permissions (try sudo/root), incorrect interface, command/report not supported on this interface, device busy.", file=sys.stderr)
                    else:
                        # This case is less common with send_feature_report but possible
                        print(f"  WARNING: Sent {bytes_written} bytes, but expected {len(report_with_id)}. Partial write or unexpected return value.", file=sys.stderr)

                except OSError as e: # Catch permission errors etc.
                    print(f"  OS ERROR (permissions?): {e}", file=sys.stderr) # Indicate OS-level error
                    print(f"  Failed to open or send to interface: {path_str}", file=sys.stderr)
                    print(f"  This interface might require root/sudo or be reserved by the OS.", file=sys.stderr) # Refined message
                except Exception as e:
                    # Catch other unexpected errors during interface handling
                    print(f"  UNEXPECTED ERROR for interface {path_str}: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                finally:
                    if hid_device:
                        print("  Closing HID interface...")
                        hid_device.close()

            print("-" * 60)
            if success_on_any_interface:
                print("Command successfully sent to at least one interface.")
                print("If the effect isn't visible, the command might need different parameters,")
                print("or the wrong interface might have received the command (control might be on another).")
            else:
                print("Failed to send the command successfully to any interface.", file=sys.stderr)
        except ValueError as e:
             # From construct_razer_report if args are too long
            print(f"\nData Error: {e}", file=sys.stderr)
        except Exception as e:
            # Catch other unexpected errors during report preparation/sending
            print(f"\nUnexpected Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    else:
        # This path should not be reached if device filtering worked correctly
        # and one of the parameterized devices was selected.
        print("\nError: No report was constructed to send. This indicates an internal logic issue.", file=sys.stderr)


    print("\nScript finished.")

# --- Entry Point ---
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.", file=sys.stderr)
        sys.exit(1)
