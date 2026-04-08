#!/usr/bin/env python3
"""
Test script to verify Pinata and Supabase connections.
Run this to check if your credentials are working.
"""
import os
import sys

# Add the parent directory to path to import utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("CONNECTION TEST: Pinata & Supabase")
print("=" * 60)

# Check environment variables
print("\n[1] Checking Environment Variables...")
print("-" * 40)

pinata_jwt = os.environ.get("PINATA_JWT", "")
supabase_url = os.environ.get("SUPABASE_URL", "")
supabase_key = os.environ.get("SUPABASE_KEY", "")

if pinata_jwt and pinata_jwt != "your_pinata_jwt_token_here":
    print(f"  PINATA_JWT: {'*' * 10}...{pinata_jwt[-10:]} (SET)")
else:
    print("  PINATA_JWT: NOT SET or using placeholder")

if supabase_url and not supabase_url.startswith("paste_"):
    print(f"  SUPABASE_URL: {supabase_url[:30]}... (SET)")
else:
    print("  SUPABASE_URL: NOT SET or using placeholder")

if supabase_key and not supabase_key.startswith("paste_"):
    print(f"  SUPABASE_KEY: {'*' * 10}...{supabase_key[-10:]} (SET)")
else:
    print("  SUPABASE_KEY: NOT SET or using placeholder")

# Test Pinata Connection
print("\n[2] Testing Pinata Connection...")
print("-" * 40)

try:
    from utils.ipfs_client import upload_to_ipfs, fetch_from_ipfs
    
    # Test with a simple payload
    test_data = {"test": True, "message": "Connection test", "timestamp": str(__import__('datetime').datetime.now())}
    
    print("  Uploading test data to IPFS...")
    cid = upload_to_ipfs(test_data, name="connection_test")
    print(f"  SUCCESS! CID: {cid}")
    
    # Try to fetch it back
    print("  Fetching data from IPFS...")
    fetched = fetch_from_ipfs(cid)
    print(f"  SUCCESS! Data retrieved: {fetched.get('message')}")
    
except Exception as e:
    print(f"  FAILED: {e}")

# Test Supabase Connection
print("\n[3] Testing Supabase Connection...")
print("-" * 40)

try:
    from utils.supabase_client import store_audit_metadata, query_audits
    
    # Try to query (safer than inserting)
    print("  Querying audit logs...")
    results = query_audits(limit=1)
    print(f"  SUCCESS! Connection established. Found {len(results)} records.")
    
except Exception as e:
    print(f"  FAILED: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
