"""Helper classes and functions for the parameter checker."""
import fnmatch
import re


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