import os
from dotenv import load_dotenv

# Path to the .env file in the root
env_path = os.path.join(os.path.dirname(__file__), '../../.env')
load_dotenv(dotenv_path=env_path)

api_key = os.environ.get("MEMORY_SERVICE_API_KEY")
print(f"MEMORY_SERVICE_API_KEY: {api_key}")

if api_key == "msk_test_key":
    print("Verification SUCCESS: .env variables loaded correctly.")
else:
    print(f"Verification FAILURE: .env variables not loaded correctly. Found: {api_key}")
