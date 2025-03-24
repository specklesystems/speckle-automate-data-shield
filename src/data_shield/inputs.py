"""Define the input schema for the function."""
from enum import Enum

from pydantic import Field
from speckle_automate import AutomateBase


class SanitizationMode(Enum):
    """Define the sanitization modes."""
    PREFIX_MATCHING = "Prefix Matching"
    PATTERN_MATCHING = "Pattern Matching"
    ANONYMIZATION = "Anonymization"

def create_one_of_enum(enum_cls):
    """Helper function to create a JSON schema from an Enum class.
    
    This is used for generating user input forms in the UI.
    """
    return [{"const": item.value, "title": item.name} for item in enum_cls]

class FunctionInputs(AutomateBase):
    """Define the input schema for the function."""

    sanitization_mode: SanitizationMode = Field(
        title="Data Sanitization Mode",
        default=SanitizationMode.PREFIX_MATCHING,
        description=(
            "Choose how data values are sanitized during processing. The selected mode determines how matching "
            "and masking of sensitive information is applied:\n\n"
            "- **Prefix Matching**: Simple, fast matching based on predefined prefixes. Use this when patterns "
            "are predictable and performance is critical.\n\n"
            "- **Pattern Matching**: Allows the use of more advanced patterns (glob or regex) to define which "
            "values should be sanitized. Recommended if you need flexible or complex matching rules.\n\n"
            "- **Anonymization**: Replaces all matched values with anonymized placeholders. Use this mode when "
            "irreversible masking is required for security or privacy compliance.\n\n"
            "If you're unsure, start with Prefix Matching for simplicity, and move to Pattern Matching as your "
            "sanitization needs grow more complex."
        ),
        json_schema_extra={
            "oneOf": create_one_of_enum(SanitizationMode),
        },
    )

    # for pattern or prefix mode this text input will be used to specify the patterns or prefixes to remove
    # for anonymization mode this input is not required. Emails will be detected in property values.
    parameter_input: str = Field(
        title="Parameter Prefix to Cleanse",
        default="",
        description="Enter a pattern. Use '*' and '?' for simple matching. For regex, wrap in slashes like `/^foo_/`.",
        examples=["foo_*", "/^foo_\\d+$/i"]
    )

    strict_mode: bool = Field(
        default=False,
        description="If checked, matching is case-sensitive. If unchecked, case-insensitive."
    )
