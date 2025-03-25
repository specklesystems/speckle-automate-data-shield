# Data Shield - Developer Guide

This document provides technical information for developers working on the Data Shield Speckle Automate function. It covers deployment workflows, core components, and guidance for extending the function.

## Deployment to Speckle Automate

### Creating a Release

The function is automatically deployed to Speckle Automate when a new release is created on GitHub:

1. Ensure your changes are committed and pushed to the main branch
2. Create a `requirements.txt` file (see next section) and commit to main branch
3. Create a new GitHub release:
    - Go to your repository on GitHub
    - Navigate to "Releases" under the repository name
    - Click "Draft a new release"
    - Create a **new tag** (e.g., `v1.0.1`)
    - Write a descriptive title and release notes
    - Click "Publish release"

Creating a new release triggers the GitHub Actions workflow defined in `main.yml`, which builds and publishes the function to Speckle Automate.

### Managing Dependencies

You can use any dependency management tool of your choice for local development (Poetry, pip, uv, etc.), but Speckle Automate requires a `requirements.txt` file for deployment.

**Important**: You must create and commit the `requirements.txt` file to the repository **before** creating a release. The deployment workflow relies on this file being present in the repository.

To generate and commit the requirements file based on your local environment:

- With standard pip: `pip freeze > requirements.txt`
- With uv: `uv pip freeze > requirements.txt`
- With Poetry: `poetry export -f requirements.txt --output requirements.txt --without-hashes`
- Or manually create/edit the file to include necessary dependencies

Then commit the updated file:
```bash
git add requirements.txt
git commit -m "Update requirements.txt"
git push
```

Only after the requirements.txt is committed should you create a new release as described above.

Note that during deployment, the GitHub Actions workflow uses `uv` to install the dependencies, but your local development environment can use any tool you prefer.

### Deployment Workflow Details

The deployment workflow:

1. Checks out the repository
2. Sets up Python 3.13
3. Installs dependencies from `requirements.txt`
4. Extracts the function schema
5. Uses the Speckle Automate GitHub composite action to:
    - Build a Docker image with the function
    - Push the image to the Speckle Automate registry
    - Update the function in Speckle Automate

## Core Components

### Parameter Matching System

The function uses a strategy pattern for parameter matching, allowing flexible and extensible matching rules:

#### ParameterMatcher Classes

* `ParameterMatcher` (ABC): Abstract base class for all matchers
* `PrefixMatcher`: Matches parameters by prefix (with optional case sensitivity)
* `PatternMatcher`: Uses regex/glob patterns for more complex matching

```python
# Example: Creating a custom matcher
class SuffixMatcher(ParameterMatcher):
    """Matches parameters by suffix."""
    
    def matches(self, param_name: str) -> bool:
        """Check if the parameter name ends with the match value."""
        if self.strict_mode:
            return param_name.endswith(self.match_value)
        return param_name.lower().endswith(self.match_value.lower())
```

#### Pattern Checking

The `PatternChecker` class handles both glob-style patterns (e.g., `speckle_*`) and regular expressions (e.g., `/^speckle_\d+$/i`):

* Glob patterns use `fnmatch` for simple wildcard matching
* Regex patterns must be wrapped in slashes (`/pattern/`)
* Case sensitivity is controlled by:
    - The global `strict_mode` parameter
    - The `/i` flag for regex patterns (overrides `strict_mode`)

### Traversal System

The function uses Speckle's graph traversal system to navigate the complex object hierarchy:

1. `GraphTraversal` from `specklepy.objects.graph_traversal.traversal` defines rules for how to navigate objects
2. `TraversalRule` objects define:
    - Conditions for when a rule applies to an object
    - Methods to extract the next objects to traverse
3. Our custom rules in `traversal.py` focus on:
    - `display_value_rule`: For objects with displayValue/elements properties
    - `default_rule`: General fallback for traversing all object members

The traversal system provides contexts that contain:
- The current object being traversed
- The path taken to reach that object
- Other metadata used during traversal

### Parameter Actions

Actions implement the logic for what to do when a parameter match is found:

#### ParameterAction Classes

* `ParameterAction` (ABC): Abstract base class for all actions
* `RemovalAction`: Removes matching parameters from objects
* `AnonymizationAction`: Masks email addresses in parameter values

Each action implements:
- `check()`: Determines if the action should be applied
- `apply()`: Performs the action on a matching parameter
- `report()`: Generates feedback for the Automate context

