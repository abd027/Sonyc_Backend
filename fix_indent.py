#!/usr/bin/env python3
"""Fix indentation issues in main.py"""
import re

file_path = 'app/main.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix line 49 indentation
lines = content.split('\n')
if len(lines) > 48:
    # Line 49 (index 48) should be indented
    if lines[48].strip().startswith('embedding_model') and not lines[48].startswith('    '):
        lines[48] = '    ' + lines[48].lstrip()
        print(f"Fixed line 49: {lines[48][:50]}")

# Fix line 387 indentation (return statement)
if len(lines) > 386:
    if lines[386].strip().startswith('return') and not lines[386].startswith('        '):
        lines[386] = '        ' + lines[386].lstrip()
        print(f"Fixed line 387: {lines[386][:50]}")

# Fix line 584 indentation (for loop after try)
if len(lines) > 583:
    if lines[583].strip().startswith('for') and not lines[583].startswith('                '):
        lines[583] = '                ' + lines[583].lstrip()
        print(f"Fixed line 584: {lines[583][:50]}")

content = '\n'.join(lines)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Indentation fixes applied!")

