#!/usr/bin/env python3
"""
Test script for Admin API endpoints
Demonstrates how to use the admin API for automated testing
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8080")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

if not ADMIN_TOKEN:
    print("❌ ADMIN_TOKEN not set in environment")
    print("Add it to your .env file: ADMIN_TOKEN=your_token_here")
    exit(1)

# Headers for admin requests
headers = {
    "X-Admin-Token": ADMIN_TOKEN,
    "Content-Type": "application/json"
}


def print_section(title):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_admin_health():
    """Test admin health endpoint"""
    print_section("Test 1: Admin Health Check")
    
    response = requests.get(f"{BASE_URL}/admin/health", headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        print("✅ Admin API is working!")
    else:
        print("❌ Admin API failed!")
        exit(1)


def test_create_test_users():
    """Create test driver and hitchhiker"""
    print_section("Test 2: Create Test Users")
    
    # Create test driver
    driver_data = {
        "phone_number": "test_driver_001",
        "role": "driver",
        "driver_data": {
            "origin": "גברעם",
            "destination": "תל אביב",
            "days": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
            "departure_time": "09:00",
            "return_time": "17:30",
            "available_seats": 3,
            "notes": "Test driver - automated testing"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/admin/users",
        headers=headers,
        json=driver_data
    )
    
    print(f"\n📝 Creating test driver...")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Create test hitchhiker
    hitchhiker_data = {
        "phone_number": "test_hitchhiker_001",
        "role": "hitchhiker",
        "hitchhiker_data": {
            "origin": "גברעם",
            "destination": "תל אביב",
            "travel_date": "2025-01-15",
            "departure_time": "09:00",
            "flexibility": "flexible",
            "notes": "Test hitchhiker - automated testing"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/admin/users",
        headers=headers,
        json=hitchhiker_data
    )
    
    print(f"\n📝 Creating test hitchhiker...")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")


def test_list_users():
    """List all users"""
    print_section("Test 3: List All Users")
    
    response = requests.get(f"{BASE_URL}/users", headers=headers)
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    print(f"\nTotal users: {data.get('count', 0)}")
    
    for user in data.get('users', [])[:5]:  # Show first 5
        print(f"  - {user['phone_number']}: {user.get('role', 'no role')}")
    
    if data.get('count', 0) > 5:
        print(f"  ... and {data['count'] - 5} more")


def test_change_phone_number():
    """Test changing phone number"""
    print_section("Test 4: Change Phone Number")
    
    response = requests.post(
        f"{BASE_URL}/admin/users/test_driver_001/change-phone",
        headers=headers,
        params={"new_phone": "driver_renamed"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        print("✅ Phone number changed successfully!")


def test_get_user_details():
    """Get details of specific user"""
    print_section("Test 5: Get User Details")
    
    response = requests.get(
        f"{BASE_URL}/user/driver_renamed",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nUser: {data['phone_number']}")
        print(f"Role: {data.get('role', 'no role')}")
        print(f"Driver data: {data.get('driver_data', {})}")


def test_cleanup():
    """Clean up test users"""
    print_section("Test 6: Cleanup Test Users")
    
    test_users = [
        "driver_renamed",
        "test_driver_001",
        "test_hitchhiker_001"
    ]
    
    for user in test_users:
        response = requests.delete(
            f"{BASE_URL}/admin/users/{user}",
            headers=headers
        )
        
        if response.status_code == 200:
            print(f"✅ Deleted: {user}")
        elif response.status_code == 404:
            print(f"⏭️  Skipped: {user} (not found)")
        else:
            print(f"❌ Failed to delete: {user}")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  🧪 Admin API Test Suite")
    print("="*60)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Admin Token: {'*' * len(ADMIN_TOKEN[:4]) + ADMIN_TOKEN[-4:]}")
    
    try:
        test_admin_health()
        test_create_test_users()
        test_list_users()
        test_change_phone_number()
        test_get_user_details()
        test_cleanup()
        
        print("\n" + "="*60)
        print("  ✅ All tests completed successfully!")
        print("="*60 + "\n")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        print("Running cleanup...")
        test_cleanup()
    
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
        print("Running cleanup...")
        test_cleanup()
        exit(1)


if __name__ == "__main__":
    main()

