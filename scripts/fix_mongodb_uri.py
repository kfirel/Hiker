#!/usr/bin/env python3
"""
Helper script to fix MongoDB URI format
"""

import urllib.parse
import sys

def fix_mongodb_uri(uri):
    """Fix MongoDB URI format - URL encode password if needed"""
    if not uri.startswith('mongodb+srv://') and not uri.startswith('mongodb://'):
        return uri
    
    # Parse the URI
    if 'mongodb+srv://' in uri:
        prefix = 'mongodb+srv://'
        rest = uri.replace(prefix, '')
    else:
        prefix = 'mongodb://'
        rest = uri.replace(prefix, '')
    
    # Split by @
    if '@' not in rest:
        print("⚠️  No authentication found in URI")
        return uri
    
    auth_part, host_part = rest.split('@', 1)
    
    if ':' not in auth_part:
        print("⚠️  No password found in URI")
        return uri
    
    username, password = auth_part.split(':', 1)
    
    # URL encode password
    encoded_password = urllib.parse.quote(password, safe='')
    
    # Reconstruct URI
    fixed_uri = f"{prefix}{username}:{encoded_password}@{host_part}"
    
    return fixed_uri

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_mongodb_uri.py 'mongodb+srv://user:pass@host'")
        sys.exit(1)
    
    original_uri = sys.argv[1]
    fixed_uri = fix_mongodb_uri(original_uri)
    
    print("Original URI:")
    print(original_uri)
    print("\nFixed URI (with URL-encoded password):")
    print(fixed_uri)
    
    if original_uri != fixed_uri:
        print("\n💡 Copy the fixed URI to your .env file")



