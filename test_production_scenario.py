#!/usr/bin/env python3
"""
Test script to simulate production scenario where ping_results changes between cycles
This simulates the real issue where run.py sends different devices in each cycle
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
        return {}
    
    data = {}
    with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data[row['ip_address']] = row
    return data

def main():
    print("="*80)
    print("🧪 PRODUCTION SCENARIO TEST - Multiple Devices, Different Ping Cycles")
    print("="*80)
    print()
    
    # Initialize config and tracker
    config = Config()
    tracker = TimeoutTracker(config)
    
    csv_path = tracker.timeout_csv_path
    print(f"📁 CSV Path: {csv_path}")
    print()
    
    # Multiple test devices
    device_a = {
        'ip_address': '10.88.88.1',
        'hostname': 'DEVICE_A',
        'device_id': '8881',
        'merk': 'Test',
        'os': '',
        'kondisi': 'baik',
        'ping_success': False
    }
    
    device_b = {
        'ip_address': '10.88.88.2',
        'hostname': 'DEVICE_B',
        'device_id': '8882',
        'merk': 'Test',
        'os': '',
        'kondisi': 'baik',
        'ping_success': False
    }
    
    device_c = {
        'ip_address': '10.88.88.3',
        'hostname': 'DEVICE_C',
        'device_id': '8883',
        'merk': 'Test',
        'os': '',
        'kondisi': 'baik',
        'ping_success': False
    }
    
    print("🎯 Test Scenario:")
    print("   - 3 devices (A, B, C) are failing")
    print("   - Each cycle pings different combinations")
    print("   - Simulates production where not all devices pinged every cycle")
    print()
    
    # Clean up
    print("🧹 Cleaning up previous test data...")
    timeout_data = tracker._read_timeout_data()
    for ip in ['10.88.88.1', '10.88.88.2', '10.88.88.3']:
        if ip in timeout_data:
            del timeout_data[ip]
    tracker._write_timeout_data(timeout_data)
    print("   ✅ Cleanup done")
    print()
    
    # Simulate 8 cycles with different device combinations
    cycles = [
        # Cycle 1: All 3 devices ping
        ([device_a, device_b, device_c], "All 3 devices", {"A": 1, "B": 1, "C": 1}),
        
        # Cycle 2: Only A and B pinged (C not in ping_results!)
        ([device_a, device_b], "Only A and B", {"A": 2, "B": 2, "C": 1}),
        
        # Cycle 3: Only B and C pinged (A not in ping_results!)
        ([device_b, device_c], "Only B and C", {"A": 2, "B": 3, "C": 2}),
        
        # Cycle 4: Only A pinged (B and C not in ping_results!)
        ([device_a], "Only A", {"A": 3, "B": 3, "C": 2}),
        
        # Cycle 5: All 3 again
        ([device_a, device_b, device_c], "All 3 devices", {"A": 4, "B": 4, "C": 3}),
        
        # Cycle 6: Only C pinged (A and B not in ping_results!)
        ([device_c], "Only C", {"A": 4, "B": 4, "C": 4}),
        
        # Cycle 7: Only B pinged
        ([device_b], "Only B", {"A": 4, "B": 5, "C": 4}),
        
        # Cycle 8: All 3 again
        ([device_a, device_b, device_c], "All 3 devices", {"A": 5, "B": 6, "C": 5}),
    ]
    
    all_passed = True
    
    for cycle_num, (ping_results, description, expected_counts) in enumerate(cycles, 1):
        print(f"{'='*80}")
        print(f"🔄 CYCLE {cycle_num}/8: {description}")
        print(f"{'='*80}")
        
        # Show which devices in this ping
        pinged_ips = [d['ip_address'] for d in ping_results]
        print(f"📤 Ping results contain: {', '.join([d['hostname'] for d in ping_results])}")
        
        # Call update
        tracker.update_timeout_tracking(ping_results)
        
        # Verify
        print(f"\n📊 Verification:")
        timeout_data = read_timeout_csv(csv_path)
        
        cycle_passed = True
        for device_key, expected_count in expected_counts.items():
            ip = f"10.88.88.{['A', 'B', 'C'].index(device_key) + 1}"
            
            if ip in timeout_data:
                actual_count = int(timeout_data[ip].get('consecutive_timeouts', 0))
                status = "✅" if actual_count == expected_count else "❌"
                
                if actual_count != expected_count:
                    cycle_passed = False
                    all_passed = False
                
                print(f"   {status} Device {device_key}: {actual_count}x (expected: {expected_count}x)")
            else:
                print(f"   ❌ Device {device_key}: NOT FOUND (expected: {expected_count}x)")
                cycle_passed = False
                all_passed = False
        
        if not cycle_passed:
            print(f"\n   🐛 BUG DETECTED in Cycle {cycle_num}!")
            print(f"   📋 Devices NOT in ping_results should be PRESERVED with same count!")
        
        print()
        time.sleep(0.5)
    
    # Final verification
    print("="*80)
    print("🎯 FINAL VERIFICATION")
    print("="*80)
    
    final_data = read_timeout_csv(csv_path)
    
    print(f"\n📊 Final State:")
    for device_key in ['A', 'B', 'C']:
        ip = f"10.88.88.{['A', 'B', 'C'].index(device_key) + 1}"
        if ip in final_data:
            count = final_data[ip].get('consecutive_timeouts', '0')
            hostname = final_data[ip].get('hostname', ip)
            print(f"   • {hostname} ({ip}): {count}x")
        else:
            print(f"   • Device {device_key} ({ip}): NOT FOUND")
    
    print()
    
    if all_passed:
        print("="*80)
        print("✅ TEST PASSED! All devices preserved correctly!")
        print("="*80)
        print()
        print("✨ Key validation:")
        print("   ✅ Devices NOT in ping_results are PRESERVED")
        print("   ✅ Counters don't reset when device not pinged")
        print("   ✅ Each device increments independently")
        return True
    else:
        print("="*80)
        print("❌ TEST FAILED! Device preservation issue detected!")
        print("="*80)
        print()
        print("🔍 Issue:")
        print("   Devices not in ping_results were removed or reset")
        print("   This causes counters to reset in production!")
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
