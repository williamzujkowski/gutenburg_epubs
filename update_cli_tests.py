#!/usr/bin/env python3
"""Quick script to update CLI tests with async_mode attribute."""

import re

with open("tests/test_cli.py") as f:
    content = f.read()

# Find all places where args = Mock() is used in test functions
pattern = r'(args = Mock\(\))'

# Replace with version that includes async_mode and concurrency
replacement = r'args = Mock()\n        args.async_mode = False'

# For download-popular tests, also add concurrency
download_popular_pattern = r'(args = Mock\(\))(.*test_download_popular.*)'
download_popular_replacement = r'args = Mock()\n        args.async_mode = False\n        args.concurrency = 5'

# Apply replacements
content = re.sub(pattern, replacement, content)

# Special handling for download-popular tests
lines = content.split('\n')
new_lines = []
in_download_popular_test = False

for i, line in enumerate(lines):
    if 'test_download_popular' in line:
        in_download_popular_test = True
    elif 'def test_' in line:
        in_download_popular_test = False

    if in_download_popular_test and 'args = Mock()' in line and i < len(lines) - 1:
        new_lines.append(line)
        if 'args.async_mode = False' not in lines[i+1]:
            new_lines.append('        args.async_mode = False')
            new_lines.append('        args.concurrency = 5')
    else:
        new_lines.append(line)

content = '\n'.join(new_lines)

with open("tests/test_cli.py", "w") as f:
    f.write(content)

print("Updated test_cli.py")
