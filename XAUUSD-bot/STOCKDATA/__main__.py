# This file makes the STOCKDATA directory runnable as a module.
import sys
import os

# Get the project root directory (the parent of STOCKDATA)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add the project root to the Python path to allow for absolute imports
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now that the path is set, we can import the main function and run it.
# We use a relative import here because we are inside the STOCKDATA package.
from .main import main

if __name__ == "__main__":
    print("Executing STOCKDATA package...")
    main()
