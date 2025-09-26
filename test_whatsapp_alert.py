"""
Test script untuk WhatsApp alert endpoint
"""

import requests
import json

def test_whatsapp_alert():
    print("🧪 Testing WhatsApp Alert Endpoint")
    print("=" * 40)
    
    # Test the alert endpoint
    url = "http://localhost:5000/alert"
    params = {"id": "CCTV-1"}
    
    try:
        print(f"Sending request to: {url}")
        print(f"Parameters: {params}")
        
        response = requests.get(url, params=params, timeout=30)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"Response JSON:")
            print(json.dumps(response_json, indent=2))
            
            if response_json.get('status') == 'error':
                print(f"\n❌ Error: {response_json.get('message')}")
                
                if 'No valid contacts' in response_json.get('message', ''):
                    print("\n💡 Solutions:")
                    print("1. Check if contacts.txt exists in project root")
                    print("2. Verify contacts.txt format: 'Group Name, Message'")
                    print("3. Run: python check_whatsapp_setup.py")
            else:
                print(f"\n✅ Request successful!")
                
        except json.JSONDecodeError:
            print(f"Response Text: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the Flask app running?")
        print("Start with: python app/utils/whatsapp.py")
    except requests.exceptions.Timeout:
        print("❌ Request timeout")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_whatsapp_alert()
