# Installation Gotchas

## Bad magic number in .pyc file

**Problem:**
When running the application, you may see an error like:

    RuntimeError: Bad magic number in .pyc file

**Cause:**
This happens when the `.pyc` files in the `__pycache__` directory were generated with a different Python version than the one currently active in your environment.

**Solution:**

1. Delete all files in the `__pycache__` directory.
2. Recompile your Python files using the current Python version:

        python -m compileall src

3. Run the installer again:

        .\run.bat

**Tip:** Always use the same Python version for compiling and running your code, ideally inside your project's virtual environment.
