#!/usr/bin/env python3
"""
Test script to verify timeout counter increments correctly
This simulates multiple ping cycles with the same failing device
"""

import os
import sys
import csv
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from app.utils.timeout_tracker import TimeoutTracker

def read_timeout_csv(csv_path):
    """Read and display timeout tracking CSV"""
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        return {}
    
    data = {}
    with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data[row['ip_address']] = row
    return data

def display_timeout_data(data):
    """Display timeout data in formatted table"""
    if not data:
        print("   (No timeout data)")
        return
    
    print(f"   {'IP Address':<15} {'Hostname':<25} {'Count':<6} {'First Timeout':<20}")
    print(f"   {'-'*15} {'-'*25} {'-'*6} {'-'*20}")
    
    for ip, entry in sorted(data.items(), key=lambda x: int(x[1].get('consecutive_timeouts', 0)), reverse=True):
        count = entry.get('consecutive_timeouts', '0')
        hostname = entry.get('hostname', 'Unknown')[:25]
        first_timeout = entry.get('first_timeout', '')[:20]
        print(f"   {ip:<15} {hostname:<25} {count:<6} {first_timeout:<20}")

def main():
    print("="*80)
    print("🧪 TIMEOUT COUNTER TEST")
    print("="*80)
    print()
    
    # Initialize config and tracker
    config = Config()
    tracker = TimeoutTracker(config)
    
    csv_path = tracker.timeout_csv_path
    print(f"📁 CSV Path: {csv_path}")
    print()
    
    # Test device
    test_device = {
        'ip_address': '10.99.99.99',
        'hostname': 'TEST_DEVICE_COUNTER',
        'device_id': '9999',
        'merk': 'Test Brand',
        'os': '',
        'kondisi': 'baik',
        'ping_success': False  # Device is failing
    }
    
    print("🎯 Test Scenario: Same device fails 5 times in a row")
    print(f"   Device: {test_device['hostname']} ({test_device['ip_address']})")
    print()
    
    # Clean up test device if exists
    print("🧹 Cleaning up previous test data...")
    timeout_data = tracker._read_timeout_data()
    if test_device['ip_address'] in timeout_data:
        del timeout_data[test_device['ip_address']]
        tracker._write_timeout_data(timeout_data)
        print("   ✅ Previous test data removed")
    else:
        print("   ℹ️  No previous test data")
    print()
    
    # Simulate 5 consecutive ping failures
    num_cycles = 5
    
    for cycle in range(1, num_cycles + 1):
        print(f"{'='*80}")
        print(f"🔄 CYCLE {cycle}/{num_cycles}")
        print(f"{'='*80}")
        
        # Simulate ping result
        ping_results = [test_device.copy()]
        
        print(f"📤 Calling update_timeout_tracking() with 1 failed device...")
        tracker.update_timeout_tracking(ping_results)
        
        # Read and display current state
        print(f"\n📊 Current State After Cycle {cycle}:")
        timeout_data = read_timeout_csv(csv_path)
        display_timeout_data(timeout_data)
        
        if test_device['ip_address'] in timeout_data:
            actual_count = int(timeout_data[test_device['ip_address']].get('consecutive_timeouts', 0))
            expected_count = cycle
            
            if actual_count == expected_count:
                print(f"\n   ✅ CORRECT: Counter = {actual_count} (expected: {expected_count})")
            else:
                print(f"\n   ❌ ERROR: Counter = {actual_count} (expected: {expected_count})")
                print(f"      🐛 BUG DETECTED! Counter should increment but it doesn't!")
        else:
            print(f"\n   ❌ ERROR: Test device not found in timeout_data!")
            print(f"      🐛 BUG: Device was removed or not added!")
        
        print()
        
        if cycle < num_cycles:
            print("⏳ Waiting 1 second before next cycle...")
            time.sleep(1)
            print()
    
    # Final verification
    print("="*80)
    print("🎯 FINAL VERIFICATION")
    print("="*80)
    
    final_data = read_timeout_csv(csv_path)
    
    if test_device['ip_address'] in final_data:
        final_count = int(final_data[test_device['ip_address']].get('consecutive_timeouts', 0))
        
        print(f"\n✨ Test device final count: {final_count}")
        print(f"✨ Expected count: {num_cycles}")
        
        if final_count == num_cycles:
            print(f"\n{'='*80}")
            print("✅ TEST PASSED! Counter increments correctly!")
            print(f"{'='*80}")
            return True
        else:
            print(f"\n{'='*80}")
            print(f"❌ TEST FAILED! Counter stuck at {final_count} (expected: {num_cycles})")
            print(f"{'='*80}")
            
            # Show possible causes
            print("\n🔍 Possible causes:")
            print("   1. Race condition - multiple processes writing simultaneously")
            print("   2. Stale IP removal - device removed between cycles")
            print("   3. File locking issue - data not persisted properly")
            print("   4. Logic error - counter reset in update logic")
            return False
    else:
        print(f"\n{'='*80}")
        print("❌ TEST FAILED! Test device disappeared from tracking!")
        print(f"{'='*80}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
