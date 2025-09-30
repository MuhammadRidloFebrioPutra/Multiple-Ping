"""
Debug script untuk mengecek setup WhatsApp
"""

import os
import sys

def main():
    print("🔍 WhatsApp Setup Debug")
    print("=" * 40)
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    print(f"Project root: {project_root}")
    
    # Check contacts.txt
    contacts_file = os.path.join(project_root, "contacts.txt")
    print(f"\n📋 Checking contacts file:")
    print(f"Path: {contacts_file}")
    print(f"Exists: {os.path.exists(contacts_file)}")
    
    if os.path.exists(contacts_file):
        try:
            with open(contacts_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"Lines in file: {len(lines)}")
            
            valid_contacts = 0
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(',', 1)
                if len(parts) == 2:
                    target, message = [part.strip() for part in parts]
                    if target and message:
                        valid_contacts += 1
                        print(f"  Line {line_num}: ✅ {target}")
                    else:
                        print(f"  Line {line_num}: ❌ Empty target/message")
                else:
                    print(f"  Line {line_num}: ❌ Invalid format")
            
            print(f"Valid contacts found: {valid_contacts}")
            
            if valid_contacts == 0:
                print("\n⚠️  No valid contacts found!")
                print("Expected format:")
                print("Group Name, Message for group")
                print("+628123456789, Message for contact")
                
        except Exception as e:
            print(f"❌ Error reading file: {e}")
    else:
        print("\n📝 Creating sample contacts.txt file...")
        try:
            sample_content = """# WhatsApp Contacts/Groups
# Format: target,message
# For groups: use group name
# For contacts: use phone number with country code (+628...)

IT Support Group, Alert from monitoring system
Network Team, Network monitoring alert
Security Team, Security monitoring alert"""
            
            with open(contacts_file, 'w', encoding='utf-8') as f:
                f.write(sample_content)
            print("✅ Sample contacts.txt created")
            print("Please edit the file with your actual group names or phone numbers")
        except Exception as e:
            print(f"❌ Error creating file: {e}")
    
    # Check Chrome profile directory
    chrome_profile = os.path.join(project_root, "chrome_profile")
    print(f"\n🌐 Chrome profile directory:")
    print(f"Path: {chrome_profile}")
    print(f"Exists: {os.path.exists(chrome_profile)}")
    
    if not os.path.exists(chrome_profile):
        print("Will be created automatically when WhatsApp service starts")
    
    # Check Chrome binary
    chrome_binary = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    print(f"\n💻 Chrome binary:")
    print(f"Path: {chrome_binary}")
    print(f"Exists: {os.path.exists(chrome_binary)}")
    
    if not os.path.exists(chrome_binary):
        print("⚠️  Chrome not found at default location")
        print("Please install Google Chrome or update the path in whatsapp.py")
    
    # Test WhatsApp service import
    print(f"\n🧪 Testing WhatsApp service import:")
    try:
        sys.path.append(project_root)
        from app.utils.whatsapp import load_contacts
        print("✅ WhatsApp service imported successfully")
        
        # Test load_contacts function
        contacts = load_contacts(contacts_file, "group")
        print(f"✅ load_contacts returned {len(contacts)} contacts")
        
        if len(contacts) == 0:
            print("⚠️  No contacts loaded - check contacts.txt format")
        
    except Exception as e:
        print(f"❌ Error importing WhatsApp service: {e}")
        print("Required packages: selenium, undetected-chromedriver, fake-useragent, pyperclip")
        print("Install with: pip install selenium undetected-chromedriver fake-useragent pyperclip webdriver-manager")

if __name__ == "__main__":
    main()
