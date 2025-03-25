"""Helper classes and functions for the parameter checker."""

from specklepy.objects import Base

from data_shield.actions import ParameterAction


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
            except KeyError:
                continue
            # Check if it's a Revit parameter
            if (
                not isinstance(param_obj, Base)
                or getattr(param_obj, "speckle_type", "") != "Objects.BuiltElements.Revit.Parameter"
            ):
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
