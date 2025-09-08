import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Default to SQLite in current directory
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///harnes.db')

# You can easily change this to:
# DATABASE_URL = 'postgresql://user:password@localhost/harness_db'
# DATABASE_URL = 'mysql://user:password@localhost/harness_db'