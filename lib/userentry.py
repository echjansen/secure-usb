import os
import sys
import subprocess

class UserEntry:
    """A class for gathering user information via dialog prompts."""

    def __init__(self):
        """Initializes the UserEntry class."""
        self.user_data = {}  # To store user entries

    # --- Support Functions ---

    def _run_dialog(self, *args):
        """Run dialog with fixed dimensions and force compatibility with terminal emulators."""
        cmd = ['dialog',  '--clear', '--stdout'] + list(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            os.system('clear')  # Helps clean up after dialog in terminal emulator
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Dialog command failed with return code {e.returncode}: {e.stderr}")
            return None  # Treat non-zero return as cancel
        except FileNotFoundError:
            print("Error: 'dialog' program not found.  Please install it.")
            sys.exit(1)
        except Exception as e:
            print(f"Error running dialog: {e}")
            return None

    def _run_inputbox(self, title, text, init="", height=0, width=0):
        """Runs an inputbox dialog prompt using the 'dialog' program."""
        cmd = ["--title", title, "--inputbox", text, str(height), str(width), init]
        result = self._run_dialog(*cmd)
        return result

    def _run_passwordbox(self, title, text, height=0, width=0):
        """Runs a passwordbox dialog prompt using the 'dialog' program."""
        cmd = ["--title", title, "--passwordbox", text, str(height), str(width)]
        result = self._run_dialog(*cmd)
        return result

    def run_yesno(self, title, text, height=0, width=0):
        """Runs a yes/no dialog prompt using the 'dialog' program.

        Returns:
            True if 'Yes' is selected.
            False if 'No' or Cancel is selected, or if an error occurs.
        """
        cmd = ['dialog', '--title', title, '--yesno', text, str(height), str(width)]
        try:
            # Clear the screen using escape codes
            print("\033[2J\033[H", end="")  # Clear screen and move cursor to top-left
            result = subprocess.run(cmd, capture_output=False, text=True, check=False)
            return result.returncode == 0
        except FileNotFoundError:
            print("Error: 'dialog' program not found.  Please install it.")
            sys.exit(1)
        except Exception as e:
            print(f"Error running dialog: {e}")
            return False
    def run_yesno_str(self, title, text, height=0, width=0):
        """Runs a yes/no dialog prompt using the 'dialog' program.

        Returns:
            True if 'Yes' is selected.
            False if 'No' or Cancel is selected, or if an error occurs.
        """
        cmd = ['dialog', '--title', title, '--yesno', text, str(height), str(width)]
        try:
            # Clear the screen using escape codes
            print("\033[2J\033[H", end="")  # Clear screen and move cursor to top-left
            result = subprocess.run(cmd, capture_output=False, text=True, check=False)
            if result.check_returncode == 0:
                return 'yes'
            else:

                return 'no'

        except FileNotFoundError:
            print("Error: 'dialog' program not found.  Please install it.")
            sys.exit(1)
        except Exception as e:
            print(f"Error running dialog: {e}")
            return False

    def _run_msgbox(self, title, text, height=0, width=0):
        """Runs a message box dialog prompt using the 'dialog' program."""
        cmd = ["--title", title, "--msgbox", text, str(height), str(width)]
        self._run_dialog(*cmd)  # No return value needed for msgbox

    # --- System Functions ---

    def _get_drive_info(self, drive):
        """Gets drive size and model information using `lsblk` and `hdparm`."""
        size = "Unknown"
        model = "Unknown"

        try:
            # Get size using lsblk
            result = subprocess.run(['lsblk', '-dn', '-b', '-o', 'SIZE', f'/dev/{drive}'], capture_output=True, text=True, check=True)
            size_bytes = int(result.stdout.strip())
            size_gb = size_bytes / (1024 ** 3)  # Convert to GB
            size = f"{size_gb:.2f} GB"
        except subprocess.CalledProcessError as e:
            print(f"Error getting size for {drive}: {e.stderr}")
        except Exception as e:
            print(f"Error getting size for {drive}: {e}")

        try:
            # Get model using hdparm
            result = subprocess.run(['hdparm', '-I', f'/dev/{drive}'], capture_output=True, text=True, check=True)
            for line in result.stdout.splitlines():
                if "Model Number:" in line:
                    model = line.split(":", 1)[1].strip()
                    break
        except subprocess.CalledProcessError as e:
            print(f"Error getting model for {drive}: {e.stderr}")
        except FileNotFoundError:
            print("Error: hdparm not found. Please install it.")
        except Exception as e:
            print(f"Error getting model for {drive}: {e}")

        return size, model

    def _get_drives(self):
        """Lists available drives and their info."""
        try:
            result = subprocess.run(['lsblk', '-dn', '-o', 'NAME'], capture_output=True, text=True, check=True)
            drives = [line.strip() for line in result.stdout.splitlines() if "loop" not in line]
            drive_info = []
            for drive in drives:
                size, model = self._get_drive_info(drive)
                drive_info.append((drive, size, model))
            return drive_info
        except subprocess.CalledProcessError as e:
            print(f"Error listing drives: {e.stderr}")
            return []
        except FileNotFoundError:
            print("Error: 'lsblk' command not found.")
            return []
        except Exception as e:
            print(f"An error occurred listing drives: {e}")
            return []

    def _get_timezones(self):
        """Lists timezones from /usr/share/zoneinfo using glob."""
        timezone_dir = "/usr/share/zoneinfo"
        timezones = []
        for root, _, files in os.walk(timezone_dir):
            for file in files:
                full_path = os.path.join(root, file)
                if os.path.isfile(full_path):  # Only add files, skip directories that may not be valid timezones
                    relative_path = os.path.relpath(full_path, timezone_dir)
                    timezones.append(relative_path)  # Relative to /usr/share/zoneinfo
        return timezones

    def _get_locales(self):
        """Reads available locales from /usr/share/i18n/SUPPORTED."""
        try:
            with open("/usr/share/i18n/SUPPORTED", "r") as f:
                locales = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                return locales
        except FileNotFoundError:
            print("Error: /usr/share/i18n/SUPPORTED not found.")
            return []
        except Exception as e:
            print(f"Error reading locales: {e}")
            return []

    def _get_keyboard_layouts(self, keymap_dir="/usr/share/kbd/keymaps"):
        """Lists available keyboard layouts from the specified directory."""
        layouts = []
        try:
            for root, _, files in os.walk(keymap_dir):
                for file in files:
                    if file.endswith(".map.gz") or file.endswith(".map"):
                        # Remove the .map.gz or .map extension to get the layout name
                        layout_name = file[:-7] if file.endswith(".map.gz") else file[:-4]
                        layouts.append(layout_name)
        except Exception as e:
            print(f"Error reading keyboard layouts: {e}")
            return []
        return sorted(layouts)  # Sort the layouts alphabetically

    def _get_reflector_countries(self):
        """Gets the list of countries from `reflector --list-countries`."""
        try:
            result = subprocess.run(['reflector', '--list-countries'], capture_output=True, text=True, check=True)
            countries = [line.strip() for line in result.stdout.splitlines()]
            return countries
        except FileNotFoundError:
            print("Error: reflector not found. Please install it.")
            return []
        except subprocess.CalledProcessError as e:
            print(f"Error listing countries: {e.stderr}")
            return []
        except Exception as e:
            print(f"An error occurred listing countries: {e}")
            return []

    def _set_console_font(self, font):
        """Sets the console font using `setfont`."""
        try:
            subprocess.run(['setfont', font], check=True)
            print(f"Console font set to: {font}")
        except FileNotFoundError:
            print("Error: setfont not found. Please install it.")
        except subprocess.CalledProcessError as e:
            print(f"Error setting font: {e.stderr}")

    # --- User Selection Functions ---

    def configure_hostname(self, default=""):
        """Prompts the user for a hostname."""
        result = self._run_inputbox("Hostname Configuration", "Enter the desired hostname:", default, height=8, width=40)
        if result:
            self.user_data["hostname"] = result
        return result

    def configure_username(self):
        """Prompts the user for a User name."""
        result = self._run_inputbox("User Configuration", "Enter the username:", height=8, width=40)
        if result:
            self.user_data["username"] = result
        return result

    def configure_userpassword(self):
        """Prompts the user for a User password (with confirmation)."""
        while True:
            password = self._run_passwordbox("User Configuration", "Enter the user password:", height=8, width=40)
            if not password:
                return None

            password_confirm = self._run_passwordbox("User Configuration", "Confirm the user password:", height=8, width=40)
            if not password_confirm:
                return None

            if password == password_confirm:
                self.user_data["userpassword"] = password
                return password
            else:
                print("Passwords do not match. Please try again.")

    def configure_lukspassword(self):
        """Prompts the user for a Luks password (with confirmation)."""
        while True:
            password = self._run_passwordbox("Luks Configuration", "Enter the Luks password:", height=8, width=40)
            if not password:
                return None

            password_confirm = self._run_passwordbox("Luks Configuration", "Confirm the Luks password:", height=8, width=40)
            if not password_confirm:
                return None

            if password == password_confirm:
                self.user_data["lukspassword"] = password
                return password
            else:
                print("Passwords do not match. Please try again.")


    def configure_drive(self):
        """Presents a menu to select a drive for installation."""
        drives = self._get_drives()
        if not drives:
            print("No drives found. Please ensure you have a drive connected.")
            return None

        drive_items = []
        for drive, size, model in drives:
            label = f"{drive} - {model} ({size})"
            drive_items.append((drive, label))

        menu_items = []
        for drive, label in drive_items:
            menu_items.extend([drive, label])

        selected_drive = self._run_dialog("--menu", "Select the drive for installation:", "20", "70", "10", *menu_items)

        if selected_drive:
            selected_drive = "/dev/" + selected_drive
            self.user_data["drive"] = selected_drive
        return selected_drive

    def configure_locale(self, default=""):
        """Prompts the user for a locale and filters the results."""
        locales = self._get_locales()
        if not locales:
            print("No locales found.")
            return None

        while True:
            filter_string = self._run_inputbox("Locale Selection", "Enter a filter string (e.g., 'en_US') or leave blank for all:", default, height=8, width=70)
            if filter_string is None:
                return None

            filtered_locales = [locale for locale in locales if filter_string.lower() in locale.lower()]

            if not filtered_locales:
                print("No locales match the filter. Try again.")
            else:
                locale_items = [(locale, locale) for locale in filtered_locales]
                menu_items = []
                for locale, label in locale_items:
                    menu_items.extend([locale, label])

                selected_locale = self._run_dialog("--menu", "Select the desired locale:", "15", "60", "10", *menu_items)
                if selected_locale:
                    self.user_data["locale"] = selected_locale
                    return selected_locale
                else:
                    return None  # User canceled the locale selection

    def configure_timezone(self):
        """Prompts the user for a timezone and filters the results."""
        timezones = self._get_timezones()
        if not timezones:
            print("No timezones found.")
            return None

        while True:
            filter_string = self._run_inputbox("Timezone Selection", "Enter a filter string (e.g., 'America') or leave blank for all:", height=8, width=60)
            if filter_string is None:
                return None

            filtered_timezones = [tz for tz in timezones if filter_string.lower() in tz.lower()]

            if not filtered_timezones:
                print("No timezones match the filter. Try again.")
            else:
                timezone_items = [(tz, tz) for tz in filtered_timezones]

                menu_items = []
                for tz, label in timezone_items:
                    menu_items.extend([tz, label])

                selected_timezone = self._run_dialog("--menu", "Select the desired timezone:", "15", "60", "10", *menu_items)
                if selected_timezone:
                    self.user_data["timezone"] = selected_timezone
                    return selected_timezone
                else:
                    return None  # User canceled the timezone selection

    def configure_keyboard(self):
        """Presents a menu to select a keyboard layout."""
        keyboard_layouts = self._get_keyboard_layouts()
        if not keyboard_layouts:
            print("No keyboard layouts found.")
            return None

        layout_items = [(layout, layout) for layout in keyboard_layouts]

        menu_items = []
        for layout, label in layout_items:
            menu_items.extend([layout, label])

        selected_keyboard = self._run_dialog("--menu", "Select the desired keyboard layout (us):", "20", "60", "10", *menu_items)  # Adjusted sizes
        if selected_keyboard:
            self.user_data["keyboard"] = selected_keyboard
        return selected_keyboard

    def configure_country_reflector(self):
        """Presents a menu to select a country from the reflector country list."""
        countries = self._get_reflector_countries()
        if not countries:
            print("No countries found.")
            return None

        country_items = [(country, country) for country in countries]

        menu_items = []
        for country, label in country_items:
            menu_items.extend([country, label])

        selected_country = self._run_dialog("--menu", "Select a country:", "20", "60", "10", *menu_items)
        if selected_country:
            self.user_data["country"] = selected_country
        return selected_country

    def configure_country(self):
        """Presents a menu to select a country from a static list."""
        countries = [  # A reasonably comprehensive list
            "United States", "Canada", "United Kingdom", "Germany", "France", "Japan", "China", "India",
            "Australia", "Brazil", "Mexico", "Italy", "Spain", "Netherlands", "Switzerland", "Sweden",
            "Belgium", "Austria", "Norway", "Denmark", "Finland", "Ireland", "Portugal", "Greece",
            "Poland", "Russia", "South Africa", "Argentina", "Chile", "Colombia", "Peru", "Venezuela",
            "Singapore", "Hong Kong", "South Korea", "Taiwan", "Thailand", "Vietnam", "Indonesia",
            "Malaysia", "Philippines", "New Zealand"
        ]

        sorted_countries = sorted(countries)

        country_items = [(country, country) for country in sorted_countries]

        menu_items = []
        for country, label in country_items:
            menu_items.extend([country, label])

        selected_country = self._run_dialog("--menu", "Select a country:", "20", "60", "10", *menu_items)
        if selected_country:
            self.user_data["country"] = selected_country
        return selected_country

    def configure_font(self):
        """Presents a menu to select a console font and applies it immediately."""
        font_options = [
            ("ter-116n", "Small"),
            ("ter-124n", "Medium"),
            ("ter-128n", "Large"),
            ("ter-132n", "Extra Large")  # Common Terminus fonts
        ]

        while True:  # Loop until the user is satisfied and presses OK
            menu_items = []
            for font, label in font_options:
                menu_items.extend([font, label, "off"]) # sets initial state to off

            # The following code is modified to use --radiolist rather than --menu
            # --radiolist <height> <width> <listheight> <tag1> <item1> <status1> ...
            cmd = ["--title", "Console Font Selection", "--radiolist", "Select a console font:", "20", "60", "10"] + menu_items
            selected_font = self._run_dialog(*cmd)

            if selected_font:
                self._set_console_font(selected_font)  # Apply the selected font immediately
                self.user_data["font"] = selected_font
                break  # Exit the loop if a font is selected
            else:
                # The user canceled the font selection.
                return None

        return selected_font

    def configure(self):
        """Main function to orchestrate the Arch Linux configuration process."""
        print("Starting Arch Linux Configuration...")

        # First, configure the font size
        font = self.configure_font()
        if font:
            self._set_console_font(font)
        else:
            print("Font configuration canceled or failed. Using default font.")

        drive = self.configure_drive()
        if not drive:
            print("Drive selection canceled.")
            return None

        lukspassword = self.configure_lukspassword()
        if not lukspassword:
            print("Password configuration canceled.")
            return None

        hostname = self.configure_hostname("archlinux")
        if not hostname:
            print("Hostname configuration canceled.")
            return None

        username = self.configure_username()
        if not username:
            print("User configuration canceled.")
            return None

        userpassword = self.configure_userpassword()
        if not userpassword:
            print("Password configuration canceled.")
            return None

        locale = self.configure_locale("en_US")
        if not locale:
            print("Locale selection canceled.")
            return None

        timezone = self.configure_timezone()
        if not timezone:
            print("Timezone configuration canceled.")
            return None

        keyboard = self.configure_keyboard()
        if not keyboard:
            print("Keyboard layout selection canceled.")
            return None

        country = self.configure_country()
        if not country:
            print("Country selection canceled.")
            return None

        # --- Configuration Summary ---
        summary_text = f"""
        Hostname: ......... {hostname}
        Username: ......... {username}
        Drive: ............ {drive}
        Locale: ........... {locale}
        Timezone: ......... {timezone}
        Keyboard Layout: .. {keyboard}
        Country: .......... {country}
        """

        self._run_msgbox("Configuration Summary", summary_text, 20, 60)

        confirmation_text = f"""
        WARNING! You are about to delete all data on drive {drive}!!!

        Do you want to continue with the installation?
        """
        confirm = self.run_yesno("Confirmation", confirmation_text)
        if not confirm:
            print("Installation canceled.")
            return None

        return self.user_data
