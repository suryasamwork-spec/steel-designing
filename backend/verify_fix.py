import re

def verify_extraction_logic(combined_text):
    print(f"Testing text: {combined_text}")
    
    # --- LOGIC COPIED FROM MAIN.PY ---
    pattern_stud_label = r'([Ww]?\d+[xX]\d+)\s*[\(\[]\s*(\d+)\s*[\)\]]'
    
    studs = []
    profiles = {}
    
    # 1. Find all stud labels: Beam(Count)
    matches = list(re.finditer(pattern_stud_label, combined_text))
    print(f"DEBUG Matches found: {len(matches)}")
    
    # Mask found beam matches
    temp_text_for_isolation = list(combined_text)

    for match in matches:
        beam = match.group(1)
        val = match.group(2)
        v_int = int(val)
        
        if 6 <= v_int <= 60:
            print(f"✅ Match (Label): {beam}({v_int})")
            studs.append(v_int)
            if beam not in profiles:
                profiles[beam] = []
            profiles[beam].append(v_int)
        else:
            print(f"⚠️ Reject (Label Value Out of Range): {beam}({v_int})")

        # Mask out this match in the text
        start, end = match.span()
        for i in range(start, end):
            temp_text_for_isolation[i] = ' '
    
    masked_text = "".join(temp_text_for_isolation)
    print(f"Profiles: {profiles}")

    # 2. Find Isolated Brackets in the MASKED text
    pattern_isolated_brackets = r'[\(\[\{]\s*(\d+)\s*[\)\]\}]'
    potential_studs = re.findall(pattern_isolated_brackets, masked_text)
    
    for val in potential_studs:
        v_int = int(val)
        if val.isdigit() and v_int < 100: 
            print(f"✅ Match (Isolated): ({v_int})")
            studs.append(v_int)
    
    return studs

# Test Case that failed before (mixed content)
test_string = "W12x14 (10)  (24)  (30)  W10x10 [5]"
extracted = verify_extraction_logic(test_string)

print(f"\nTotal Extracted: {len(extracted)}")
print(f"Values: {extracted}")

expected_count = 4 # 10, 24, 30, 5
if len(extracted) == expected_count:
    print("\n✅ Verification PASSED: All items extracted.")
else:
    print(f"\n❌ Verification FAILED: Expected {expected_count}, got {len(extracted)}")
