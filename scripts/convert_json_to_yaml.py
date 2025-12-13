#!/usr/bin/env python3
"""
Convert conversation_flow.json to conversation_flow.yml
"""

import json
import yaml
import sys
import os
from pathlib import Path

def convert_json_to_yaml(json_file: str, yaml_file: str = None):
    """
    Convert JSON file to YAML
    
    Args:
        json_file: Path to JSON file
        yaml_file: Path to output YAML file (defaults to same name with .yml extension)
    """
    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}")
        sys.exit(1)
    
    # Load JSON
    print(f"📖 Loading JSON file: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Determine output file
    if yaml_file is None:
        yaml_file = json_file.replace('.json', '.yml')
    
    # Write YAML
    print(f"💾 Writing YAML file: {yaml_file}")
    with open(yaml_file, 'w', encoding='utf-8') as f:
        yaml.dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            width=120,
            line_break=None  # Use system default
        )
    
    print(f"✅ Converted {json_file} to {yaml_file}")
    print(f"📊 Stats: {len(data.get('states', {}))} states, {len(data.get('commands', {}))} commands")
    
    return yaml_file

if __name__ == '__main__':
    # Default to src/conversation_flow.json
    project_root = Path(__file__).parent.parent
    default_json = project_root / 'src' / 'conversation_flow.json'
    
    json_file = sys.argv[1] if len(sys.argv) > 1 else str(default_json)
    yaml_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    convert_json_to_yaml(json_file, yaml_file)










