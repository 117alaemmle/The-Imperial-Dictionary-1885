import sys
import os
import difflib
import tempfile
import subprocess

VALID_WORDS_FILE = "valid_words.txt"
OUTPUT_DSL_FILE = "fixed_dictionary.dsl"

class Entry:
    def __init__(self):
        self.headwords = []
        self.definition = []

def load_valid_words(filepath):
    print(f"Loading valid words from {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Lowercase for case-insensitive matching, removing whitespace
            return set(word.strip().lower() for word in f if word.strip())
    except FileNotFoundError:
        print(f"Error: Could not find {filepath}. Please create it and try again.")
        sys.exit(1)

def parse_dsl(filepath):
    print(f"Parsing dictionary file: {filepath}...")
    entries = []
    current_entry = None
    headers = []
    
    with open(filepath, 'r', encoding='utf-16') as f:
        for line in f:
            stripped = line.rstrip('\n')
            if not stripped:
                continue
                
            # If line starts with a space or tab, it's a definition
            if line.startswith(' ') or line.startswith('\t'):
                if current_entry:
                    current_entry.definition.append(stripped)
            # Headers usually start with #
            elif line.startswith('#'):
                headers.append(stripped)
            # Otherwise, it's a headword
            else:
                # If the previous entry has definitions, it's closed. Start a new one.
                if current_entry and current_entry.definition:
                    entries.append(current_entry)
                    current_entry = Entry()
                elif not current_entry:
                    current_entry = Entry()
                
                current_entry.headwords.append(stripped)
                
        if current_entry:
            entries.append(current_entry)
            
    return headers, entries

def get_input_with_prefill(prompt, text):
    """Attempts to pre-fill the input prompt so the user can just edit the existing string."""
    try:
        import readline
        def hook():
            readline.insert_text(text)
            readline.redisplay()
        readline.set_pre_input_hook(hook)
        result = input(prompt)
        readline.set_pre_input_hook()
        return result
    except ImportError:
        # Fallback if readline is not available (e.g., standard Windows without pyreadline)
        print(f"Original: {text}")
        result = input(prompt + " (Leave blank to keep original): ")
        return result if result.strip() else text

def edit_entry_externally(entry):
    """Dumps entry to a temp file, opens system editor, and reads it back."""
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt', encoding='utf-8') as tf:
        for hw in entry.headwords:
            tf.write(hw + '\n')
        for line in entry.definition:
            tf.write(line + '\n')
        tmp_name = tf.name
    
    # Determine default editor
    editor = os.environ.get('EDITOR', 'notepad' if os.name == 'nt' else 'nano')
    subprocess.call([editor, tmp_name])
    
    # Read modifications back
    with open(tmp_name, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_hws, new_defs = [], []
    for line in lines:
        stripped = line.rstrip('\n')
        if not stripped:
            continue
        if line.startswith(' ') or line.startswith('\t'):
            new_defs.append(stripped)
        else:
            new_hws.append(stripped)
            
    os.remove(tmp_name)
    entry.headwords = new_hws
    entry.definition = new_defs

def get_nearest_match(word, valid_words_set):
    """Finds the closest match using difflib. Restricted to same starting letter for speed."""
    if not word: return None
    first_char = word[0].lower()
    # Narrow down the pool to speed up difflib on huge datasets
    pool = [w for w in valid_words_set if w.startswith(first_char) and abs(len(w) - len(word)) <= 2]
    matches = difflib.get_close_matches(word.lower(), pool, n=1, cutoff=0.5)
    return matches[0] if matches else "No close match found"

def main():
    if len(sys.argv) < 2:
        print("Usage: python dict_fixer.py <dictionary_file.dsl>")
        sys.exit(1)
        
    dsl_file = sys.argv[1]
    valid_words = load_valid_words(VALID_WORDS_FILE)
    headers, entries = parse_dsl(dsl_file)
    
    invalid_targets = []
    
    print("Scanning for invalid headwords...")
    for i, entry in enumerate(entries):
        for hw_idx, hw_line in enumerate(entry.headwords):
            # Handle "Spelling1 , Spelling2" formatting by splitting on commas
            sub_words = [w.strip() for w in hw_line.split(',')]
            for sub_word in sub_words:
                if not sub_word:  # Skip empty strings from stray commas
                    continue
                
                lower_sub = sub_word.lower()
                if lower_sub not in valid_words:
                    # Bypass if replacing dashes with spaces OR removing dashes completely results in a valid word
                    if '-' in lower_sub:
                        if lower_sub.replace('-', ' ') in valid_words or lower_sub.replace('-', '') in valid_words:
                            continue
                        
                    invalid_targets.append((i, hw_idx, hw_line, sub_word))
                    break # Only flag the line once, even if multiple parts are invalid
                    
    total_invalid = len(invalid_targets)
    print(f"\n--- SCAN COMPLETE ---")
    print(f"Total invalid headwords found: {total_invalid}\n")
    
    if total_invalid == 0:
        print("No errors found! Exiting.")
        sys.exit(0)
        
    input("Press Enter to begin fixing entries (Press Ctrl+C at any time to save and quit)...")
    
    try:
        for count, (entry_idx, hw_idx, full_hw_line, bad_sub_word) in enumerate(invalid_targets, 1):
            
            # If the user whitelisted this word earlier in this session, skip it silently
            if bad_sub_word.lower() in valid_words:
                continue
                
            entry = entries[entry_idx]
            
            # Re-fetch the headword line in case it was altered by a previous multi-headword edit
            current_hw_line = entry.headwords[hw_idx] 
            
            prev_hw = entries[entry_idx - 1].headwords[0] if entry_idx > 0 else "START OF DICTIONARY"
            next_hw = entries[entry_idx + 1].headwords[0] if entry_idx < len(entries) - 1 else "END OF DICTIONARY"
            
            nearest = get_nearest_match(bad_sub_word, valid_words)
            
            # Capitalize the suggestion to match Imperial Dictionary conventions
            if nearest and nearest != "No close match found":
                nearest = nearest.capitalize()
            elif not nearest:
                nearest = "No close match found"
            
            print("\n" + "="*60)
            print(f"Reviewing {count} of {total_invalid}")
            print(f"PREVIOUS : {prev_hw}")
            print(f"CURRENT  : {current_hw_line}  <-- INVALID ({bad_sub_word})")
            print(f"NEXT     : {next_hw}")
            print(f"SUGGESTED: {nearest}")
            print("-" * 60)
            print("\n".join(entry.definition[:5])) # Show first 5 lines of def for context
            if len(entry.definition) > 5: print("   [... definition truncated for preview ...]")
            print("-" * 60)
            
            valid_choice = False
            while not valid_choice:
                print("Options: [a]ccept suggested | [c]ustom edit | [s]kip | [w]hitelist (add to valid) | [e]dit entry | [D]agger macro")
                choice = input("Action: ").strip().lower()
                
                if choice == 'a':
                    if nearest != "No close match found":
                        entry.headwords[hw_idx] = current_hw_line.replace(bad_sub_word, nearest)
                        valid_choice = True
                    else:
                        print("Cannot accept - no match available.")
                        
                elif choice == 'c':
                    new_hw = get_input_with_prefill("Enter custom headword: ", current_hw_line)
                    entry.headwords[hw_idx] = new_hw
                    valid_choice = True
                    
                elif choice == 's':
                    valid_choice = True
                    
                elif choice == 'w':
                    # Append to the valid words text file
                    with open(VALID_WORDS_FILE, 'a', encoding='utf-8') as f:
                        f.write(bad_sub_word + '\n')
                    # Add to the in-memory set to auto-skip future occurrences
                    valid_words.add(bad_sub_word.lower())
                    print(f"Added '{bad_sub_word}' to {VALID_WORDS_FILE}.")
                    valid_choice = True
                    
                elif choice == 'e':
                    edit_entry_externally(entry)
                    valid_choice = True
                    
                elif choice == 'd':
                    entry.headwords[hw_idx] = current_hw_line[:-1]
                    def_fixed = False
                    for line_idx, def_line in enumerate(entry.definition):
                        if '[m2]' in def_line:
                            entry.definition[line_idx] = def_line.replace('[m2]', '[m2]† ', 1)
                            def_fixed = True
                            break
                            
                    if not def_fixed:
                        print("Warning: '[m2]' tag not found in the definition. Headword was truncated, but dagger was not inserted.")
                    valid_choice = True
                    
                else:
                    print("Invalid option. Please choose a, c, s, w, e, or D.")

    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Saving progress...")

    print(f"\nWriting updated dictionary to {OUTPUT_DSL_FILE}...")
    with open(OUTPUT_DSL_FILE, 'w', encoding='utf-16') as f:
        for header in headers:
            f.write(header + '\n')
        for entry in entries:
            for hw in entry.headwords:
                f.write(hw + '\n')
            for d in entry.definition:
                f.write(d + '\n')
                
    print("Done! Check your fixed dictionary file.")

    print(f"\nWriting updated dictionary to {OUTPUT_DSL_FILE}...")
    with open(OUTPUT_DSL_FILE, 'w', encoding='utf-16') as f:
        for header in headers:
            f.write(header + '\n')
        for entry in entries:
            for hw in entry.headwords:
                f.write(hw + '\n')
            for d in entry.definition:
                f.write(d + '\n')
                
    print("Done! Check your fixed dictionary file.")
    
if __name__ == "__main__":
    main()