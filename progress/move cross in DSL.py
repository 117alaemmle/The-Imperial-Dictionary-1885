import re

def move_cross_in_dsl(input_file, output_file):
    try:
        # Open the DSL file using UTF-16 encoding
        with open(input_file, 'r', encoding='utf-16') as f:
            content = f.read()

        # The Regex Pattern:
        # ([^\r\n]+?)  -> Group 1: Captures the headword text right up until the cross
        # \s*†\s*\r?\n -> Matches any space before the cross, the cross itself, and the line break
        # (\s*\[m2\])  -> Group 2: Captures the indentation (tabs/spaces) and the [m2] tag
        pattern = re.compile(r'([^\r\n]+?)\s*†\s*\r?\n(\s*\[m2\])')
        
        # The Replacement: Group 1 + Newline + Group 2 + Cross + Space
        modified_content = pattern.sub(r'\1\n\2† ', content)

        # Write the modified content to the output file, preserving UTF-16
        with open(output_file, 'w', encoding='utf-16') as f:
            f.write(modified_content)
            
        print(f"Success! Processed DSL saved to '{output_file}'.")

    except FileNotFoundError:
        print(f"Error: Could not find the file '{input_file}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Change these filenames if necessary
    INPUT_FILENAME = 'imperial_1885_v1.dsl'
    OUTPUT_FILENAME = 'imperial_1885_v1_mod.dsl'
    
    move_cross_in_dsl(INPUT_FILENAME, OUTPUT_FILENAME)