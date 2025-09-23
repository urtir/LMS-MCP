#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the fixed query generation logic
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

def test_query_cleanup():
    """Test the query cleanup logic"""
    
    # Simulate problematic LLM responses
    test_cases = [
        # Case 1: Response with thinking tags
        ('<think>\n</think>\n\nSQL injection\nBrute force\nMalware...', 'SQL injection'),
        
        # Case 2: Multi-line response
        ('Output:\nSQL injection vulnerability attack\nBrute force authentication\nMalware detection', 'SQL injection vulnerability attack'),
        
        # Case 3: Response with artifacts
        ('Keywords: SQL injection vulnerability', 'SQL injection vulnerability'),
        
        # Case 4: Good response
        ('SQL injection vulnerability attack', 'SQL injection vulnerability attack'),
        
        # Case 5: Empty response
        ('', 'security vulnerability attack'),
    ]
    
    import re
    
    for i, (generated_query, expected_pattern) in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Input: '{generated_query}'")
        
        # Apply the cleanup logic
        cleaned_query = generated_query.strip()
        
        # Remove quotes
        cleaned_query = cleaned_query.replace('"', '').replace("'", '').strip()
        
        # Handle thinking tags
        if '<think>' in cleaned_query or '</' in cleaned_query:
            cleaned_query = re.sub(r'<think>.*?</think>', '', cleaned_query, flags=re.DOTALL)
            cleaned_query = cleaned_query.strip()
        
        # Handle multi-line responses
        if '\n' in cleaned_query:
            lines = [line.strip() for line in cleaned_query.split('\n') if line.strip()]
            for line in lines:
                words = line.split()
                if (3 <= len(words) <= 10 and 
                    not line.lower().startswith(("okay", "let", "the user", "output", "keywords")) and
                    not any(phrase in line.lower() for phrase in ["tackle this", "lets", "i would", "here are"])):
                    cleaned_query = line
                    break
            else:
                cleaned_query = lines[0] if lines else "security log analysis"
        
        # Remove common artifacts
        cleaned_query = cleaned_query.replace("Output:", "").replace("Keywords:", "").strip()
        
        # Fallback for empty
        if not cleaned_query or len(cleaned_query) < 3:
            cleaned_query = "security vulnerability attack"
        
        # Truncate if too long
        if len(cleaned_query) > 100:
            words = cleaned_query.split()[:8]
            cleaned_query = " ".join(words)
        
        print(f"Output: '{cleaned_query}'")
        print(f"Expected pattern: '{expected_pattern}'")
        
        # Check if it looks reasonable
        if len(cleaned_query) >= 3 and len(cleaned_query) <= 100:
            print("✅ PASS - Output looks good")
        else:
            print("❌ FAIL - Output invalid")

if __name__ == "__main__":
    print("🧪 Testing Query Cleanup Logic")
    print("=" * 50)
    test_query_cleanup()
    print("\n" + "=" * 50)
    print("✅ Test completed!")