#!/usr/bin/env python3
"""
Test script for the updated /camera/generate-demo-video API
Tests both use_existing_data=false and use_existing_data=true scenarios
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:8000"

def test_generate_new_video():
    """Test video generation with use_existing_data=false (default)"""
    print("\n🎬 Test 1: Generate video with NEW data (use_existing_data=false)")
    print("-" * 60)
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/camera/generate-demo-video",
            json={"use_existing_data": False},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get("success"):
            print(f"\n✅ Success! Generated video from NEW data")
            print(f"   - Data Source: {result.get('data_source')}")
            print(f"   - Frames: {result.get('frame_count')}")
            print(f"   - Video URL: {result.get('video_url')}")
        else:
            print(f"\n❌ Failed: {result.get('error')}")
            print(f"   Data Source: {result.get('data_source')}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_generate_existing_video():
    """Test video generation with use_existing_data=true"""
    print("\n\n♻️  Test 2: Generate video with EXISTING data (use_existing_data=true)")
    print("-" * 60)
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/camera/generate-demo-video",
            json={"use_existing_data": True},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get("success"):
            print(f"\n✅ Success! Generated video from EXISTING data")
            print(f"   - Data Source: {result.get('data_source')}")
            print(f"   - Frames: {result.get('frame_count')}")
            print(f"   - Video URL: {result.get('video_url')}")
        else:
            print(f"\n❌ Failed: {result.get('error')}")
            print(f"   Data Source: {result.get('data_source')}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_default_behavior():
    """Test video generation with default parameters (no body)"""
    print("\n\n📹 Test 3: Generate video with DEFAULT parameters (no body)")
    print("-" * 60)
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/camera/generate-demo-video",
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get("success"):
            print(f"\n✅ Success! Generated video with defaults")
            print(f"   - Data Source: {result.get('data_source')}")
            print(f"   - Frames: {result.get('frame_count')}")
        else:
            print(f"\n❌ Failed: {result.get('error')}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 API Testing - /camera/generate-demo-video")
    print("=" * 60)
    print(f"API Base URL: {API_BASE_URL}")
    print("Make sure the backend server is running on port 8000!")
    
    # Run tests
    test_generate_new_video()
    time.sleep(2)
    test_generate_existing_video()
    time.sleep(2)
    test_default_behavior()
    
    print("\n" + "=" * 60)
    print("✅ Testing complete!")
    print("=" * 60)
