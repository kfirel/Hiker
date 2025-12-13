"""
Flow Loader - Loads conversation flow from YAML (preferred) or JSON (fallback)
"""

import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to import yaml, but don't fail if not available
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML not installed. Install with: pip install pyyaml")


class FlowLoader:
    """Loads conversation flow from YAML (preferred) or JSON (fallback)"""
    
    def __init__(self, flow_file: str):
        """
        Initialize flow loader
        
        Args:
            flow_file: Path to flow file (supports .yml, .yaml, .json)
        """
        self.flow_file = flow_file
        self.flow = self._load_flow()
    
    def _load_flow(self) -> Dict[str, Any]:
        """Load flow from YAML (preferred) or JSON (fallback)"""
        # If relative path, look in src/ directory
        if not os.path.isabs(self.flow_file) and not os.path.exists(self.flow_file):
            src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            flow_file = os.path.join(src_dir, self.flow_file)
        else:
            flow_file = self.flow_file
        
        # Try YAML first (.yml or .yaml)
        yaml_files = []
        if YAML_AVAILABLE:
            # Try .yml extension
            yaml_file = flow_file.replace('.json', '.yml')
            if yaml_file != flow_file and os.path.exists(yaml_file):
                yaml_files.append(yaml_file)
            
            # Try .yaml extension
            yaml_file2 = flow_file.replace('.json', '.yaml')
            if yaml_file2 != flow_file and yaml_file2 != yaml_file and os.path.exists(yaml_file2):
                yaml_files.append(yaml_file2)
            
            # If flow_file already ends with .yml or .yaml
            if flow_file.endswith(('.yml', '.yaml')) and os.path.exists(flow_file):
                yaml_files.append(flow_file)
        
        # Try YAML files
        for yaml_file in yaml_files:
            if os.path.exists(yaml_file):
                logger.info(f"Loading flow from YAML: {yaml_file}")
                return self._load_yaml(yaml_file)
        
        # Fallback to JSON
        if os.path.exists(flow_file):
            logger.info(f"Loading flow from JSON: {flow_file}")
            return self._load_json(flow_file)
        
        # If flow_file was .yml/.yaml but doesn't exist, try .json
        if flow_file.endswith(('.yml', '.yaml')):
            json_file = flow_file.rsplit('.', 1)[0] + '.json'
            if os.path.exists(json_file):
                logger.info(f"Loading flow from JSON (fallback): {json_file}")
                return self._load_json(json_file)
        
        raise FileNotFoundError(
            f"Flow file not found. Tried: {yaml_files + [flow_file]}"
        )
    
    def _load_yaml(self, file_path: str) -> Dict[str, Any]:
        """Load YAML file"""
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML not installed. Install with: pip install pyyaml")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data or {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading YAML file {file_path}: {e}")
            raise
    
    def _load_json(self, file_path: str) -> Dict[str, Any]:
        """Load JSON file (fallback)"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON file {file_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading JSON file {file_path}: {e}")
            raise
    
    def reload(self):
        """Reload flow from file"""
        self.flow = self._load_flow()
        return self.flow










