import sqlite3
import os
import re

# Update this to match the exact name of the extracted ITIS database file
DB_FILE = "ITIS.sqlite" 
OUTPUT_FILE = "valid_words.txt"

def extract_itis_words(db_path, output_path):
    if not os.path.exists(db_path):
        print(f"Error: Could not find '{db_path}'.")
        print("Please extract the ITIS zip file, ensure the database is in this folder, and update DB_FILE in this script if the name differs.")
        return

    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Querying taxonomic names...")
    try:
        # The 'taxonomic_units' table contains the classifications
        cursor.execute("SELECT complete_name FROM taxonomic_units")
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}. The table structure might have changed.")
        conn.close()
        return

    scientific_words = set()
    
    # Regex to keep only standard letters and hyphens 
    # (ignores numbers or hybrid symbols sometimes found in modern taxonomy)
    word_pattern = re.compile(r'^[a-zA-Z\-]+$')

    print("Processing names (this will take a few seconds)...")
    for row in cursor.fetchall():
        name = row[0]
        if name:
            # Split multi-word names (e.g., "Felis catus") into individual words
            for word in name.split():
                # Strip edge punctuation and lowercase it
                clean_word = word.strip('.,()[]"\'').lower()
                
                # Only add if it's a valid alphabetic/hyphenated word longer than 1 letter
                if word_pattern.match(clean_word) and len(clean_word) > 1:
                    scientific_words.add(clean_word)

    conn.close()
    print(f"Extracted {len(scientific_words)} unique scientific words from ITIS.")

    # Read existing words so we don't bloat your text file with duplicates
    existing_words = set()
    if os.path.exists(output_path):
        print(f"Reading existing words from {output_path} to avoid duplicates...")
        with open(output_path, 'r', encoding='utf-8') as f:
            existing_words = set(w.strip().lower() for w in f)
    
    # Isolate only the words that aren't already in your list
    new_words = scientific_words - existing_words

    if not new_words:
        print("No new words to add. Your list already has them all!")
        return

    print(f"Appending to {output_path}...")
    with open(output_path, 'a', encoding='utf-8') as f:
        for word in sorted(new_words):
            f.write(word + '\n')

    print(f"\n--- SUCCESS ---")
    print(f"Added {len(new_words):,} new scientific terms to {output_path}.")

if __name__ == "__main__":
    extract_itis_words(DB_FILE, OUTPUT_FILE)