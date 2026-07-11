import os

# Apify token is read from the environment so secrets never live in git history.
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")