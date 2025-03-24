from speckle_automate import AutomationContext
from specklepy.objects import Base

from data_shield import FunctionInputs, SanitizationMode, PrefixRemovalAction, get_data_traversal_rules


class ParameterProcessor:
    """Class to handle parameter processing with actions, prioritising v3 but keeping v2 support for later."""

    def __init__(self, removal_action):
        self.removal_action = removal_action
        self.cleansed_objects = set()

    def process_context(self, context):
        """Process a traversal context to handle parameters and properties."""
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
        """Recursively process v3-style properties dictionary to find and remove parameters."""
        has_forbidden_prefix = self.removal_action.forbidden_prefix

        for key, value in list(properties_dict.items()):  # Safe iteration during mutation
            if isinstance(value, dict) and "value" in value:
                param_name = value.get("name", key)

                if param_name.startswith(has_forbidden_prefix):
                    self.removal_action.apply(value, current_object, properties_dict, key)
                    self.cleansed_objects.add(current_object.id)

            elif isinstance(value, dict):
                # Recurse into nested dictionaries
                self.process_properties_dict(value, current_object)


def automate_function(
        automate_context: AutomationContext,
        function_inputs: FunctionInputs,
) -> None:
    """Main function for parameter sanitization, prioritising v3 support."""

    if (
            function_inputs.sanitization_mode != SanitizationMode.ANONYMIZATION
            and not function_inputs.forbidden_parameter_input
    ):
        automate_context.mark_run_failed("No parameter input has been set.")
        return

    removal_action = PrefixRemovalAction(function_inputs.forbidden_parameter_input)
    processor = ParameterProcessor(removal_action)

    version_root_object = automate_context.receive_version()
    speckle_data = get_data_traversal_rules()
    traversal_contexts = speckle_data.traverse(version_root_object)

    for context in traversal_contexts:
        processor.process_context(context)

    if not processor.cleansed_objects:
        automate_context.mark_run_success("No parameters were removed.")
        return

    removal_action.report(automate_context)

    model_id, new_version_id = automate_context.create_new_version_in_project(
        version_root_object, "cleansed", "Cleansed Parameters"
    )

    if not new_version_id:
        automate_context.mark_run_failed("Failed to create a new version.")
        return

    automate_context.set_context_view([new_version_id], False)

    automate_context.mark_run_success("Actions applied and reports generated.")
