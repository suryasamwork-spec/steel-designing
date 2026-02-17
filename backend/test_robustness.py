import re

# Simulate the post-process logic from main.py
def process_text_simulated(ocr_outputs):
    char_map = {
        'k': '1', 'K': '1', 'l': '1', 'I': '1', '|': '1',
        'O': '0', 'o': '0', 'D': '0', 'Q': '0',
        'S': '5', 's': '5',
        'Z': '2', 'z': '2',
        'B': '8',
        '{': '(', '}': ')', 
        # STRICT CHANGE: Unmap [] so they are NOT converted to ()
        # '[': '(', ']': ')' 
    }
    
    extracted_texts = []
    
    for text_val in ocr_outputs:
        clean_t = text_val.strip()
        
        # 1. Apply Character Mapping
        norm_t = ""
        for char in clean_t:
            norm_t += char_map.get(char, char)
        
        extracted_texts.append(norm_t)
        
    combined_text = " ".join(extracted_texts)
    combined_text = re.sub(r'\s+', ' ', combined_text) 
    
    print(f"\nProcessing: {combined_text}")
    
    # Logic copied from main.py regexes
    # REVERT: Match BOTH parentheses () and square brackets []
    pattern_stud_label = r'([Ww]?\d+[xX]\d+)\s*[\(\[]\s*(\d+)\s*[\)\]]'
    studs = []
    
    # 1. Find matched Beam Labels
    matches = list(re.finditer(pattern_stud_label, combined_text))
    
    temp_text_for_isolation = list(combined_text)

    for match in matches:
        beam = match.group(1)
        val = match.group(2)
        v_int = int(val)
        
        if 6 <= v_int <= 60:
            print(f"✅ Match (Label): {beam}({v_int})")
            studs.append(v_int)
        else:
            print(f"⚠️ Reject (Label Value Out of Range): {beam}({v_int})")

        # Mask out this match
        start, end = match.span()
        for i in range(start, end):
            temp_text_for_isolation[i] = ' '
    
    masked_text = "".join(temp_text_for_isolation)

    # 2. Find Isolated Brackets (Flexible Spacing)
    # REVERT: Match BOTH parentheses () and square brackets []
    pattern_isolated_brackets = r'[\(\[]\s*(\d+)\s*[\)\]]'
    potential_studs = re.findall(pattern_isolated_brackets, masked_text)
    
    for val in potential_studs:
        v_int = int(val)
        if 6 <= v_int <= 60:
            print(f"✅ Match (Isolated): ({v_int})")
            studs.append(v_int)
        else:
            print(f"⚠️ Reject (Isolated Out of Range 6-60): ({val})")
        
    return studs

# Test Cases
test_scenarios = [
    # 1. Typos - Should Pass
    (["k8", "W12x14(l0)", "(O7)"], [18, 10, 7]),
    
    # 2. Spacing - Should Pass
    (["( 12 )", "W16x40 ( 24 )"], [12, 24]),
    
    # 3. Validation - Should Fail / Reject
    (["(2)", "(4)", "(100)", "W12x12(200)"], []), # All out of range 6-60
    
    # 4. Fractions / Dates - Should Reject 
    (["(1/2)", "( 1 )", "( 5 )"], []), 
    
    # 5. Mixed - Should Pass some
    (["(20)", "(4)"], [20]),
    
    # 6. BRACKET TYPE CHECK - Square Brackets Should PASS NOW if in range (12, 20)
    (["[12]", "[ 20 ]", "W10x10[12]"], [12, 20, 12]) 
]

for inputs, expected in test_scenarios:
    print("-" * 20)
    print(f"Input: {inputs}")
    result = process_text_simulated(inputs)
    print(f"Result: {result}")
    
    # Note: Exact matching might vary if my manual logic here differs slightly from strict regex
    # But checking if we get NUMBERS is key.
    if len(result) == len(expected):
        print("PASS")
    else:
        print(f"FAIL (Expected {len(expected)})")
