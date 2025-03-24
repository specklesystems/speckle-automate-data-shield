from speckle_automate import execute_automate_function

from data_shield import FunctionInputs
from data_shield import automate_function

# make sure to call the function with the executor
if __name__ == "__main__":
    # NOTE: always pass in the automate function by its reference; do not invoke it!

    execute_automate_function(automate_function, FunctionInputs)
