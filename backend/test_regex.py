#!/usr/bin/env python3
import re

# Test content
content = """<h1>テスト記事</h1>
<p>この記事は画像プレースホルダーのテスト用です。</p>

<!-- IMAGE_PLACEHOLDER: img_001|美しい風景の写真|A beautiful landscape with mountains and blue sky -->

<p>上記のプレースホルダーは美しい風景の画像を表示します。</p>

<!-- IMAGE_PLACEHOLDER: img_002|AI技術のイメージ図|An illustration showing AI technology and machine learning concepts -->

<p>こちらのプレースホルダーはAI技術のイメージ図を表示します。</p>"""

print("Testing regex patterns...")
print(f"Content length: {len(content)}")

# Debug: Show each line
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'IMAGE_PLACEHOLDER' in line:
        print(f"Line {i}: {repr(line)}")

# Better regex pattern that handles more characters in the prompt
pattern = r'<!-- IMAGE_PLACEHOLDER: ([^|]+)\|([^|]+)\|([^>]+) -->'
matches = re.findall(pattern, content)

print(f"\nFound {len(matches)} matches:")
for i, (placeholder_id, description_jp, prompt_en) in enumerate(matches):
    print(f"  {i+1}. ID: '{placeholder_id.strip()}'")
    print(f"     JP: '{description_jp.strip()}'") 
    print(f"     EN: '{prompt_en.strip()}'")

# Test simple placeholder
simple_test = "<!-- IMAGE_PLACEHOLDER: test_id|test description|test prompt -->"
simple_matches = re.findall(pattern, simple_test)
print(f"\nSimple test matches: {len(simple_matches)}")
if simple_matches:
    print(f"  Simple match: {simple_matches[0]}")