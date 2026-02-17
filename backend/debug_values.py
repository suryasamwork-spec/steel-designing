import requests
import json

URL = "http://localhost:5001/api/extract-text"
PDF_PATH = "test_valid.pdf"

def debug_extraction():
    data = {
        "x": 0,
        "y": 0,
        "width": 1000,
        "height": 1000,
        "page_num": 0
    }
    
    print(f"🕵️ Debugging extraction for {PDF_PATH}...")
    try:
        with open(PDF_PATH, "rb") as f:
            files = {"pdf": f}
            res = requests.post(URL, data=data, files=files)
            
            if res.status_code == 200:
                result = res.json()
                print("\n--- Extracted Raw Text ---")
                print(result.get('raw_text', ''))
                print("\n--- Detected Studs ---")
                print(f"Studs: {result.get('studs')}")
                print("\n--- Profiles ---")
                print(json.dumps(result.get('profiles'), indent=2))
            else:
                print(f"❌ Failed: {res.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_extraction()
