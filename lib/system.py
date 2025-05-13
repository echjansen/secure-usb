import os
import re
import shutil
import subprocess
from typing import List, Union

class System:
    """
    A class to encapsulate helper functions for Arch Linux installation.
    This class has no specific dependencies.
    """

    def __init__(self, debug=False):
        """
        Initializes the ArchInstallHelper class.

        Args:
            debug (bool, optional): Enables debug output to console (print). Defaults to False.
        """
        self.debug = debug

    def check_sudo(self):
        """
        Check that the software is running with sudo privileges.
        """

        if os.getegid() == 0:
            if self.debug: print("Script is running with sudo privileges.")
            return True
        else:
            if self.debug: print("Application must run with sudo privileges.")
            exit()

    def check_uefi(self):
        """
        Check that the system is running in UEFI mode (Unified Extensible Firmware Interface).
        """

        if os.path.exists('/sys/firmware/efi/'):
            if self.debug: print("System is booted in UEFI mode.")
            return True
        else:
            if self.debug: print("System is NOT booted in UEFI mode (likely BIOS/Legacy mode).")
            return False

    def check_secure_boot(self):
        """
        Check that the system is running with Secure Boot
        """

        try:
            # Execute dmesg | grep -1 tpm
            result = subprocess.run(
                ['dmesg'],
                capture_output=True,
                text=True,
                check=True          # Check for non-zero exit code
            )
            dmesg_output = result.stdout.strip()

            grep_result = subprocess.run(
                ['grep', '-i', 'tpm'],
                input=dmesg_output,
                capture_output=True,
                text=True,
                check=False          # Do Not check for non-zero exit code
            )
            grep_output = grep_result.stdout.strip()

            if grep_output:
                if self.debug: print('TPM (Trusted Platform Module) detected.')
                return True
            else:
                if self.debug: print('TPM (Trusted Platform Module) not detected.')
                return False

        except subprocess.CalledProcessError as e:
            if self.debug: print(f'Error executing dmesg: {e}')
            exit()
        except Exception as e:
            if self.debug: print(f'An unexpected error occurred: {e}')
            exit()

    def check_pacman(self, packages):
        """
        Checks (and updates) the Pacman package manager and installs a list of core applications.

        Args:
            packages: A list of strings, where each string is the name of a package
                     to install (e.g., ["reflector", "python-rich"]).  Assumes Arch Linux.
        Returns:
            True if the installation was successful, False otherwise.  Prints
            detailed error messages to stderr if an error occurs.
        """

        if not isinstance(packages, list):
            if self.debug: print("Error: 'packages' argument must be a list.")
            return False

        if not all(isinstance(p, str) for p in packages):
            if self.debug: print("Error: All elements in 'packages' must be strings.")
            return False

        try:
            # Update the package manager database
            if self.debug: print("Updating Pacman database...")
            subprocess.run(["sudo", "pacman", "-Sy"], capture_output=True, text=True, check=True)

            # Install the specified packages
            if self.debug: print("Installing core requirements...")
            subprocess.run(["sudo", "pacman", "-S", "--noconfirm"] + packages, capture_output=True, text=True, check=True)

            return True

        except subprocess.CalledProcessError as e:
            if self.debug: print(f"Error executing command: {e.cmd}")
            exit()
        except Exception as e:
            if self.debug: print(f"An unexpected error occurred: {e}")
            exit()

    def get_cpu_brand(self) -> str:
        """
        Uses the 'lscpu' command to determine the CPU brand (Intel, AMD, etc.).

        Returns:
            str: The CPU brand name.
                 Returns "Unknown" if the brand cannot be determined or an error occurs.
        """
        try:
            # Execute lscpu
            result = subprocess.run(
                ['lscpu'],
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout.strip()

            # Search for the "CPU vendor" line
            vendor_id = None
            model_name = None
            for line in output.splitlines():
                if "Vendor ID:" in line:
                    vendor_id = line.split(":", 1)[1].strip()
                if "Model name:" in line:
                    model_name = line.split(":", 1)[1].strip()

            if vendor_id:
                if vendor_id == "GenuineIntel":
                    return "Intel"
                elif vendor_id == "AuthenticAMD":
                    return "AMD"
                else:
                    if model_name:
                       return model_name # Returning the "Model name"
                    else:
                       return vendor_id  # Return the raw "CPU vendor" string if known brands aren't matched.
            else:
                if self.debug: print("Could not determine CPU brand from lscpu output.")
                return "Unknown"

        except subprocess.CalledProcessError as e:
            if self.debug: print(f"Error executing lscpu: {e}")
            return "Unknown"
        except FileNotFoundError:
            if self.debug: print("Error: lscpu command not found. Please ensure lscpu is installed.")
            return "Unknown"
        except Exception as e:
            if self.debug: print(f"An unexpected error occurred: {e}")
            return "Unknown"

    def get_graphics_card_brand(self) -> str:
        """
        Uses the 'lspci' command to determine the graphics card brand (Intel, NVIDIA, AMD, etc.).

        Returns:
            str: The graphics card brand name.
                 Returns "Unknown" if the brand cannot be determined or an error occurs.
        """

        try:
            # Execute lspci to get VGA compatible controller information
            result = subprocess.run(
                ['lspci', '-vnn', '-d', '::0300'],  # Filter for VGA compatible controllers
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout.strip()

            # Parse the output to find the graphics card brand
            for line in output.splitlines():
                if "VGA compatible controller" in line:
                    # Extract the brand name from the line
                    brand = line.split("VGA compatible controller")[1].strip()

                    # Normalize the brand (remove extra info, use common names)
                    if "Intel" in brand:
                        return "Intel"
                    elif "NVIDIA" in brand:
                        return "NVIDIA"
                    elif "AMD" in brand or "ATI" in brand:
                        return "AMD"  # Using AMD as the standard name
                    elif "VMware" in brand :
                        return "VMWare"  # VMWare Virtualisation
                    elif "Oracle" in brand :
                        return "VirtualBox"  # VirtualBox Virtualisation
                    else:
                        return brand  # Return the raw brand if known brands aren't matched.

            if self.debug: print("Could not determine graphics card brand from lspci output.")
            return "Unknown"

        except subprocess.CalledProcessError as e:
            if self.debug: print(f"Error executing lspci: {e}")
            return "Unknown"
        except FileNotFoundError:
            if self.debug: print("Error: lspci command not found. Please ensure lspci is installed.")
            return "Unknown"
        except Exception as e:
            if self.debug: print(f"An unexpected error occurred: {e}")
            return "Unknown"

    def get_virtualizer(self) -> str:
        """
        Uses the 'systemd-detect-virt' command to determine the current virtualizer.

        Returns:
            str: The name of the virtualizer (e.g., "vmware", "kvm", "docker", "lxc").
                 Returns "none" if running on bare metal or the virtualizer cannot be determined.
                 Returns "Unknown" if an error occurs.
        """

        try:
            # Execute systemd-detect-virt
            result = subprocess.run(
                ['systemd-detect-virt'],
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout.strip()

            if output:
                return output
            else:
                return "none"  # Running on bare metal

        except subprocess.CalledProcessError as e:
            if self.debug: print(f"Error executing systemd-detect-virt: {e}")
            return "Unknown"
        except FileNotFoundError:
            if self.debug: print("Error: systemd-detect-virt command not found. Please ensure systemd is installed.")
            return "Unknown"
        except Exception as e:
            if self.debug: print(f"An unexpected error occurred: {e}")
            return "Unknown"

    def get_packages_from_file(self, filepath: str) -> List[str]:
        """
        Reads a file containing a list of package names (one per line),
        removes comments, and returns a list of clean package names.

        Comments start with '#' and can be the entire line or behind the package name.

        To use with for instance pacstrap use ' '.join(packages)

        Args:
            filepath: The path to the file containing the package list.

        Returns:
            A list of package names (without comments).
        """
        packages: List[str] = []

        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()  # Remove leading/trailing whitespace

                    # Skip empty lines and comment-only lines
                    if not line or line.startswith('#'):
                        continue

                    # Remove comments at the end of the line
                    if '#' in line:
                        line = line.split('#', 1)[0].strip() # Splitting from the left side only once

                    # Add the package name to the list
                    if line:  # Ensure there's something left after removing comments
                        packages.append(line)

        except FileNotFoundError:
            if self.debug: print(f"Error: File not found: {filepath}")
        except Exception as e:
            if self.debug: print(f"An error occurred: {e}")

        return packages

    def get_partition(self, device: str, partition_no: int):
        """
        Determines the first partition of a given device using the 'ls' command.

        Args:
            device (str): The device name (e.g., '/dev/sda' or '/dev/nvme0n1').
            partition_no (int): The partiton number (e.g., '1' format '/dev/nvme0n1p1').

        Returns:
            str: The name of the partition (e.g., '/dev/sda1' or '/dev/nvme0n1p1'),
                 or None if no partition is found.
            None: If the device doesn't exist or if an error occurs while listing partitions.
        """

        def _get_partitions(device, pattern):
            """Helper function to run ls with a specific pattern."""
            command = f"ls {device}{pattern} 2>/dev/null"
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                return stdout.strip().split('\n')
            else:
                return []

        try:
            # Try the NVMe-style pattern first
            partitions = _get_partitions(device, "p*[0-9]")  # Matches nvme0n1p1, nvme0n1p2, etc.

            # If NVMe-style partitions weren't found, try the sdX-style pattern
            if not partitions:
                partitions = _get_partitions(device, "[0-9]")  # Matches sda1, sda2, etc.

            if partitions:
                partitions.sort()
                first_partition = partitions[partition_no -1]

                # Updated regex to match both /dev/sda1 and /dev/nvme0n1p1 formats
                if re.match(rf"^{device}(p?[0-9]+|[0-9]+)$", first_partition):
                    return first_partition
                else:
                    return None
            else:
                return None

        except FileNotFoundError:
            if self.debug: print("Error: 'ls' command not found.  Please ensure it is in your PATH.")
            return None
        except Exception as e:
            if self.debug: print(f"An error occurred: {e}")
            return None

    def find_subdirectory(self, source_name: str) -> Union[str, None]:
        """
        Finds the source directory by name within the current directory structure
        using the 'find' command.

        Args:
            source_name: The name of the source directory to find.

        Returns:
            The absolute path to the source directory if found, otherwise None.
        """

        try:
            # Execute the 'find' command
            result = subprocess.run(
                ['find', '.', '-name', source_name, '-type', 'd', '-print0'],  # Find directories only, print null-terminated
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout.strip()

            if output:
                # Split the output by null characters (handles filenames with spaces or newlines)
                paths = output.split('\0')
                # Return the first matching directory (assuming there's only one)
                return os.path.abspath(paths[0])

            else:
                if self.debug: print(f"Error: Source directory '{source_name}' not found using 'find' command.")
                return None

        except subprocess.CalledProcessError as e:
            if self.debug: print(f"Error executing find command: {e}")
            return None
        except FileNotFoundError:
            if self.debug: print("Error: find command not found. Please ensure find is installed.")
            return None
        except Exception as e:
            if self.debug: print(f"An unexpected error occurred: {e}")
            return None

    def copy_file_structure(self, source: str, destination: str) -> None:
        """
        Copies the file structure (folders and files) from a source directory to a
        destination directory, creating any missing folders in the destination.

        Args:
            source: The path to the source directory.
            destination: The path to the destination directory.
        """
        #log.info(f'Copying file from {source} to {destination}')

        try:
            # Check if the source directory exists
            if not os.path.isdir(source):
                source = self.find_subdirectory(source)
                if not source:
                    if self.debug: print(f"Error: Source directory '{source}' not found.")
                    return

            # Create the destination directory if it doesn't exist
            os.makedirs(destination, exist_ok=True)  # exist_ok=True prevents an error if the directory already exists

            for root, _, files in os.walk(source):
                # Create the corresponding directory structure in the destination
                dest_dir = os.path.join(destination, os.path.relpath(root, source))
                os.makedirs(dest_dir, exist_ok=True)

                for file in files:
                    source_file = os.path.join(root, file)
                    dest_file = os.path.join(dest_dir, file)
                    try:
                        shutil.copy2(source_file, dest_file)  # copy2 preserves metadata
                    except Exception as e:
                        if self.debug: print(f"Warning: Could not copy '{source_file}' to '{dest_file}': {e}")

        except Exception as e:
            if self.debug: print(f"An unexpected error occurred: {e}")
            return None
