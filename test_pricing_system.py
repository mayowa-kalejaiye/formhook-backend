#!/usr/bin/env python3
"""
FormHook Pricing System Test
----------------------------
Test script to validate the new pricing tiers, usage tracking, and validation system.
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
BEARER_TOKEN = "your-jwt-token-here"

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json"
}

def test_pricing_plans():
    """Test the public pricing plans endpoint."""
    print("Testing GET /subscription/plans (public endpoint)...")
    response = requests.get(f"{BASE_URL}/subscription/plans")
    
    if response.status_code == 200:
        plans = response.json()
        print("✅ Successfully retrieved pricing plans")
        print(f"Available plans: {', '.join(plans['plans'].keys())}")
        
        # Verify our new pricing structure
        expected_tiers = ['free', 'starter', 'professional', 'business', 'enterprise']
        for tier in expected_tiers:
            if tier in plans['plans']:
                plan = plans['plans'][tier]
                print(f"✓ {tier.title()}: {plan['name']} - ${plan['price_monthly']/100:.0f}/month")
                print(f"  └─ {plan['monthly_submissions']:,} submissions/month")
            else:
                print(f"✗ Missing tier: {tier}")
    else:
        print(f"✗ Failed with status {response.status_code}: {response.text}")


def test_current_subscription():
    """Test current user subscription info."""
    print("\nTesting GET /subscription/current (requires auth)...")
    response = requests.get(f"{BASE_URL}/subscription/current", headers=headers)
    
    if response.status_code == 200:
        sub_info = response.json()
        print("✅ Successfully retrieved subscription info")
        print(f"Current tier: {sub_info['tier']} ({sub_info['plan_name']})")
        print(f"Usage: {sub_info['usage_info']['submissions_used']}/{sub_info['usage_info']['submissions_limit']} submissions")
        print(f"Usage percentage: {sub_info['usage_info']['usage_percentage']:.1f}%")
        
        if sub_info['usage_info']['is_over_limit']:
            print(f"⚠️ Over limit! Overage cost: {sub_info['usage_info']['overage_cost_formatted']}")
    elif response.status_code == 401:
        print("⚠️ Authentication required - update BEARER_TOKEN")
    else:
        print(f"✗ Failed with status {response.status_code}: {response.text}")


def test_usage_stats():
    """Test usage statistics endpoint."""
    print("\nTesting GET /subscription/usage (requires auth)...")
    response = requests.get(f"{BASE_URL}/subscription/usage", headers=headers)
    
    if response.status_code == 200:
        usage = response.json()
        print("✅ Successfully retrieved usage statistics")
        print(f"Submissions remaining: {usage['submissions_remaining']:,}")
        print(f"Days until reset: {usage['days_remaining']}")
        print(f"Forms created: {usage['forms_count']}")
        
        if usage['upgrade_available']:
            print("💡 Upgrade options available")
    elif response.status_code == 401:
        print("⚠️ Authentication required - update BEARER_TOKEN")
    else:
        print(f"✗ Failed with status {response.status_code}: {response.text}")


def test_tier_recommendation():
    """Test AI-powered tier recommendation."""
    print("\nTesting GET /subscription/recommendation (requires auth)...")
    response = requests.get(f"{BASE_URL}/subscription/recommendation", headers=headers)
    
    if response.status_code == 200:
        recommendation = response.json()
        if recommendation:
            print("✅ Received tier recommendation")
            print(f"Recommendation: {recommendation['type']} to {recommendation['recommended_tier']}")
            print(f"Reason: {recommendation['reason']}")
            
            if recommendation['type'] == 'upgrade':
                print(f"Additional cost: {recommendation.get('monthly_cost', 'N/A')}")
            elif recommendation['type'] == 'downgrade':
                print(f"Monthly savings: {recommendation.get('monthly_savings', 'N/A')}")
        else:
            print("✅ No tier recommendation (current tier is optimal)")
    elif response.status_code == 401:
        print("⚠️ Authentication required - update BEARER_TOKEN")
    else:
        print(f"✗ Failed with status {response.status_code}: {response.text}")


def test_feature_validation():
    """Test feature access validation."""
    print("\nTesting POST /subscription/validate-feature (requires auth)...")
    
    # Test features that should exist
    features_to_test = [
        "basic_analytics",
        "advanced_analytics", 
        "webhooks",
        "white_label",
        "enterprise_analytics"
    ]
    
    for feature in features_to_test:
        response = requests.post(
            f"{BASE_URL}/subscription/validate-feature",
            params={"feature": feature},
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            access = "✅" if result['has_access'] else "❌"
            print(f"{access} {feature}: {'Available' if result['has_access'] else 'Requires upgrade'}")
        elif response.status_code == 401:
            print("⚠️ Authentication required - update BEARER_TOKEN")
            break
        else:
            print(f"✗ Failed to validate {feature}: {response.status_code}")


def test_upgrade_simulation():
    """Test subscription upgrade simulation."""
    print("\nTesting POST /subscription/upgrade (requires auth)...")
    
    upgrade_data = {
        "target_tier": "professional",
        "billing_cycle": "monthly"
    }
    
    response = requests.post(
        f"{BASE_URL}/subscription/upgrade",
        json=upgrade_data,
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Upgrade simulation successful")
        print(f"Upgrade from {result['current_tier']} to {result['target_tier']}")
        print(f"Price change: ${result['price_change']/100:.2f}/month")
        print("Next steps:")
        for step in result['next_steps']:
            print(f"  • {step}")
    elif response.status_code == 400:
        error = response.json()
        print(f"⚠️ Invalid upgrade: {error['detail']}")
    elif response.status_code == 401:
        print("⚠️ Authentication required - update BEARER_TOKEN")
    else:
        print(f"✗ Failed with status {response.status_code}: {response.text}")


if __name__ == "__main__":
    print("FormHook Pricing System Test")
    print("=" * 50)
    
    # Test public endpoints first
    test_pricing_plans()
    
    # Test authenticated endpoints
    if BEARER_TOKEN != "your-jwt-token-here":
        test_current_subscription()
        test_usage_stats() 
        test_tier_recommendation()
        test_feature_validation()
        test_upgrade_simulation()
    else:
        print("\n⚠️ To test authenticated endpoints, update BEARER_TOKEN with a valid JWT")
    
    print("\n" + "=" * 50)
    print("🎯 NEW PRICING TIERS IMPLEMENTED:")
    print("   • FREE: 100 submissions/month, 3 forms")
    print("   • STARTER: $9/month, 1,000 submissions")  
    print("   • PROFESSIONAL: $29/month, 10,000 submissions")
    print("   • BUSINESS: $99/month, 100,000 submissions")
    print("   • ENTERPRISE: $199/month+, 1M+ submissions")
    print()
    print("🔧 FEATURES ADDED:")
    print("   • Usage tracking and validation")
    print("   • Tier-based feature restrictions")
    print("   • Smart upgrade recommendations")
    print("   • Subscription management endpoints")
    print("   • Overage cost calculations")
    print()
    print("Test completed!")
