#!/usr/bin/env python3
"""
Script to automatically add LLM post-processing to ALL MCP tools
"""

import re

def process_file():
    # Read the current file
    with open('src/api/wazuh_fastmcp_server.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern to find all @mcp.tool functions that return json.dumps
    pattern = r'(@mcp\.tool\s*\nasync def [^(]+\([^)]*\) -> str:[^}]+?)(return json\.dumps\(result, indent=2\))'
    
    def replace_return(match):
        function_part = match.group(1)
        
        # Extract function name
        func_name_match = re.search(r'async def (\w+)\(', function_part)
        if not func_name_match:
            return match.group(0)
        
        func_name = func_name_match.group(1)
        
        # Skip functions that already have LLM processing
        if 'format_with_llm' in function_part:
            return match.group(0)
        
        # Create the replacement
        replacement = f"""{function_part}raw_json = json.dumps(result, indent=2)
    
    # Format with LLM
    formatted_response = await format_with_llm(
        raw_json=raw_json,
        tool_name="{func_name}",
        user_context=f"User called {func_name} function",
        ctx=ctx
    )
    
    return formatted_response"""
        
        return replacement
    
    # Apply the replacement
    new_content = re.sub(pattern, replace_return, content, flags=re.DOTALL)
    
    # Write back to file
    with open('src/api/wazuh_fastmcp_server.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Applied LLM processing to all MCP tools!")

if __name__ == "__main__":
    process_file()