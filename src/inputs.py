# inputs.py
from enum import Enum
from pydantic import Field

from speckle_automate import AutomateBase



class SanitizationMode(Enum):
    PREFIX_MATCHING = "Prefix Matching"
    PATTERN_MATCHING = "Pattern Matching"
    ANONYMIZATION = "Anonymization"

def create_one_of_enum(enum_cls):
    """
    Helper function to create a JSON schema from an Enum class.
    This is used for generating user input forms in the UI.
    """
    return [{"const": item.value, "title": item.name} for item in enum_cls]

class FunctionInputs(AutomateBase):
    sanitization_mode: SanitizationMode = Field(
        default=SanitizationMode.PREFIX_MATCHING,
        title="Data Sanitization Mode",
        description="Select the mode of data sanitization: Prefix Matching, Pattern Matching, or Anonymization.",
        json_schema_extra={
            "oneOf": create_one_of_enum(SanitizationMode),
        },
    )

    forbidden_parameter_input: str = Field(
        title="Parameter Prefix to Cleanse",
        description=(
            # for pattern or prefix mode this text input will be used to specify the patterns or prefixes to remove
            # for anonymization mode this input is not required. Emails will be detected in property values.

            "Specify the prefix or pattern to remove from the parameter names. "
        )
    )