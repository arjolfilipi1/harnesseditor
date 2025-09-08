# Initialize the database
from database.core import init_database, close_database
from services.data_loader import DataLoader

# Initialize with default SQLite
init_database()

try:
    # Load a specific harness
    harness = DataLoader.load_harness("MAIN_HARNESS")
    print(f"Loaded harness: {harness.name}")
    
    # Calculate branch lengths
    for branch_id, branch in harness.branches.items():
        length = branch.calculate_length()
        print(f"Branch {branch_id} length: {length} mm")
        
finally:
    close_database()