```python
# Example: Creating a custom action
class TransformAction(ParameterAction):
    """Action to transform parameter values based on a rule."""
    
    def __init__(self, matcher: ParameterMatcher, transform_func) -> None:
        """Initialize with a matcher strategy and transform function."""
        super().__init__()
        self.matcher = matcher
        self.transform_func = transform_func
        
    def check(self, param_name: str) -> bool:
        """Check if parameter matches using the provided matcher."""
        return self.matcher.matches(param_name)
        
    def apply(self, parameter, parent_object, containing_dict, parameter_key) -> None:
        """Transform the parameter value."""
        param_name = parameter.get("name", parameter_key)
        object_id = getattr(parent_object, "id", None)
        
        if "value" in parameter and isinstance(parameter["value"], str):
            parameter["value"] = self.transform_func(parameter["value"])
            
        # Track affected object and parameter
        self.affected_parameters[object_id].append(param_name)
        
    def report(self, automate_context: AutomationContext) -> None:
        """Report the transformed parameters."""
        if not self.affected_parameters:
            return
            
        transformed_params = set(param for params in self.affected_parameters.values() for param in params)
        
        message = f"Transformed {len(transformed_params)} parameters"
        
        automate_context.attach_info_to_objects(
            category="Transformed_Parameters",
            object_ids=list(self.affected_parameters.keys()),
            message=message,
        )
```

#### Parameter Processing

The `ParameterProcessor` class orchestrates the application of actions:

1. Takes an action and a flag indicating whether to check parameter names or values
2. Processes traversal contexts by examining properties and parameters
3. Handles both modern (v3) and legacy (v2) Speckle objects
4. Applies the action to matching parameters
5. Tracks processed objects for reporting

### Adding New Sanitization Modes

To add a new sanitization mode:

1. Update the `SanitizationMode` enum in `inputs.py`:
   ```python
   class SanitizationMode(Enum):
       PREFIX_MATCHING = "Prefix Matching"
       PATTERN_MATCHING = "Pattern Matching"
       ANONYMIZATION = "Anonymization"
       NEW_MODE = "Your New Mode"  # Add your new mode here
   ```

2. Create any necessary new matchers or actions in `actions.py`

3. Update the `automate_function` in `function.py` to handle the new mode:
   ```python
   if function_inputs.sanitization_mode == SanitizationMode.NEW_MODE:
       # Add specific validation for your new mode
       action = create_your_new_action()  # Create a factory function for your action
   ```

## Function Flow

The main function flow is:

1. User selects a sanitization mode and provides parameters via the UI
2. Function creates the appropriate action based on the mode
3. Version data is received from Speckle
4. Traversal rules navigate through the object tree
5. Parameters are processed with the selected action
6. Results are reported back to the Automate context
7. A new sanitized version is created

## Additional Resources

- [Speckle Automate Documentation](https://automate.speckle.dev/)
- [Speckle Python SDK Documentation](https://speckle.guide/dev/python.html)
- [Pydantic Documentation](https://docs.pydantic.dev/) (for function inputs)

## Testing

### Local Testing with pytest

pytest is the recommended way to test Speckle Automate functions locally. This allows you to verify your function works correctly before deploying it.

1. Set up your test environment by creating a `.env` file with your Speckle credentials:

   ```
   SPECKLE_TOKEN="9a110400812dc32b57e524c9c6f1a2000ebabec1c9"
   SPECKLE_SERVER_URL="https://app.speckle.systems/"
   SPECKLE_PROJECT_ID="d94c63b75d"
   SPECKLE_AUTOMATION_ID="99896f98b6"
   ```

2. Run the tests with your preferred method:

   ```bash
   # Using pytest directly
   python -m pytest
   
   # Or if using a virtual environment tool
   # poetry run pytest
   ```

The tests in `test_function.py` provide examples of how to set up the automation context and run the function with different inputs.

### Setting Up a Test Automation

To properly test your function, you should:

1. Create a test automation in Speckle Automate
2. Use the provided IDs and token in your `.env` file
3. This allows your tests to interact with actual Speckle objects and verify the function's behavior

The `speckle-automate` package provides fixtures that help with loading these environment variables and setting up the test context automatically.

Example test setup:

```python
def test_function_run(test_automation_run_data: AutomationRunData, test_automation_token: str) -> None:
    """Run an integration test for the automate function."""
    automation_context = AutomationContext.initialize(test_automation_run_data, test_automation_token)
    
    # Run your function with test inputs
    automate_sdk = run_function(
        automation_context,
        automate_function,
        FunctionInputs(sanitization_mode=SanitizationMode.PATTERN_MATCHING, parameter_input="test_*", strict_mode=True),
    )
    
    # Verify the results
    assert automate_sdk.run_status == AutomationStatus.SUCCEEDED
```

The fixtures `test_automation_run_data` and `test_automation_token` are provided by the `speckle-automate` package and automatically use the values from your `.env` file.