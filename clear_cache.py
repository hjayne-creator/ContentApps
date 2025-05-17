"""
Script to clear Flask's cache and rebuild the application.
Run this before restarting your application on Render.
"""
import os
import shutil
from datetime import datetime

# Log the execution
print(f"Cache clearing started at {datetime.now()}")

# Remove any __pycache__ directories 
found = 0
for root, dirs, files in os.walk('.'):
    if '__pycache__' in dirs:
        pycache_path = os.path.join(root, '__pycache__')
        print(f"Removing {pycache_path}")
        shutil.rmtree(pycache_path)
        found += 1

# Report results
print(f"Removed {found} __pycache__ directories")
print(f"Cache clearing completed at {datetime.now()}")
print("You can now restart your application") 