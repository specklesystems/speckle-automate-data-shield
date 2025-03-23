# function.py

from speckle_automate import AutomationContext
from specklepy.objects import Base

from actions import PrefixRemovalAction
from inputs import SanitizationMode
from rules import ParameterRules
from src.inputs import FunctionInputs
from traversal import get_data_traversal_rules


class ParameterProcessor:
    """Class to handle parameter processing with various actions."""

    def __init__(self, removal_action):
        self.removal_action = removal_action
        self.cleansed_objects = set()

    def process_context(self, context):
        """Process a traversal context to handle parameters and properties."""
        current_object = context.current

        # Handle parameters (v2 structure)
        if hasattr(current_object, "parameters") and current_object.parameters is not None:
            self.process_parameters(current_object.parameters, current_object)

        # Handle properties (v3 structure)
        if hasattr(current_object, "properties") and current_object.properties is not None:
            self.process_properties(current_object.properties, current_object)

    def process_parameters(self, parameters, current_object):
        """Process v2 style Base object parameters."""
        # Checking rules
        is_revit_parameter = ParameterRules.speckle_type_rule(
            "Objects.BuiltElements.Revit.Parameter"
        )
        has_forbidden_prefix = self.removal_action.forbidden_prefix

        if isinstance(parameters, Base):
            for param_name in parameters.get_member_names():
                param_value = getattr(parameters, param_name)
                if (
                        isinstance(param_value, Base)
                        and is_revit_parameter(param_value)
                        and param_value.name.startswith(has_forbidden_prefix)
                ):
                    self.removal_action.apply(param_value, current_object)
                    self.cleansed_objects.add(current_object.id)

    def process_properties(self, properties, current_object):
        """Process v3 style dictionary properties."""
        if isinstance(properties, dict) or (
                isinstance(properties, Base) and hasattr(properties, "Parameters")
        ):
            # Get Parameters as dict from either dict or Base object
            parameters_dict = (
                properties.get("Parameters")
                if isinstance(properties, dict)
                else getattr(properties, "Parameters", None)
            )
            if parameters_dict:
                self.process_properties_dict(parameters_dict, current_object)

    def process_properties_dict(self, properties_dict, current_object):
        """Process properties dictionary structure with primitives or nested dicts."""
        has_forbidden_prefix = self.removal_action.forbidden_prefix

        for key, value in properties_dict.items():
            if isinstance(value, dict):
                # Recursively process nested dictionaries
                self.process_properties_dict(value, current_object)
            # Check dictionary parameter with value field
            elif isinstance(value, dict) and "value" in value:
                parameter_name = value.get("name", key)

                if parameter_name.startswith(has_forbidden_prefix):
                    self.removal_action.apply(value, current_object)
                    self.cleansed_objects.add(current_object.id)

def automate_function(
        automate_context: AutomationContext,
        function_inputs: FunctionInputs,
) -> None:
    """Main function for the Speckle Automation."""
    # Validate inputs
    if (
            function_inputs.sanitization_mode != SanitizationMode.ANONYMIZATION
            and not function_inputs.forbidden_parameter_input
    ):
        automate_context.mark_run_failed("No parameter input has been set.")
        return

    # Setup actions
    removal_action = PrefixRemovalAction(function_inputs.forbidden_parameter_input)

    # Setup processor
    processor = ParameterProcessor(removal_action)

    # Get data
    version_root_object = automate_context.receive_version()

    # Traverse the received Speckle data
    speckle_data = get_data_traversal_rules()
    traversal_contexts = speckle_data.traverse(version_root_object)

    # Process all contexts
    for context in traversal_contexts:
        processor.process_context(context)

    # Check if any objects were affected
    if not processor.cleansed_objects:
        automate_context.mark_run_success("No parameters were removed.")
        return

    # Generate report
    removal_action.report(automate_context)

    # Create new version
    new_version_id = automate_context.create_new_version_in_project(
        version_root_object, "cleansed", "Cleansed Parameters"
    )

    if not new_version_id:
        automate_context.mark_run_failed("Failed to create a new version.")
        return

    # Final summary
    automate_context.mark_run_success("Actions applied and reports generated.")