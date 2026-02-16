import re

def test_extraction(combined_text):
    # Normalize common OCR errors
    combined_text = combined_text.replace('|', '(').replace('{', '(').replace('}', ')')
    print(f"Testing text: {combined_text}")
    
    # Robust Pattern Matching
    pattern_elevation = r'[\[\(\{]\s*([^\]\)\}]*?[\d"\']+[^\]\)\}]*?)\s*[\]\)\}]'
    pattern_studs = r'[\(\[\|]\s*(\d+)\s*[\)\]\|]'
    
    elevations = []
    potential_elevations = re.findall(pattern_elevation, combined_text)
    for match in potential_elevations:
        if any(c in match for c in ['"', "'", '.', 'x']) or len(match) > 3:
            elevations.append(match.strip())
            
    studs = []
    potential_studs = re.findall(pattern_studs, combined_text)
    for val in potential_studs:
        if val.isdigit():
            studs.append(int(val))
    
    if not studs:
        naked_numbers = re.findall(r'(?<=[(\[|])\s*(\d+)\s*|(\d+)\s*(?=[)\]|])', combined_text)
        for group in naked_numbers:
            val = next((v for v in group if v), None)
            if val and val.isdigit():
                studs.append(int(val))

    print(f"Extracted: {len(studs)} studs ({studs}), {len(elevations)} elevations ({elevations})")
    return studs, elevations

# Test cases based on the screenshot and rotations
test_cases = [
    "W24x62 (33) 48k 14k 24k W18x35 (29)", # Horizontal
    "W18x35  (29)",                       # Vertical (simulated merge)
    "W24x62 (33)  W18x35  (29)  14k",     # Multiple labels in one selection
    "W18x35  ( 29 )  W21x62 ( 30 )",     # Spaced brackets
]

for tc in test_cases:
    test_extraction(tc)
    print("-" * 20)
