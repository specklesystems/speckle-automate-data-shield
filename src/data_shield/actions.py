"""Module for parameter actions and matching strategies."""
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any

from speckle_automate import AutomationContext
from specklepy.objects import Base

from data_shield.helpers import PatternChecker


class ParameterMatcher(ABC):
    """Strategy interface for parameter matching logic."""

    def __init__(self, match_value: str, strict_mode: bool = False):
        """Initialize with a value to match against and a strict mode flag."""
        self.match_value = match_value
        self.strict_mode = strict_mode

    @abstractmethod
    def matches(self, param_name: str) -> bool:
        """Check if parameter name matches according to this strategy."""
        pass


class PrefixMatcher(ParameterMatcher):
    """Matches parameters by prefix."""

    def matches(self, param_name: str) -> bool:
        """Check if the parameter name starts with the match value."""
        if self.strict_mode:
            return param_name.startswith(self.match_value)
        return param_name.lower().startswith(self.match_value.lower())


class PatternMatcher(ParameterMatcher):
    """Matches parameters by regex pattern."""

    def matches(self, param_name: str) -> bool:
        """Check if the parameter name matches the regex pattern."""
        pattern = PatternChecker(self.match_value, self.strict_mode)
        return pattern.check(param_name)


class ParameterAction(ABC):
    """Base class for actions on parameters."""

    def __init__(self) -> None:
        """A dictionary to keep track of parameters affected by the action."""
        self.affected_parameters: dict[str, list[str]] = defaultdict(list)

    @abstractmethod
    def check(self, param_name: str) -> bool:
        """Check if the parameter meets the criteria for this action."""
        pass

    @abstractmethod
    def apply(self, parameter: dict[str, Any], parent_object: Base, properties_dict: dict[str, Any], key: str) -> None:
        """Apply the specific action logic on the parameter."""
        pass

    @abstractmethod
    def report(self, automate_context: AutomationContext) -> None:
        """Method to provide feedback based on the action's results."""
        pass


class RemovalAction(ParameterAction):
    """Action to remove parameters based on a matching strategy."""

    def __init__(self, matcher: ParameterMatcher) -> None:
        """Initialize with a matcher strategy."""
        super().__init__()
        self.matcher = matcher

    def check(self, param_name: str) -> bool:
        """Check if parameter matches using the provided matcher."""
        return self.matcher.matches(param_name)

    def apply(
            self,
            parameter: dict[str, Any],
            parent_object: Base,
            containing_dict: dict[str, Any],
            parameter_key: str
    ) -> None:
        """Remove the parameter from the containing dictionary if it matches."""
        param_name = parameter.get("name", parameter_key)

        # Remove from the containing dictionary
        containing_dict.pop(parameter_key, None)

        # Track affected object and parameter
        self.affected_parameters[getattr(parent_object, "id", None)].append(param_name)

    def report(self, automate_context: AutomationContext) -> None:
        """Provide feedback based on the action's results."""
        if not self.affected_parameters:
            return

        removed_params = set(
            param for params in self.affected_parameters.values() for param in params
        )

        message = f"The following parameters were removed: {', '.join(removed_params)}"

        automate_context.attach_info_to_objects(
            category="Removed_Parameters",
            object_ids=list(self.affected_parameters.keys()),
            message=message,
        )


# Factory functions to create specific actions with the right matcher
def create_prefix_removal_action(forbidden_prefix: str, strict_mode: bool = False) -> RemovalAction:
    """Create a removal action that matches by prefix."""
    matcher = PrefixMatcher(forbidden_prefix, strict_mode)
    return RemovalAction(matcher)


def create_pattern_removal_action(pattern: str, strict_mode: bool = False) -> RemovalAction:
    """Create a removal action that matches by pattern/regex."""
    matcher = PatternMatcher(pattern, strict_mode)
    return RemovalAction(matcher)


# Placeholder for future anonymization action
def create_anonymization_action() -> None:
    """Create an action that anonymizes email addresses in parameter values.
    
    This is a placeholder for future implementation.
    """
    # To be implemented
    return None