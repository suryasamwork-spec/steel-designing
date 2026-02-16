import requests
import json

url = "http://localhost:5001/api/extract-text"
# Ensure we have a valid PDF. Using the one from previous context if available, else a dummy one might fail OCR but return structure.
# Assuming test_valid.pdf exists from previous ls command.

files = {
    'pdf': ('test_valid.pdf', open('test_valid.pdf', 'rb'), 'application/pdf')
}
data = {
    'x': 0,
    'y': 0,
    'width': 600,
    'height': 800,
    'page_num': 0
}

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, files=files, data=data)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        res_json = response.json()
        print("Response JSON keys:", res_json.keys())
        if 'profiles' in res_json:
            print("✅ 'profiles' key found in response.")
            print("Profiles data:", json.dumps(res_json['profiles'], indent=2))
        else:
            print("❌ 'profiles' key MISSING in response.")
    else:
        print(f"Error Response: {response.text}")

except Exception as e:
    print(f"Error: {e}")
