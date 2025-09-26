from flask import request, jsonify
import time
import random
import numpy as np
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
from undetected_chromedriver import Chrome, ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager
import logging
import os
import re
import pyperclip
import atexit
import threading
import csv
from datetime import datetime
from typing import Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global WebDriver instance
driver = None

# Function to set up profile directory
def setup_profile_directory(profile_path):
    try:
        profile_path = os.path.abspath(profile_path)
        if os.path.exists(profile_path):
            lock_file = os.path.join(profile_path, 'SingletonLock')
            if os.path.exists(lock_file):
                os.remove(lock_file)
                logging.info(f"Removed SingletonLock from {profile_path}")
        else:
            os.makedirs(profile_path, exist_ok=True)
            logging.info(f"Created profile directory: {profile_path}")
        if os.name == 'nt':
            os.system(f'icacls "{profile_path}" /grant Users:F /T')
        logging.info(f"Profile directory set up: {profile_path}")
        return profile_path
    except Exception as e:
        logging.error(f"Failed to set up profile directory: {e}")
        return None

# Function to validate phone number
def is_valid_phone_number(phone_number):
    pattern = r'^\+\d{9,15}$'
    return bool(re.match(pattern, phone_number))

# Function to load contacts from a file
def load_contacts(file_path, type_):
    contacts = []
    try:
        # Make file path absolute if it's relative
        if not os.path.isabs(file_path):
            # Look in the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            file_path = os.path.join(project_root, file_path)
        
        logging.info(f"Looking for contacts file at: {file_path}")
        
        if not os.path.exists(file_path):
            logging.error(f"Contacts file {file_path} does not exist")
            logging.info(f"Please create the file with format: 'target,message' per line")
            return []
            
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                try:
                    line = line.strip()
                    if not line or line.startswith('#'):  # Skip empty lines and comments
                        continue
                    parts = line.split(',', 1)
                    if len(parts) != 2:
                        logging.error(f"Invalid line format in {file_path} at line {line_num}: {line}")
                        continue
                    target, message = [part.strip() for part in parts]
                    if not target or not message:
                        logging.error(f"Empty target or message in {file_path} at line {line_num}: {line}")
                        continue
                    if type_ == 'contact' and not is_valid_phone_number(target):
                        logging.warning(f"Invalid phone number format at line {line_num}: {target}")
                        continue
                    contacts.append((target, message))
                    logging.info(f"Valid {type_} loaded: {target}")
                except ValueError as e:
                    logging.error(f"Invalid line format in {file_path} at line {line_num}: {line} ({e})")
        logging.info(f"Loaded {len(contacts)} valid entries from {file_path}")
        return contacts
    except Exception as e:
        logging.error(f"Error loading contacts from {file_path}: {e}")
        return []

# Function to simulate human-like typing
def human_typing(element, text):
    lines = text.split('|')
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        for char in line:
            element.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
        if i < len(lines) - 1:
            element.send_keys(Keys.SHIFT + Keys.ENTER)
            logging.info("Inserted line break with Shift+Enter")
            time.sleep(random.uniform(0.1, 0.3))

# Function to paste message
def paste_message(element, text):
    try:
        # Remove extra whitespace and ensure consistent formatting
        cleaned_text = text.strip()
        # Copy the entire text to clipboard
        pyperclip.copy(cleaned_text)
        # Paste the text using Ctrl+V
        element.send_keys(Keys.CONTROL, 'v')
        logging.info(f"Pasted full message: {cleaned_text}")
        # time.sleep(random.uniform(0.1, 0.3))
    except Exception as e:
        logging.error(f"Failed to paste message: {e}")

# Function to simulate mouse movement
def simulate_mouse_movement(driver):
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # time.sleep(random.uniform(0.5, 1.5))
        driver.execute_script("window.scrollTo(0, 0);")
    except Exception as e:
        logging.warning(f"Mouse movement simulation failed: {e}")

# Function to save session
def save_session(driver):
    try:
        driver.get("https://web.whatsapp.com")
        time.sleep(random.uniform(1, 2))
        logging.info("Session saved by navigating to main page")
    except Exception as e:
        logging.error(f"Failed to save session: {e}")

# Function to periodically save session
def periodic_save_session():
    global driver
    while True:
        if driver is not None:
            try:
                save_session(driver)
            except Exception as e:
                logging.error(f"Periodic session save failed: {e}")
        # Sleep for a random interval between 5 and 7 minutes (300 to 420 seconds)
        time.sleep(random.uniform(300, 420))

