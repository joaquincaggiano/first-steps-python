import os

MEDIA_DIR = "app/media"
MEDIA_URL = "/media"
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10"))  # 10MB
