#!/usr/bin/env python3
"""
Quick test script for the Twilio SMS API
"""

import requests
import json

# Server URL
BASE_URL = "http://localhost:5000"

def test_health():
    """Test the health endpoint"""
    print("🏥 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_sms_simulation():
    """Test the SMS simulation endpoint (doesn't actually send)"""
    print("\n📱 Testing SMS simulation...")
    data = {
        "to": "+16475752697",
        "message": "Hello from Flask + Twilio test!"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/test-sms",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ SMS simulation failed: {e}")
        return False

def test_real_sms():
    """Test sending a real SMS to your phone number"""
    print("\n📨 Testing real SMS to +1 (647) 575-2697...")
    
    # Ask for confirmation before sending real SMS
    confirm = input("Send a real SMS to your phone? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("⏭️  Skipping real SMS test")
        return True
    
    data = {
        "to": "+16475752697",
        "message": "Hello! This is a test SMS from your Flask + Twilio app! 🚀"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/send-sms",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ SMS sent successfully! Check your phone!")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Real SMS test failed: {e}")
        return False

def send_custom_sms():
    """Send a custom SMS message"""
    print("\n✏️  Send Custom SMS")
    print("-" * 30)
    
    # Get custom message
    message = input("Enter your message: ").strip()
    
    if not message:
        print("❌ No message entered")
        return False
    
    data = {
        "to": "+16475752697",
        "message": message
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/send-sms",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Custom SMS sent successfully!")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Custom SMS failed: {e}")
        return False

def main():
    print("🧪 Twilio SMS API Test Suite")
    print(f"📱 Your phone: +1 (647) 575-2697")
    print("=" * 50)
    
    # Test 1: Health check
    health_ok = test_health()
    
    if not health_ok:
        print("❌ Server not responding. Make sure Flask is running on localhost:5000")
        return
    
    # Test 2: SMS simulation
    sim_ok = test_sms_simulation()
    
    # Test 3: Real SMS (optional)
    real_ok = test_real_sms()
    
    # Test 4: Custom SMS (optional)
    if real_ok:
        custom_ok = True
        while True:
            send_another = input("\nSend another custom SMS? (y/n): ").strip().lower()
            if send_another == 'y':
                custom_ok = send_custom_sms() and custom_ok
            else:
                break
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Health Check: {'✅' if health_ok else '❌'}")
    print(f"SMS Simulation: {'✅' if sim_ok else '❌'}")
    print(f"Real SMS: {'✅' if real_ok else '❌'}")
    
    if all([health_ok, sim_ok]):
        print("\n🎉 All tests passed! Your Twilio SMS API is working!")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
