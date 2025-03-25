"""Helper classes and functions for the parameter checker."""

from specklepy.objects import Base

from data_shield.actions import ParameterAction


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
        # Debug counters
        self.total_objects_processed = 0
        self.revit_params_processed = 0

    def process_context(self, context):
        """Process a traversal context to handle parameters and properties.

        Args:
            context: The traversal context containing the current object
        """
        current_object = context.current
        self.total_objects_processed += 1

        # First handle modern v3 properties
        if hasattr(current_object, "properties") and current_object.properties is not None:
            properties_dict = (
                current_object.properties.__dict__
                if isinstance(current_object.properties, Base)
                else current_object.properties
            )
            self.process_properties_dict(properties_dict, current_object)

        # Then handle legacy v2 Revit parameters
        if hasattr(current_object, "parameters") and current_object.parameters is not None:
            self.process_revit_parameters(current_object)

    def process_properties_dict(self, properties_dict, current_object):
        """Recursively process v3-style properties dictionary to find and apply the action to parameters.

        Args:
            properties_dict: The properties dictionary to process
            current_object: The current object being processed
        """
        if not properties_dict:
            return

        for key, value in list(properties_dict.items()):  # Safe iteration during mutation
            if isinstance(value, dict) and "value" in value:
                param_name = value.get("name", key)

                # Check based on mode (name or value)
                if self.check_values:
                    # For value-based actions (like anonymization)
                    param_value = value.get("value", "")
                    if self.action.check(param_value):
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

        # If parameters is a dictionary rather than a Base object, use it directly
        if isinstance(parameters, dict):
            self.process_properties_dict(parameters, current_object)
            return

        # Get all parameter keys - handle different ways of storing parameters
        param_keys = []

        # Try get_dynamic_member_names() for Base objects
        if hasattr(parameters, "get_dynamic_member_names"):
            param_keys.extend(parameters.get_dynamic_member_names())

        # Try __dict__ for standard attributes
        if hasattr(parameters, "__dict__"):
            param_keys.extend(k for k in parameters.__dict__.keys() if not k.startswith("_"))

        # Try dir() as a last resort
        if not param_keys:
            param_keys.extend(k for k in dir(parameters) if not k.startswith("_") and k != "get_dynamic_member_names")

        # Process each parameter
        for parameter_key in param_keys:
            # Track for debugging
            self.revit_params_processed += 1

            # Skip known non-parameter attributes
            if parameter_key in ["speckle_type", "id", "totalChildrenCount"]:
                continue

            # Get the parameter object using multiple methods
            param_obj = None
            param_value = None

            # Try __getitem__ first (common for Revit parameters)
            try:
                param_obj = parameters.__getitem__(f"{parameter_key}")
            except (AttributeError, KeyError, TypeError):
                try:
                    # Try direct attribute access
                    param_obj = getattr(parameters, parameter_key, None)
                except KeyError:
                    continue

            # If we couldn't get the parameter, skip it
            if param_obj is None:
                continue

            # Prepare a parameter dict with the info we have
            param_dict = {}

            # Get the name - try from the parameter object first
            param_name = getattr(param_obj, "name", parameter_key) if isinstance(param_obj, Base) else parameter_key
            param_dict["name"] = param_name

            # Get the value
            if isinstance(param_obj, Base) and hasattr(param_obj, "value"):
                param_value = getattr(param_obj, "value")
                param_dict["value"] = param_value
            elif isinstance(param_obj, dict) and "value" in param_obj:
                param_value = param_obj["value"]
                param_dict["value"] = param_value
            else:
                # If we can't find a value, this might not be a parameter
                continue

            # Add any other useful metadata
            param_dict["applicationInternalName"] = parameter_key

            # Check based on mode (name or value)
            if self.check_values:
                # For value-based actions (like anonymization)
                if isinstance(param_value, str) and self.action.check(param_value):
                    # Apply the action
                    self.action.apply(param_dict, current_object, parameters, parameter_key)
                    self.processed_objects.add(current_object.id)
            else:
                # For name-based actions (like removal)
                if self.action.check(param_name):
                    # Apply the action
                    self.action.apply(param_dict, current_object, parameters, parameter_key)
                    self.processed_objects.add(current_object.id)
