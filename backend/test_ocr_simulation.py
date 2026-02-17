import re

def simulate_extraction(text):
    # Regexes from main.py
    pattern_stud_label = r'([Ww]\d+[xX]\d+)\s*[\[\(]\s*(\d+)\s*[\]\)]'
    blocklist_keywords = ["COUNT", "STUD", "TOTAL", "SHEET", "DWG", "NOTE", "QTY", "PCS", "PIECES", "REV", "DATE"]
    
    profiles = {}
    total_studs = 0
    
    print(f"Input Text: {text}")
    
    # 1. Find Labeled
    matches = list(re.finditer(pattern_stud_label, text))
    temp_text = list(text)
    
    for m in matches:
        beam = m.group(1).upper()
        val = int(m.group(2))
        print(f"Found Labeled: {beam} -> {val}")
        if beam not in profiles: profiles[beam] = []
        profiles[beam].append(val)
        total_studs += 1
        # Mask
        for i in range(m.start(), m.end()): temp_text[i] = " "
        
    masked_text = "".join(temp_text)
    
    # 2. Find Isolated
    pattern_iso = r'([\[\(])\s*(\d+)\s*([\]\)])'
    iso_matches = list(re.finditer(pattern_iso, masked_text))
    
    for m in iso_matches:
        val = int(m.group(2))
        start_idx = m.start()
        preceding = masked_text[max(0, start_idx-40):start_idx].upper()
        
        is_blocked = any(kw in preceding for kw in blocklist_keywords)
        if is_blocked:
            print(f"Blocked isolated value {val} due to context: ...{preceding}")
            continue
            
        print(f"Found Isolated: {val}")
        if "UNLABELED" not in profiles: profiles["UNLABELED"] = []
        profiles["UNLABELED"].append(val)
        total_studs += 1
        
    print(f"\nFinal Profiles: {profiles}")
    print(f"Total Studs Counted: {total_studs}")

# Test the user's reported problem cases
print("--- TEST 1: Supporting () and [] for labels ---")
simulate_extraction("W24X68 (26)  STUD COUNT [55]  W12X19[18]")

print("\n--- TEST 2: Spaced parentheses ---")
simulate_extraction("W14X22  ( 20 )")
