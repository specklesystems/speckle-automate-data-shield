"""Run integration tests with a speckle server."""

from speckle_automate import (
    AutomationContext,
    AutomationRunData,
    AutomationStatus,
    run_function,
)
from speckle_automate.fixtures import *

from data_shield.function import FunctionInputs, SanitizationMode, automate_function


class TestFunction:
    """Test the automate function."""

    def test_function_run(self, test_automation_run_data: AutomationRunData, test_automation_token: str) -> None:
        """Run an integration test for the automate function."""
        automation_context = AutomationContext.initialize(test_automation_run_data, test_automation_token)

        automate_sdk = run_function(
            automation_context,
            automate_function,
            FunctionInputs(
                sanitization_mode=SanitizationMode.ANONYMIZATION,
                parameter_input="SPECKLE",
                strict_mode=False,
            ),
        )

        assert automate_sdk.run_status == AutomationStatus.SUCCEEDED
