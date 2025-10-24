#!/usr/bin/env python3
"""
VAPID Key Generator for Web Push Notifications
-----------------------------------------------
This script generates VAPID keys required for browser push notifications.

Usage:
    python scripts/generate_vapid_keys.py

The script will generate a public and private VAPID key pair and display
them in the format needed for your .env file.

Add these keys to your environment variables:
    VAPID_PUBLIC_KEY=<public_key>
    VAPID_PRIVATE_KEY=<private_key>
    VAPID_SUBJECT=mailto:admin@formhook.com
"""

try:
    from pywebpush import webpush
    from py_vapid import Vapid
except ImportError:
    print("❌ Error: Required package not installed")
    print("\nPlease install pywebpush:")
    print("    pip install pywebpush")
    exit(1)


def generate_vapid_keys():
    """Generate VAPID keys for web push"""
    print("🔐 Generating VAPID keys for FormHook Push Notifications...")
    print("-" * 60)
    
    # Generate VAPID keys
    vapid = Vapid()
    vapid.generate_keys()
    
    # Get keys in the format needed
    private_key = vapid.private_key.decode('utf-8')
    public_key = vapid.public_key.decode('utf-8')
    
    print("\n✅ VAPID Keys Generated Successfully!")
    print("\n" + "=" * 60)
    print("Add these to your .env file:")
    print("=" * 60)
    print(f"\nVAPID_PUBLIC_KEY={public_key}")
    print(f"VAPID_PRIVATE_KEY={private_key}")
    print("VAPID_SUBJECT=mailto:admin@formhook.com")
    print("\n" + "=" * 60)
    
    print("\n📝 Notes:")
    print("  - Keep the PRIVATE key secret!")
    print("  - The PUBLIC key is shared with the frontend")
    print("  - Change VAPID_SUBJECT to your actual email")
    print("  - Add these keys to your Render environment variables")
    print("\n🚀 Your push notifications are ready to use!")


if __name__ == "__main__":
    generate_vapid_keys()
