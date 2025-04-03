import re

def extract_yaml_from_response(response_text) -> str:
    """Extract YAML content from agent response."""
    # Handle None or empty input
    if not response_text:
        return ""
        
    # Debug input type
    print(f"extract_yaml_from_response received type: {type(response_text)}")
    
    # Handle Pydantic models
    if hasattr(response_text, '__class__') and 'BaseModel' in str(response_text.__class__.__mro__):
        try:
            import yaml
            # Support both Pydantic v1 and v2
            if hasattr(response_text, "model_dump"):
                # Pydantic v2
                response_dict = response_text.model_dump()
            else:
                # Pydantic v1
                response_dict = response_text.dict()
                
            yaml_content = yaml.dump(response_dict, default_flow_style=False)
            print(f"Converted Pydantic model to YAML (length: {len(yaml_content)})")
            return yaml_content
        except Exception as e:
            print(f"Error converting Pydantic model to YAML: {e}")
            # Fall back to string representation and continue processing
            response_text = str(response_text)
    
    # If response is already a dict, convert to YAML string
    if isinstance(response_text, dict):
        try:
            import yaml
            # Handle special case when the dict has an 'output' key containing YAML
            if 'output' in response_text and isinstance(response_text['output'], str):
                return extract_yaml_from_response(response_text['output'])
            yaml_content = yaml.dump(response_text, default_flow_style=False, sort_keys=False)
            print(f"Converted dict to YAML (length: {len(yaml_content)})")
            return yaml_content
        except Exception as e:
            print(f"Error converting dict to YAML: {e}")
            return ""
    
    # Ensure response is a string
    if not isinstance(response_text, str):
        try:
            response_text = str(response_text)
        except Exception as e:
            print(f"Error converting response to string: {e}")
            return ""
    
    # Debug
    print(f"Extracting YAML from response of length {len(response_text)}")
    if len(response_text) < 500:
        print(f"Response: {response_text}")
    else:
        print(f"Response (truncated): {response_text[:200]}...")
        
    # Try to extract from code block (this is the most common format)
    yaml_match = re.search(r'```(?:yaml)?\s*(.*?)\s*```', response_text, re.DOTALL)
    if yaml_match:
        yaml_content = yaml_match.group(1).strip()
        print(f"Extracted YAML from code block (length: {len(yaml_content)})")
        return yaml_content
    
    # Try to extract YAML-like structure by looking for patterns
    lines = response_text.split('\n')
    yaml_lines = []
    in_yaml_section = False
    
    for line in lines:
        # Check for YAML section headers or list items
        if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:', line) or re.match(r'^\s*-\s+', line):
            in_yaml_section = True
            yaml_lines.append(line)
        # Include indented lines that might be part of YAML structure
        elif in_yaml_section and (line.startswith('  ') or not line.strip()):
            yaml_lines.append(line)
        # Break if we encounter non-YAML text after YAML section
        elif in_yaml_section and line.strip() and not line.startswith('  '):
            if line.startswith('#'):  # Allow comments
                yaml_lines.append(line)
            else:
                break
    
    if yaml_lines:
        yaml_content = '\n'.join(yaml_lines)
        print(f"Extracted {len(yaml_lines)} lines of YAML (length: {len(yaml_content)})")
        return yaml_content
    
    # If we get here, just return the text as-is if it looks like YAML
    # Check if it has any YAML-like patterns
    if re.search(r'^\s*[a-zA-Z_][a-zA-Z0-9_]*:', response_text, re.MULTILINE):
        print("Returning response as-is (appears to contain YAML)")
        return response_text
    
    print("No YAML pattern found, returning empty string")
    return ""

def post_process_yaml(yaml_content: str) -> str:
    """Post-process YAML to fix common issues like unquoted special characters."""
    # Fix package names with @ symbols that need to be quoted
    # Look for lines like "- @package/name: version" and replace with "- '@package/name': version"
    pattern = r'(\s+- )(@[^:]+)(:.+)'
    yaml_content = re.sub(pattern, r'\1\'\2\'\3', yaml_content)
    
    return yaml_content