# Function to search for a contact
def search_contact(driver, phone_number):
    try:
        search_box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//div[@aria-placeholder="Search or start a new chat"]'))
        )
        search_box.click()
        time.sleep(random.uniform(0.5, 1))
        search_box.send_keys(Keys.CONTROL + "a")
        search_box.send_keys(Keys.DELETE)
        time.sleep(random.uniform(0.3, 0.7))
        for char in phone_number:
            search_box.send_keys(char)
            time.sleep(random.uniform(0.05, 0.2))
        time.sleep(random.uniform(1, 2))
        search_box.send_keys(Keys.ENTER)
        logging.info(f"Searched for contact: {phone_number}")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//div[@aria-placeholder="Type a message"]'))
        )
        logging.info(f"Chat opened for {phone_number}")
        return True
    except Exception as e:
        logging.error(f"Failed to search for {phone_number}: {e}")
        return False

# Function to search for a group
def search_group(driver, group_name):
    try:
        search_box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//div[@aria-placeholder="Search or start a new chat"]'))
        )
        search_box.click()
        # time.sleep(random.uniform(0.5, 1))
        search_box.send_keys(Keys.CONTROL + "a")
        search_box.send_keys(Keys.DELETE)
        # time.sleep(random.uniform(0.3, 0.7))
        for char in group_name:
            search_box.send_keys(char)
            # time.sleep(random.uniform(0.05, 0.2))
        # time.sleep(random.uniform(1, 2))
        search_box.send_keys(Keys.ENTER)
        logging.info(f"Searched for group: {group_name}")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//div[@aria-placeholder="Type a message"]'))
        )
        logging.info(f"Group chat opened for {group_name}")
        return True
    except Exception as e:
        logging.error(f"Failed to search for group {group_name}: {e}")
        return False

# Function to initialize the WebDriver
def initialize_driver(profile_path, proxy=None, chrome_binary=None):
    global driver
    if driver is not None:
        logging.info("Using existing WebDriver instance")
        return driver

    profile_path = setup_profile_directory(profile_path)
    if not profile_path:
        raise Exception("Failed to set up profile directory")

    desktop_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.88 Safari/537.36",
    ]

    user_agent = random.choice(desktop_agents)
    logging.info(f"Using Desktop User-Agent: {user_agent}")

    chrome_options = ChromeOptions()
    chrome_options.add_argument(f'--user-agent={user_agent}')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument(f'--window-size={1920},{1080}')
    chrome_options.add_argument(f'--user-data-dir={profile_path}')
    chrome_options.add_argument("--force-device-scale-factor=1")
    chrome_options.add_argument("--high-dpi-support=1")

    if chrome_binary and os.path.exists(chrome_binary):
        chrome_options.binary_location = chrome_binary
        logging.info(f"Using Chrome binary: {chrome_binary}")
    if proxy:
        chrome_options.add_argument(f'--proxy-server={proxy}')
        logging.info(f"Using proxy: {proxy}")

    driver = Chrome(options=chrome_options, executable_path=ChromeDriverManager().install())
    logging.info("Browser initialized successfully")
    driver.get("https://web.whatsapp.com")
    logging.info("Navigated to WhatsApp Web")

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[@aria-placeholder="Search or start a new chat"]'))
        )
        logging.info("Already logged in, session persisted")
    except:
        logging.info("Please scan the QR code with your WhatsApp mobile app.")
        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, '//div[@aria-placeholder="Search or start a new chat"]'))
            )
        except:
            logging.warning("Primary search bar XPath failed, trying fallback")
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, '//div[@aria-placeholder="Search or start a new chat"]'))
            )
        logging.info("Logged in successfully via QR code")

    return driver

# Function to close the WebDriver
def close_driver():
    global driver
    if driver:
        driver.quit()
        logging.info("Browser closed")
        driver = None

# Register close_driver to run when the application exits
atexit.register(close_driver)

