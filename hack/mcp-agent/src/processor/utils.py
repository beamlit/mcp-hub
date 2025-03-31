import re

def extract_yaml_from_response(response_text) -> str:
    """Extract YAML content from agent response."""
    # Handle None or empty input
    if not response_text:
        return ""
    
    # If response is already a dict, convert to YAML string
    if isinstance(response_text, dict):
        try:
            import yaml
            # Handle special case when the dict has an 'output' key containing YAML
            if 'output' in response_text and isinstance(response_text['output'], str):
                return extract_yaml_from_response(response_text['output'])
            return yaml.dump(response_text, default_flow_style=False, sort_keys=False)
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
        
    # Try to extract from code block
    print(response_text)
    yaml_match = re.search(r'```(?:yaml)?\n(.*?)\n```', response_text, re.DOTALL)
    if yaml_match:
        return yaml_match.group(1)
    
    # Otherwise return the full text as it might be just the YAML content
    return response_text

def post_process_yaml(yaml_content: str) -> str:
    """Post-process YAML to fix common issues like unquoted special characters."""
    # Fix package names with @ symbols that need to be quoted
    # Look for lines like "- @package/name: version" and replace with "- '@package/name': version"
    pattern = r'(\s+- )(@[^:]+)(:.+)'
    yaml_content = re.sub(pattern, r'\1\'\2\'\3', yaml_content)
    
    return yaml_content
