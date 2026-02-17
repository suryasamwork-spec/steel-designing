import requests
import os
import time

# Configuration
URL = "http://localhost:5001/api/extract-text"
PDF_PATH = "test_valid.pdf" 

def test_extraction():
    # 1. Verify File Exists
    if not os.path.exists(PDF_PATH):
        print(f"❌ File not found: {PDF_PATH}")
        print("Please ensure 'test_valid.pdf' exists in the current directory.")
        return

    print(f"🚀 Testing extraction API at {URL}...")
    print(f"📂 Using file: {PDF_PATH}")
    
    # 2. Prepare Request Data
    # Selecting a large region to ensure we catch some text
    data = {
        "x": 0,
        "y": 0,
        "width": 1000, # Large width to cover most drawings
        "height": 1000, # Large height
        "page_num": 0
    }
    
    # 3. Send Request
    try:
        with open(PDF_PATH, "rb") as f:
            files = {"pdf": f}
            start_time = time.time()
            response = requests.post(URL, data=data, files=files)
            end_time = time.time()
            duration = end_time - start_time
            
            # 4. Analyze Response
            if response.status_code == 200:
                result = response.json()
                print(f"\n⏱️ Time Taken: {duration:.2f} seconds")
                print("\n✅ API Request Successful (200 OK)")
                print("-" * 30)
                
                # Check structure
                expected_keys = ["success", "profiles", "studs", "studs_count", "elevations"]
                missing_keys = [k for k in expected_keys if k not in result]
                
                if missing_keys:
                    print(f"⚠️ Response missing keys: {missing_keys}")
                else:
                    print("✅ Response structure valid")

                # Print Content
                print(f"🔹 Success: {result.get('success')}")
                print(f"🔹 Studs Count: {result.get('studs_count')}")
                print(f"🔹 Profiles Found: {result.get('profiles')}")
                print(f"🔹 Raw Text (snippet): {result.get('raw_text', '')[:100]}...")
                
                if result.get("success"):
                    print("\n🎉 TEST PASSED: Extraction API is functioning.")
                else:
                    print("\n⚠️ TEST WARNING: API returned success=False (logic issue?)")
            
            else:
                print(f"\n❌ API Request Failed with status {response.status_code}")
                print(f"Response: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Could not connect to the server.")
        print("👉 Is 'main.py' running on port 5001?")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")

if __name__ == "__main__":
    test_extraction()
