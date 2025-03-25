"""Updated main Automate function for parameter sanitization."""

from speckle_automate import AutomationContext
from specklepy.objects import Base

from data_shield.actions import (
    ParameterAction,
    create_anonymization_action,
    create_pattern_removal_action,
    create_prefix_removal_action,
)
from data_shield.inputs import FunctionInputs, SanitizationMode
from data_shield.traversal import get_data_traversal_rules


def automate_function(
    automate_context: AutomationContext,
    function_inputs: FunctionInputs,
) -> None:
    """Main function for parameter sanitization.

    Args:
        automate_context: The automation context
        function_inputs: The function inputs
    """
    # Create appropriate action based on sanitization mode
    action = None
    check_values = False

    if function_inputs.sanitization_mode == SanitizationMode.PREFIX_MATCHING:
        if not function_inputs.parameter_input:
            automate_context.mark_run_failed("No parameter prefix has been set for PREFIX_MATCHING mode.")
            return
        action = create_prefix_removal_action(function_inputs.parameter_input, function_inputs.strict_mode)

    elif function_inputs.sanitization_mode == SanitizationMode.PATTERN_MATCHING:
        if not function_inputs.parameter_input:
            automate_context.mark_run_failed("No parameter pattern has been set for PATTERN_MATCHING mode.")
            return
        action = create_pattern_removal_action(function_inputs.parameter_input, function_inputs.strict_mode)

    elif function_inputs.sanitization_mode == SanitizationMode.ANONYMIZATION:
        # Anonymization doesn't require a parameter input as it automatically detects emails
        action = create_anonymization_action()
        # For anonymization, we check values, not names
        check_values = True

    if not action:
        automate_context.mark_run_failed("Failed to create a valid action.")
        return

    # Process the model with the selected action
    processor = ParameterProcessor(action, check_values)

    version_root_object = automate_context.receive_version()
    speckle_data = get_data_traversal_rules()
    traversal_contexts = speckle_data.traverse(version_root_object)

    # the run_data object contains all the information about the specific Automate run
    run_data = automate_context.automation_run_data

    # included in the run_data object is the action(s) that triggered the Automate run and project_id
    # at time of writing, only one action can trigger an Automate run, a new model version
    trigger_model_id = run_data.triggers[0].payload.model_id
    project_id = run_data.project_id

    # the automate_context includes an authenticated Speckle client which we can use specklepy methods with
    trigger_model = automate_context.speckle_client.model.get(trigger_model_id, project_id)

    for context in traversal_contexts:
        processor.process_context(context)

    if not processor.processed_objects:
        automate_context.mark_run_success("No parameters were processed.")
        return

    # Generate report for the action
    action.report(automate_context)

    # Create a new version with the processed parameters
    new_model_id, new_version_id = automate_context.create_new_version_in_project(
        version_root_object, f"processed/{trigger_model.name}", "Processed Parameters"
    )

    if not new_version_id:
        automate_context.mark_run_failed("Failed to create a new version.")
        return

    # We can pin the result view to the specific version we created.
    automate_context.set_context_view([f"{new_model_id}@{new_version_id}"], False)

    automate_context.mark_run_success(
        f"Parameters processed successfully with shield function "
        f"{function_inputs.sanitization_mode}"
        f"{' running in strict mode' if function_inputs.strict_mode else ''}."
    )


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
            except:
                continue

            # Check if it's a Revit parameter
            if not isinstance(param_obj, Base) or getattr(param_obj, "speckle_type", "") != "Objects.BuiltElements.Revit.Parameter":
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
                    self.processed_objects.add(current_object.id)
