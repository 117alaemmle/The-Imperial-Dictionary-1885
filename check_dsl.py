import sys
import os

# ==========================================
# CONFIGURATION
# ==========================================
# Modifiable constant for the number of lines to show per error type
MAX_REPORT_LINES = 15 

# Set your DSL dictionary file path here
DICTIONARY_FILE = "imperial_1885_v1.dsl" 

# Note: Standard ABBYY Lingvo DSL files are often UTF-16. 
# If you get decoding errors, change 'utf-8' to 'utf-16'.
FILE_ENCODING = "utf-16" 
# ==========================================

def check_dsl_dictionary(filepath, max_reports):
    if not os.path.exists(filepath):
        print(f"Error: Could not find file '{filepath}'")
        return

    # Tracking lists for our 4 error types
    errors = {
        "duplicates": [],
        "out_of_order": [],
        "no_entry": [],
        "orphan_entry": []
    }

    seen_headwords = set()
    last_headword = None
    
    # State tracking variables
    # Valid line types: 'start', 'headword', 'entry', 'blank'
    prev_line_type = 'start'
    prev_headword_line_num = -1
    prev_headword_text = ""

    with open(filepath, 'r', encoding=FILE_ENCODING) as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line_num = i + 1
        raw_line = line.rstrip('\r\n')
        
        # Determine the structural type of the current line
        if not raw_line.strip():
            current_line_type = 'blank'
        elif raw_line.startswith(' ') or raw_line.startswith('\t'):
            current_line_type = 'entry'
        else:
            current_line_type = 'headword'
            
        # --- Evaluate Rules ---
        
        if current_line_type == 'headword':
            headword_lower = raw_line.lower()
            
            # 1. Duplicate headwords (case-insensitive)
            if headword_lower in seen_headwords:
                errors["duplicates"].append((line_num, raw_line))
            else:
                seen_headwords.add(headword_lower)
                
            # 2. Out of alphabetical order
            if last_headword is not None and headword_lower < last_headword:
                errors["out_of_order"].append((line_num, raw_line))
            
            last_headword = headword_lower
            
            # 3. Headword without entry (Case A: Followed immediately by another headword)
            if prev_line_type == 'headword':
                errors["no_entry"].append((prev_headword_line_num, prev_headword_text))
                
            prev_headword_line_num = line_num
            prev_headword_text = raw_line

        elif current_line_type == 'entry':
            # 4. Entries without headwords (Preceded by a blank line or start of file)
            if prev_line_type in ('blank', 'start'):
                errors["orphan_entry"].append((line_num, raw_line.strip()))
                
        elif current_line_type == 'blank':
            # 3. Headword without entry (Case B: Followed immediately by a blank line)
            if prev_line_type == 'headword':
                errors["no_entry"].append((prev_headword_line_num, prev_headword_text))
                
        prev_line_type = current_line_type

    # EOF Check for Rule 3: If the very last line in the file was a headword
    if prev_line_type == 'headword':
        errors["no_entry"].append((prev_headword_line_num, prev_headword_text))

    # --- Print Summary Report ---
    print("="*50)
    print(" DSL DICTIONARY ERROR REPORT")
    print("="*50)
    
    error_labels = [
        ("duplicates", "Duplicate headwords (case-insensitive)"),
        ("out_of_order", "Headwords not in alphabetical order"),
        ("no_entry", "Headwords without entries"),
        ("orphan_entry", "Entries without headwords (blank line preceding)")
    ]
    
    for key, label in error_labels:
        err_list = errors[key]
        print(f"\n[ {label}: {len(err_list)} found ]")
        
        if err_list:
            limit = min(max_reports, len(err_list))
            print(f"  -> Showing first {limit} occurrences:")
            for j in range(limit):
                l_num, txt = err_list[j]
                # Truncate long strings for cleaner terminal output
                disp_txt = txt if len(txt) < 50 else txt[:47] + "..."
                print(f"     Line {l_num}: {disp_txt}")

if __name__ == "__main__":
    check_dsl_dictionary(DICTIONARY_FILE, MAX_REPORT_LINES)
