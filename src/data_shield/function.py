"""Updated main Automate function for parameter sanitization."""

from speckle_automate import AutomationContext

from data_shield.actions import (
    create_anonymization_action,
    create_pattern_removal_action,
    create_prefix_removal_action,
)
from data_shield.helpers import ParameterProcessor
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
        f"{function_inputs.sanitization_mode.value}"
        f"{' running in strict mode' if function_inputs.strict_mode else ''}."
    )
