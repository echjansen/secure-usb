import subprocess
import logging
import os
import re
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.logging import RichHandler

class Shell:
    """
    A class to execute shell commands with rich console output and logging,
    """

    # Theme colors for 'rich' objects
    COLOR_THEME = {
        'info':     'yellow',
        'warning':  'bold yellow',
        'success':  'green',
        'error':    'red',
        'critical': 'bold reverse red',
        'debug':    'blue',
        'command':  'cyan',
        'stdout':   'white',
        'stderr':   'red',
    }

    class CustomFormatter(logging.Formatter):
        def __init__(self, theme):
            super().__init__()
            self.theme = theme
            self.COLORS = self.theme

        def format(self, record):
            log_color = self.COLORS.get(record.levelname.lower(), 'white')
            record.msg = f'[{log_color}]{record.msg}[/{log_color}]'
            return super().format(record)

    def __init__(self, console, log, debug=False, theme=None, log_file='install.log'):
        """
        Initializes the Shell.

        Args:
            console (Console): The rich console object.
            log (logging.Logger): The logging object.
            debug (bool, optional): Enables debug output. Defaults to False.
            theme (dict, optional): A dictionary defining the theme for rich console. Defaults to None.
            log_file (str, optional): Path to the log file. Defaults to 'install.log'.
        """
        self.debug = debug
        self.log_file = log_file
        self.theme = theme if theme else Shell.COLOR_THEME # Use Shell.COLOR_THEME as default
        self.console = console
        self.log = log

        # Configure the logger
        self.log.setLevel(logging.DEBUG if self.debug else logging.INFO)
        self.log.propagate = False

        # Check if the log already has a file handler and add if it doesn't
        has_file_handler = any(isinstance(handler, logging.FileHandler) for handler in self.log.handlers)
        if not has_file_handler:
            self.file_handler = logging.FileHandler(self.log_file, mode='a')
            self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            self.file_handler.setFormatter(self.formatter)
            self.log.addHandler(self.file_handler)

        # Rich Handler for Console Output (only for execute method feedback)
        self.console_handler = RichHandler(
            console=self.console, # Explicitly pass the console object
            rich_tracebacks=True,
            markup=True,
            show_time=False,
            show_level=False, # Don't show level again as it's in the console output
            show_path=False
        )
        self.console_formatter = Shell.CustomFormatter(self.theme)
        self.console_handler.setFormatter(self.console_formatter)
        self.console_handler.setLevel(logging.WARNING) # Only print warnings or higher to the console

        # Ensure the console handler is added only once
        has_console_handler = any(isinstance(handler, RichHandler) for handler in self.log.handlers)
        if not has_console_handler:
            self.log.addHandler(self.console_handler)

        self.log.info("Shell initialized.")

    def __substitute_globals(self, text):
        """
        Substitutes global $variables in a string.

        Args:
            text    : The string containing global variable placeholders (e.g., "My string is $VARIABLE").
            globals ; List of variables (or empty)

        Returns:
            The string with global variables replaced by their values, or the original string if no
            global variables are found or an error occurs. Returns empty string on KeyError to prevent information leakage.
        """

        def replace_match(match):
            variable_name = match.group(1)  # Extract the variable name
            try:
                # Attempt to retrieve the global variable value
                value = os.environ.get(variable_name)

                if value is None:
                    return "" # Return empty string in case of none - could also raise ValueError

                return str(value)  # Ensure the value is a string
            except KeyError:
                # Handle cases where the global variable doesn't exist - return empty to avoid accidental information disclosure
                return ""
            except Exception as e:
                # Handle other potential errors during substitution
                print(f"Error during substitution: {e}")
                return match.group(0)  # Return original placeholder to avoid crashing

        # Regex to find global variables in the format $VARIABLE, $VARIABLE_ONE, etc.
        # It looks for a dollar sign ($) followed by one or more alphanumeric characters and underscores.
        pattern = r"\$([a-zA-Z_][a-zA-Z0-9_]*)"

        # Use re.sub to replace the matched patterns with the corresponding global variable values
        substituted_string = re.sub(pattern, replace_match, text)

        return substituted_string


    def _substitute_globals(self, text):
        """
        Substitutes {variables} in a string, using curly braces.

        Args:
            input_string: The string containing global variable placeholders (e.g., "My string is {VARIABLE}").

        Returns:
            The string with global variables replaced by their values, or the original string if no
            global variables are found or an error occurs.  Returns an empty string on KeyError to prevent information leakage.
        """

        def replace_match(match):
            variable_name = match.group(1)  # Extract the variable name
            try:
                # Attempt to retrieve the global variable value
                value = os.environ.get(variable_name)  # Use environ, this is intended for global variables

                if value is None:
                    return ""  # Return empty string in case of None - could also raise ValueError

                return str(value)  # Ensure the value is a string
            except KeyError:
                # Handle cases where the global variable doesn't exist - return empty string to avoid information disclosure
                return ""  # Or, you could raise a ValueError or leave the variable in place, depends on the context
            except Exception as e:
                # Handle other potential errors during substitution
                print(f"Error during substitution: {e}")
                return match.group(0)  # Return original placeholder to avoid crashing

        # Regex to find global variables in the format {VARIABLE}, {VARIABLE_ONE}, etc.
        # It looks for an opening curly brace ({) followed by one or more alphanumeric characters and underscores,
        # and then a closing curly brace (}).
        pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"  # Updated regex

        # Use re.sub to replace the matched patterns with the corresponding global variable values
        substituted_string = re.sub(pattern, replace_match, text)

        return substituted_string

    def execute(self, description, command, input=None, output_var=None, check_returncode=True, strict=False):
        """
        Executes a shell command.

        Args:
            description (str): Description of the command.
            command (str): The shell command to execute.
            input (str, optional): Input for the command. Defaults to None.
            output_var (str, optional): Global variable to store the output. Defaults to None.
            check_returncode (bool, optional): If True, raises an exception on non-zero return code. Defaults to True.
            strict (bool, optional): when strict is True the shell command is strict with "set -euo pipefail' (bool - optional - default False)

        Returns:
            bool: True if the command was successful, False otherwise.
        """
        description = self._substitute_globals(description)
        command = self._substitute_globals(command)
        if input: input = self._substitute_globals(input)

        try:
            # Print description to console using rich directly
            self.console.print(f"[{self.theme['warning']}][ ] {description}[/{self.theme['warning']}]", end='\r')

            if self.debug:
                self.console.print(Panel(f"[{self.theme['command']}]{command}[/{self.theme['command']}]", title="Command"))

            shell_command = command
            if strict:
                shell_command = 'set -euo pipefail;' + command

            process = subprocess.Popen(
                shell_command,
                shell=True,
                stdin=subprocess.PIPE if input else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                executable='/bin/bash'
            )

            stdout, stderr = process.communicate(input=input.encode() if input else None)
            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()

            returncode = process.returncode

            if self.debug:
                output_panel = Panel(
                    Text.assemble(
                        ("STDOUT:\n", "bold"),
                        (stdout_str, self.theme['stdout']),
                        ("\n\nSTDERR:\n", "bold"),
                        (stderr_str, self.theme['stderr']),
                        style=Style(color="white")
                    ),
                    title="Output"
                )
                # Only print output when present
                if stdout_str != "" or stderr_str != "":
                    self.console.print(output_panel)

            if check_returncode and returncode != 0:
                self.console.print(f"[{self.theme['error']}][✗] {description}[/{self.theme['error']}]")
                self.log.error(f"Command failed: {command}")
                self.log.error(f"Return code: {returncode}")
                self.log.error(f"Stdout: {stdout_str}")
                self.log.error(f"Stderr: {stderr_str}")
                return False # Indicate failure
            else:
                if check_returncode:
                    self.console.print(f"[{self.theme['success']}][✓] {description}[/{self.theme['success']}]")
                else:
                    self.console.print(f"[{self.theme['success']}][✓] {description} (return code ignored)[/{self.theme['success']}]")

            # Store output in global variable if specified
            if output_var:
                os.environ[output_var] = stdout_str
                self.log.debug(f"Stored output in global variable '{output_var}'")

            self.log.info(f"Command executed successfully: {command}")
            return True  # Indicate success

        except Exception:
            self.console.print(f"[{self.theme['error']}][✗] {description}[/{self.theme['error']}]")
            self.log.exception(f"Exception while executing command: {command}")
            if self.debug:
                self.console.print_exception(show_locals=True)
            return False  # Indicate failure

    def execute_all(self, commands):
        """
        Executes a list of shell commands.

        Args:
            commands (list): A list of dictionaries, where each dictionary contains the arguments for the 'execute' method.

        Returns:
            bool: True if all commands were successful, False otherwise.
        """
        all_successful = True
        for command_data in commands:
            if not self.execute(**command_data):
                all_successful = False
        return all_successful