# Function to send WhatsApp messages
def send_whatsapp_messages(cctv_id, contacts_file, type_="group", method="computer", profile_path="chrome_profile", proxy=None, chrome_binary=None, max_retries=3):
    if type_ not in ['contact', 'group']:
        return {"status": "error", "message": f"Invalid type: {type_}. Must be 'contact' or 'group'."}
    if method not in ['human', 'computer']:
        return {"status": "error", "message": f"Invalid method: {method}. Must be 'human' or 'computer'."}

    retry_count = 0
    while retry_count < max_retries:
        try:
            global driver
            driver = initialize_driver(profile_path, proxy, chrome_binary)

            current_url = driver.current_url
            if "/mobile" in current_url:
                logging.warning(f"Mobile redirect detected on attempt {retry_count + 1}. Restarting...")
                close_driver()
                retry_count += 1
                time.sleep(random.uniform(5, 10))
                continue

            contacts = load_contacts(contacts_file, type_)
            if not contacts:
                return {"status": "error", "message": "No valid contacts or groups loaded"}

            results = []
            for target, base_message in contacts:
                # Check if this is a timeout alert (contains TIMEOUT- prefix)
                if cctv_id.startswith('TIMEOUT-'):
                    # Parse timeout alert data
                    parts = cctv_id.replace('TIMEOUT-', '').split('-', 1)
                    device_id = parts[0] if len(parts) > 0 else 'Unknown'
                    ip_address = parts[1] if len(parts) > 1 else 'Unknown'
                    
                    # Get device data from timeout tracking
                    device_data = get_timeout_device_data(ip_address)
                    
                    alert_message = f"""🚨 DEVICE TIMEOUT ALERT 🚨

⚠️ CRITICAL: Device Tidak Dapat Dijangkau!

📍 Device Information:
• IP Address: {device_data.get('ip_address', ip_address)}
• Hostname: {device_data.get('hostname', 'Unknown')}
• Device ID: {device_data.get('device_id', device_id)}
• Brand/Model: {device_data.get('merk', 'Unknown')}
• Status: {device_data.get('kondisi', 'Unknown')}

⏰ Timeout Details:
• Consecutive Timeouts: {device_data.get('consecutive_timeouts', 'Unknown')}
• First Timeout: {format_datetime(device_data.get('first_timeout', 'Unknown'))}
• Last Check: {format_datetime(device_data.get('last_timeout', 'Unknown'))}

🔧 Action Required:
1. Check device power and network connection
2. Verify network connectivity to {ip_address}
3. Physical inspection may be required
4. Contact technical support if issue persists

Alert Time: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} WIB

This is an automated alert from Pelindo Monitoring System."""
                else:
                    # Default sensor alert message
                    alert_message = f"""🚨 CCTV-{cctv_id} ALERT 🚨

Status: firing
Open at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} WIB
Close at: -
Duration: -
Annotations:

🚨 Digital Sensor Alert!

* Device: ENVIROMUX-16D
* Location: DC Pelindo Surabaya
* Sensor: Water Leak - PAC #2
* Condition: Anomaly Detected

summary :
Sensor Detected : Anomaly Detected"""

                logging.info(f"Processing {type_}: {target}")
                for attempt in range(3):
                    try:
                        if type_ == 'contact':
                            if not search_contact(driver, target):
                                results.append({"target": target, "status": "failed", "error": f"Failed to open chat for contact {target}"})
                                break
                        elif type_ == 'group':
                            if not search_group(driver, target):
                                results.append({"target": target, "status": "failed", "error": f"Failed to open chat for group {target}"})
                                break

                        message_box = WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.XPATH, '//div[@aria-placeholder="Type a message"]'))
                        )
                        logging.info(f"Message box located for {target}")

                        simulate_mouse_movement(driver)
                        if method == 'human':
                            human_typing(message_box, alert_message)
                        else:
                            paste_message(message_box, alert_message)
                        message_box.send_keys(Keys.ENTER)
                        logging.info(f"Message sent to {type_} {target} using {method} method")
                        results.append({"target": target, "status": "success"})
                        break
                    except Exception as e:
                        logging.error(f"Attempt {attempt + 1} failed for {type_} {target}: {e}")
                        if attempt == 2:
                            results.append({"target": target, "status": "failed", "error": str(e)})

            return {"status": "success", "results": results}

        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return {"status": "error", "message": str(e)}

        retry_count += 1
        if retry_count < max_retries:
            logging.info(f"Retrying program (attempt {retry_count + 1}/{max_retries})")

    return {"status": "error", "message": f"Failed to avoid mobile redirect after {max_retries} attempts"}

def get_timeout_device_data(ip_address: str) -> Dict:
    """Get device data from timeout tracking CSV"""
    try:
        from config import Config
        config = Config()
        timeout_dir = getattr(config, 'CSV_OUTPUT_DIR', 'ping_results')
        timeout_csv_path = os.path.join(timeout_dir, 'timeout_tracking.csv')
        
        if not os.path.exists(timeout_csv_path):
            return {}
        
        with open(timeout_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row['ip_address'] == ip_address:
                    return dict(row)
        
        return {}
    except Exception as e:
        logging.error(f"Error getting timeout device data: {e}")
        return {}

def format_datetime(datetime_str: str) -> str:
    """Format datetime string for better readability"""
    try:
        if not datetime_str or datetime_str == 'Unknown':
            return 'Unknown'
        dt = datetime.fromisoformat(datetime_str)
        return dt.strftime('%d-%m-%Y %H:%M:%S')
    except:
        return datetime_str

# Start periodic session saving in a background thread
def start_periodic_session_saver():
    session_thread = threading.Thread(target=periodic_save_session, daemon=True)
    session_thread.start()
    logging.info("Started periodic session saver thread")