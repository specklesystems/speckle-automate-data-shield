"""Module for parameter actions and matching strategies."""

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any

from speckle_automate import AutomationContext
from specklepy.objects import Base

from data_shield.helpers import EmailMatcher, PatternChecker


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
        self, parameter: dict[str, Any], parent_object: Base, containing_dict: dict[str, Any] | Base, parameter_key: str
    ) -> None:
        """Remove the parameter from the containing dictionary if it matches.

        This method handles both dictionary-style containers and Base objects with attributes.

        Args:
            parameter: The parameter dictionary or object
            parent_object: The parent Speckle object
            containing_dict: The container (dict or Base object) holding the parameter
            parameter_key: The key or attribute name of the parameter
        """
        param_name = parameter.get("name", parameter_key)
        object_id = getattr(parent_object, "id", None)

        # Handle removal based on the container type
        if isinstance(containing_dict, dict):
            # Standard dictionary - just pop the key
            containing_dict.pop(parameter_key, None)
        elif isinstance(containing_dict, Base):
            # For Base objects like Revit parameters, try to remove using __dict__
            try:
                if hasattr(containing_dict, "__dict__") and parameter_key in containing_dict.__dict__:
                    containing_dict.__dict__.pop(parameter_key)
                else:
                    # If not in __dict__, try using dynamic attribute removal
                    containing_dict.__dict__.pop(parameter_key, None)
            except (AttributeError, KeyError, TypeError):
                # Fallback to alternative methods if direct dict manipulation fails
                try:
                    delattr(containing_dict, parameter_key)
                except (AttributeError, TypeError):
                    try:
                        setattr(containing_dict, parameter_key, None)
                    except (AttributeError, TypeError):
                        # If all removal attempts fail, try one more approach specific to Speckle Base objects
                        if (
                            hasattr(containing_dict, "get_dynamic_member_names")
                            and parameter_key in containing_dict.get_dynamic_member_names()
                        ):
                            # This is a workaround for dynamic properties in Speckle Base objects
                            application_name = parameter.get("applicationInternalName", parameter_key)
                            if application_name in containing_dict.__dict__:
                                containing_dict.__dict__.pop(application_name)

        # Track affected object and parameter
        self.affected_parameters[object_id].append(param_name)

    def report(self, automate_context: AutomationContext) -> None:
        """Provide feedback based on the action's results."""
        if not self.affected_parameters:
            return

        removed_params = set(param for params in self.affected_parameters.values() for param in params)

        message = f"The following parameters were removed: {', '.join(removed_params)}"

        automate_context.attach_info_to_objects(
            category="Removed_Parameters",
            object_ids=list(self.affected_parameters.keys()),
            message=message,
        )


class AnonymizationAction(ParameterAction):
    """Action to anonymize email addresses in parameter values."""

    def __init__(self) -> None:
        """Initialize the anonymization action with an email matcher."""
        super().__init__()
        self.email_matcher = EmailMatcher()
        # Count of anonymized parameters for reporting
        self.anonymized_count = 0

    def check(self, param_value: str) -> bool:
        """Check if parameter value contains an email address.

        Args:
            param_value: The parameter value to check

        Returns:
            bool: True if the parameter value contains an email address, False otherwise
        """
        return self.email_matcher.contains_email(param_value)

    def apply(
        self, parameter: dict[str, Any], parent_object: Base, containing_dict: dict[str, Any] | Base, parameter_key: str
    ) -> None:
        """Anonymize email addresses in the parameter value.

        Args:
            parameter: The parameter dictionary
            parent_object: The parent Speckle object
            containing_dict: The container (dict or Base object) holding the parameter
            parameter_key: The key or attribute name of the parameter
        """
        if "value" not in parameter or not isinstance(parameter["value"], str):
            return

        param_name = parameter.get("name", parameter_key)
        original_value = parameter["value"]
        object_id = getattr(parent_object, "id", None)

        # Anonymize email addresses in the parameter value
        anonymized_value = self.email_matcher.anonymize_email(original_value)

        # Only track changes if something was actually anonymized
        if anonymized_value != original_value:
            # Update the parameter value in place
            parameter["value"] = anonymized_value

            # If we're dealing with a Base object parameter (like in Revit),
            # update the actual value property of the parameter object
            if isinstance(containing_dict, Base):
                try:
                    # Try to get the parameter object using __getitem__ first (Revit v2 style)
                    param_obj = containing_dict.__getitem__(parameter_key)
                    if param_obj is not None and hasattr(param_obj, "value"):
                        setattr(param_obj, "value", anonymized_value)
                except (AttributeError, KeyError, TypeError):
                    # Fallback to standard attribute access
                    param_obj = getattr(containing_dict, parameter_key, None)
                    if param_obj is not None and hasattr(param_obj, "value"):
                        setattr(param_obj, "value", anonymized_value)

            # Track affected object and parameter
            self.affected_parameters[object_id].append(param_name)
            self.anonymized_count += 1

    def report(self, automate_context: AutomationContext) -> None:
        """Provide feedback based on the action's results.

        Args:
            automate_context: The automation context
        """
        if not self.affected_parameters:
            return

        anonymized_params = set(param for params in self.affected_parameters.values() for param in params)

        message = f"Email addresses were anonymized in {len(anonymized_params)} parameters"

        automate_context.attach_info_to_objects(
            category="Anonymized_Parameters",
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


# Factory function to create anonymization action
def create_anonymization_action() -> AnonymizationAction:
    """Create an action that anonymizes email addresses in parameter values."""
    return AnonymizationAction()
