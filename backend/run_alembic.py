"""Helper to run Alembic without local package shadowing issues."""

import os
import sys

# Remove current dir from sys.path to avoid local alembic/ shadowing the package
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path = [p for p in sys.path if os.path.abspath(p) != backend_dir]

# Now import the real alembic
from alembic.config import main as alembic_main

# Re-add backend dir for our shared/models imports
sys.path.insert(0, backend_dir)

# Change to backend dir so alembic.ini paths resolve correctly
os.chdir(backend_dir)

alembic_main(sys.argv[1:])
