#!/usr/bin/env python3
import os
import sys
import django

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try to load .env file explicitly
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    print(f"Attempting to load: {env_path}")
    load_dotenv(env_path, verbose=True)
except ImportError:
    print("python-dotenv not installed, trying decouple...")

# Set up Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cms_backend.settings')

# Print some debugging info
print("\nEnvironment variables before Django setup:")
print(f"  AWS_STORAGE_BUCKET_NAME: {os.environ.get('AWS_STORAGE_BUCKET_NAME', 'NOT SET')}")
print(f"  AWS_ACCESS_KEY_ID: {os.environ.get('AWS_ACCESS_KEY_ID', 'NOT SET')[:10] if os.environ.get('AWS_ACCESS_KEY_ID') else 'NOT SET'}")

django.setup()

from django.conf import settings

print("\n" + "=" * 70)
print("AWS S3 CONFIGURATION TEST")
print("=" * 70)

print("\nFile Storage Backend:")
print(f"  DEFAULT_FILE_STORAGE: {settings.DEFAULT_FILE_STORAGE}")

print("\nAWS Credentials:")
print(f"  AWS_ACCESS_KEY_ID: {'***' if settings.AWS_ACCESS_KEY_ID else 'Not set'}")
print(f"  AWS_SECRET_ACCESS_KEY: {'***' if settings.AWS_SECRET_ACCESS_KEY else 'Not set'}")

print("\nAWS S3 Configuration:")
print(f"  AWS_STORAGE_BUCKET_NAME: {settings.AWS_STORAGE_BUCKET_NAME}")
print(f"  AWS_S3_ENDPOINT_URL: {settings.AWS_S3_ENDPOINT_URL}")
print(f"  AWS_S3_REGION_NAME: {settings.AWS_S3_REGION_NAME}")
print(f"  AWS_S3_ADDRESSING_STYLE: {settings.AWS_S3_ADDRESSING_STYLE}")
print(f"  AWS_S3_VERIFY: {settings.AWS_S3_VERIFY}")
print(f"  AWS_S3_USE_SSL: {settings.AWS_S3_USE_SSL}")
print(f"  AWS_QUERYSTRING_AUTH: {settings.AWS_QUERYSTRING_AUTH}")
print(f"  AWS_S3_FILE_OVERWRITE: {settings.AWS_S3_FILE_OVERWRITE}")

print("\nMedia URL Configuration:")
print(f"  MEDIA_URL: {settings.MEDIA_URL}")

if settings.DEFAULT_FILE_STORAGE == 'storages.backends.s3boto3.S3Boto3Storage':
    print("\n✓ S3 Backend is ENABLED and will be used for file uploads!")
    print(f"✓ Formation letters will be stored in: s3://{settings.AWS_STORAGE_BUCKET_NAME}/")
else:
    print("\n✗ S3 Backend is NOT ENABLED. Using local storage fallback.")
    print(f"✗ Formation letters will be stored in: {settings.MEDIA_URL}")

print("\n" + "=" * 70)
