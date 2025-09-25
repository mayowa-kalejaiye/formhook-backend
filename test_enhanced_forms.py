#!/usr/bin/env python3
"""
Quick test script to verify the enhanced form endpoints are working correctly.
This script assumes you have a running FormHook instance and valid credentials.
"""

import requests
import json
from datetime import datetime

# Configuration - update these values for your environment
BASE_URL = "http://localhost:8000"  # Adjust to your actual server URL
# You'll need to replace this with a valid bearer token from your system
BEARER_TOKEN = "your-jwt-token-here"

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json"
}

def test_list_forms():
    """Test the enhanced list forms endpoint"""
    print("Testing GET /forms/ (enhanced with metadata)...")
    response = requests.get(f"{BASE_URL}/forms/", headers=headers)
    
    if response.status_code == 200:
        forms = response.json()
        print(f"✓ Successfully retrieved {len(forms)} forms")
        
        if forms:
            # Check if metadata fields are present
            first_form = forms[0]
            metadata_fields = ['submission_count', 'recent_submissions', 'last_submission_at', 'status']
            
            for field in metadata_fields:
                if field in first_form:
                    print(f"✓ Metadata field '{field}' present: {first_form[field]}")
                else:
                    print(f"✗ Missing metadata field: {field}")
        else:
            print("ℹ No forms found")
    else:
        print(f"✗ Failed with status {response.status_code}: {response.text}")

def test_form_detail(form_id):
    """Test the enhanced form detail endpoint"""
    print(f"\nTesting GET /forms/{form_id} (enhanced with metadata)...")
    response = requests.get(f"{BASE_URL}/forms/{form_id}", headers=headers)
    
    if response.status_code == 200:
        form = response.json()
        print("✓ Successfully retrieved form details")
        
        # Check if metadata fields are present
        metadata_fields = ['submission_count', 'recent_submissions', 'last_submission_at', 'status']
        
        for field in metadata_fields:
            if field in form:
                print(f"✓ Metadata field '{field}' present: {form[field]}")
            else:
                print(f"✗ Missing metadata field: {field}")
                
        # Show basic form info
        print(f"Form Name: {form.get('name', 'N/A')}")
        print(f"Total Submissions: {form.get('submission_count', 0)}")
        print(f"Recent Submissions (7 days): {form.get('recent_submissions', 0)}")
        
    elif response.status_code == 404:
        print("✗ Form not found (check if form_id exists and belongs to user)")
    else:
        print(f"✗ Failed with status {response.status_code}: {response.text}")

def test_public_form(form_id):
    """Test the new public form endpoint (no authentication required)"""
    print(f"\nTesting GET /forms/public/{form_id} (public endpoint - NO AUTH)...")
    
    # Note: No authorization header needed for public endpoint
    public_headers = {"Content-Type": "application/json"}
    response = requests.get(f"{BASE_URL}/forms/public/{form_id}", headers=public_headers)
    
    if response.status_code == 200:
        form = response.json()
        print("✅ Successfully retrieved public form structure")
        
        # Check that only public fields are present
        public_fields = ['id', 'name', 'description', 'fields']
        private_fields = ['webhook_url', 'webhook_secret', 'api_token', 'user_id', 'submission_count']
        
        for field in public_fields:
            if field in form:
                print(f"✓ Public field '{field}' present: {form[field] if field != 'fields' else f'{len(form[field])} fields'}")
            else:
                print(f"✗ Missing public field: {field}")
        
        for field in private_fields:
            if field not in form:
                print(f"✓ Private field '{field}' correctly excluded")
            else:
                print(f"⚠ WARNING: Private field '{field}' exposed in public endpoint!")
        
        # Show form structure
        print(f"\nForm Structure:")
        print(f"  Name: {form.get('name', 'N/A')}")
        print(f"  Description: {form.get('description', 'None')}")
        print(f"  Fields: {len(form.get('fields', []))} custom fields defined")
        
        if form.get('fields'):
            print("  Field details:")
            for i, field in enumerate(form['fields']):
                print(f"    {i+1}. {field.get('label', 'Unlabeled')} ({field.get('type', 'unknown')}) - {'Required' if field.get('required') else 'Optional'}")
        
    elif response.status_code == 404:
        print("✗ Form not found (check if form_id exists)")
    else:
        print(f"✗ Failed with status {response.status_code}: {response.text}")

if __name__ == "__main__":
    print("FormHook Enhanced Forms API Test")
    print("=" * 40)
    
    print("⚠ IMPORTANT: Update BEARER_TOKEN variable with a valid JWT token before running!")
    print("⚠ For public form test, also update FORM_ID_TO_TEST variable with a real form ID")
    
    # Test list forms (requires auth)
    test_list_forms()
    
    # For testing form detail, you'll need to provide a valid form ID
    # Uncomment and update the line below with a real form ID from your system
    # test_form_detail("your-form-id-here")
    
    # Test the new public endpoint (NO AUTH REQUIRED)
    # Replace with an actual form ID from your database
    FORM_ID_TO_TEST = "your-form-id-here"
    if FORM_ID_TO_TEST != "your-form-id-here":
        test_public_form(FORM_ID_TO_TEST)
    else:
        print("\n📝 To test the public endpoint, update FORM_ID_TO_TEST with a real form ID")
    
    print("\n" + "=" * 40)
    print("Test completed!")
    print("\n🎉 NEW PUBLIC ENDPOINT ADDED:")
    print(f"   GET {BASE_URL}/forms/public/{{form_id}}")
    print("   • No authentication required")
    print("   • Returns form structure for public form rendering")
    print("   • Only includes: id, name, description, fields")
    print("   • Excludes sensitive data: webhook URLs, API tokens, user info")
