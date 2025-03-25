"""Helper classes and functions for the parameter checker."""

import fnmatch
import re
from re import Pattern

from specklepy.objects import Base

from data_shield.actions import ParameterAction


class PatternChecker:
    """Checks if a parameter name matches a user-defined pattern."""

    def __init__(self, pattern: str, strict: bool = True):
        """Initializes the pattern checker.

        Args:
            pattern: User-defined pattern. Glob by default; /regex/ for regex; /regex/i for ignore-case.
            strict: Switches case-insensitive matching for both glob and regex (unless overridden by /i in regex).
        """
        self.is_regex = pattern.startswith("/") and (pattern.rstrip("i").endswith("/"))
        self.user_strict = strict

        if self.is_regex:
            # Check for inline ignore-case flag
            if pattern.endswith("/i"):
                self.ignore_case = True
                pattern_body = pattern[1:-2]
            else:
                self.ignore_case = not strict  # fallback to global strict setting if no /i flag
                pattern_body = pattern[1:-1]

            flags = re.IGNORECASE if self.ignore_case else 0
            self.regex = re.compile(pattern_body, flags)
            self.pattern = pattern_body
        else:
            self.regex = None
            self.pattern = pattern
            self.ignore_case = not strict

    def check(self, param_name: str) -> bool:
        """Checks if the parameter name matches the user-defined pattern."""
        if self.is_regex:
            return self.regex.search(param_name) is not None
        # For glob: emulate strict or non-strict
        if self.ignore_case:
            return fnmatch.fnmatch(param_name.lower(), self.pattern.lower())
        else:
            return fnmatch.fnmatchcase(param_name, self.pattern)


class EmailMatcher:
    """Class for identifying and anonymizing email addresses in parameter values."""

    # Email regex pattern - basic pattern to identify email addresses
    EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    def __init__(self):
        """Initialize with a compiled regex pattern for email matching."""
        self.pattern: Pattern = re.compile(self.EMAIL_PATTERN)

    def contains_email(self, value: str) -> bool:
        """Check if a string contains an email address.

        Args:
            value: The string to check for email addresses

        Returns:
            bool: True if the string contains an email address, False otherwise
        """
        if not isinstance(value, str):
            return False

        return bool(self.pattern.search(value))

    def anonymize_email(self, value: str) -> str:
        """Anonymize email addresses in a string.

        The function replaces the local part of each email address with the
        first character followed by asterisks, preserving the domain part.

        Example: "email@example.com" becomes "e****@example.com"

        Args:
            value: The string containing email addresses to anonymize

        Returns:
            str: The string with anonymized email addresses
        """
        if not isinstance(value, str):
            return value

        def replace_email(match_obj):
            """Replace function for regex sub to anonymize matched emails."""
            email = match_obj.group(0)

            # Split the email into local part and domain part
            local, domain = email.split("@", 1)

            # Anonymize the local part: keep first and last character, replace rest with asterisks
            if len(local) > 2:
                # For longer local parts, keep first and last characters
                anonymized_local = local[0] + "*" * (len(local) - 2) + local[-1]
            elif len(local) == 2:
                # For 2-character local parts, show first character and one asterisk
                anonymized_local = local[0] + "*"
            else:
                # For 1-character local parts, just use an asterisk
                anonymized_local = "*"

            # Return the anonymized email
            return f"{anonymized_local}@{domain}"

        # Replace all email addresses in the string
        return self.pattern.sub(replace_email, value)


# Modified ParameterProcessor class imported from processor_update.py
class ParameterProcessor:
    """Class to handle parameter processing with various actions."""

    def __init__(self, action: ParameterAction, check_values: bool = False):
        """Initialize the parameter processor with an action.

        Args:
            action: The parameter action to apply
            check_values: If True, check parameter values instead of names
        """
        self.action = action
        self.check_values = check_values
        self.processed_objects = set()

    def process_context(self, context):
        """Process a traversal context to handle parameters and properties.

        Args:
            context: The traversal context containing the current object
        """
        current_object = context.current

        # Prioritise v3
        if hasattr(current_object, "properties") and current_object.properties is not None:
            properties_dict = (
                current_object.properties.__dict__
                if isinstance(current_object.properties, Base)
                else current_object.properties
            )
            self.process_properties_dict(properties_dict, current_object)

        # Legacy placeholder for v2, ready for later
        if hasattr(current_object, "parameters") and current_object.parameters is not None:
            pass  # Add v2 handling when ready

    def process_properties_dict(self, properties_dict, current_object):
        """Recursively process v3-style properties dictionary to find and apply the action to parameters.

        Args:
            properties_dict: The properties dictionary to process
            current_object: The current object being processed
        """
        for key, value in list(properties_dict.items()):  # Safe iteration during mutation
            if isinstance(value, dict) and "value" in value:
                param_name = value.get("name", key)

                # Check based on mode (name or value)
                if self.check_values:
                    # For value-based actions (like anonymization)
                    if self.action.check(value.get("value", "")):
                        self.action.apply(value, current_object, properties_dict, key)
                        self.processed_objects.add(current_object.id)
                else:
                    # For name-based actions (like removal)
                    if self.action.check(param_name):
                        self.action.apply(value, current_object, properties_dict, key)
                        self.processed_objects.add(current_object.id)

            elif isinstance(value, dict):
                # Recurse into nested dictionaries
                self.process_properties_dict(value, current_object)

    def process_revit_parameters(self, current_object):
        """Process v2 Revit-style parameters to find and apply the action.

        Revit parameters are stored as Base objects with speckle_type 'Objects.BuiltElements.Revit.Parameter'
        and can be accessed via current_object.parameters.

        Args:
            current_object: The current object being processed
        """
        if not hasattr(current_object, "parameters") or current_object.parameters is None:
            return

        parameters = current_object.parameters

        # Use get_dynamic_member_names() to get all parameter keys
        for parameter_key in parameters.get_dynamic_member_names():
            # Get the parameter object using __getitem__
            try:
                param_obj = parameters.__getitem__(f"{parameter_key}")
            except KeyError:
                continue
            # Check if it's a Revit parameter
            if (
                not isinstance(param_obj, Base)
                or getattr(param_obj, "speckle_type", "") != "Objects.BuiltElements.Revit.Parameter"
            ):
                continue

            # For name-based checks, we need to check both the name property and applicationInternalName
            name_to_check = getattr(param_obj, "name", "")
            value_to_check = getattr(param_obj, "value", "")

            # Create a parameter dict to pass to the action
            param_dict = {
                "name": name_to_check,
                "value": value_to_check,
                "applicationInternalName": parameter_key,
            }

            # Check based on mode (name or value)
            if self.check_values:
                # For value-based actions (like anonymization)
                if isinstance(value_to_check, str) and self.action.check(value_to_check):
                    # Apply the action
                    self.action.apply(param_dict, current_object, parameters, parameter_key)
                    self.processed_objects.add(current_object.id)
            else:
                # For name-based actions (like removal)
                if self.action.check(name_to_check):
                    # Apply the action
                    self.action.apply(param_dict, current_object, parameters, parameter_key)
                    self.processed_objects.add(current_object.id)
