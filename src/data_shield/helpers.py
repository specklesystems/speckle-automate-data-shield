"""Helper classes and functions for the parameter checker."""
import fnmatch
import re
from re import Pattern


class PatternChecker:
    """Checks if a parameter name matches a user-defined pattern."""

    def __init__(self, pattern: str, strict: bool = True):
        """Initializes the pattern checker.

        Args:
            pattern: User-defined pattern. Glob by default; /regex/ for regex; /regex/i for ignore-case.
            strict: Switches case-insensitive matching for both glob and regex (unless overridden by /i in regex).
        """
        self.is_regex = pattern.startswith('/') and (pattern.rstrip('i').endswith('/'))
        self.user_strict = strict

        if self.is_regex:
            # Check for inline ignore-case flag
            if pattern.endswith('/i'):
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
    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

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
            local, domain = email.split('@', 1)

            # Anonymize the local part: keep first and last character, replace rest with asterisks
            if len(local) > 2:
                # For longer local parts, keep first and last characters
                anonymized_local = local[0] + '*' * (len(local) - 2) + local[-1]
            elif len(local) == 2:
                # For 2-character local parts, show first character and one asterisk
                anonymized_local = local[0] + '*'
            else:
                # For 1-character local parts, just use an asterisk
                anonymized_local = '*'

            # Return the anonymized email
            return f"{anonymized_local}@{domain}"

        # Replace all email addresses in the string
        return self.pattern.sub(replace_email, value)