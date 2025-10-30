import random
import time
import uuid
import logging
import logging.config
import ast
from pathlib import Path
import json
import sys
import os


class DataGenerator:
    
    def __init__(self, defaults=None):
        self.defaults = defaults or {}
        self.logger = self.setup_logging()
    
    def setup_logging(self):
        logger = logging.getLogger(__name__)
        if logger.handlers:
            return logger
        
        config_path = self.defaults.get('logging_config', 'logging.ini')
        if os.path.exists(config_path):
            try:
                logging.config.fileConfig(config_path, disable_existing_loggers=False)
                return logging.getLogger(__name__)
            except Exception:
                # If config load fails, fall back to basic configuration
                logging.getLogger(__name__).exception(f"Failed to load logging config '{config_path}', falling back")

        # Fallback: programmatic configuration (console + file)
        handlers = [logging.StreamHandler(), logging.FileHandler(self.defaults.get('log_file', 'magicgenerator.log'))]
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=handlers
        )

        return logging.getLogger(__name__)
    
    def parse_schema(self, schema_input):
        # Accept dicts directly (caller provided a parsed schema)
        if isinstance(schema_input, dict):
            return schema_input

        if not isinstance(schema_input, str):
            self.logger.error("Schema must be a JSON string or a path to a JSON file")
            raise ValueError("Schema must be a JSON string or a path to a JSON file")

        # If it's a path, read the file
        if os.path.isfile(schema_input):
            try:
                with open(schema_input, 'r') as f:
                    schema = json.load(f)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in schema file '{schema_input}': {e}")
                raise ValueError(f"Invalid JSON in schema file '{schema_input}': {e}")
            except FileNotFoundError as e:
                self.logger.exception(f"Could not read schema file '{schema_input}': {e}")
                raise ValueError(f"Could not read schema file '{schema_input}': {e}")
        else:
            # Try parsing the string as JSON
            try:
                schema = json.loads(schema_input)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON schema string: {e}")
                raise ValueError(f"Invalid JSON schema string: {e}")

        return schema

    def validate_schema(self, schema):
        if not isinstance(schema, dict):
            self.logger.error("Schema must be a dictionary")
            raise ValueError("Schema must be a dictionary")

        for key, value in schema.items():
            if not isinstance(value, str):
                self.logger.error(f"Schema value for '{key}' must be a string")
                raise ValueError(f"Schema value for '{key}' must be a string")

            if ':' not in value:
                self.logger.error(f"Schema value for '{key}' must contain ':' separator")
                raise ValueError(f"Schema value for '{key}' must contain ':' separator")

            left_type = value.split(':', 1)[0].strip()
            if left_type not in ('timestamp', 'str', 'int'):
                self.logger.error(f"Unsupported field type in schema for '{key}': {left_type}")
                raise ValueError(f"Unsupported field type in schema for '{key}': {left_type}")

    
    def generate_value(self, field_type, value_spec):
        try:
            if field_type == 'timestamp':
                if value_spec and value_spec.strip():
                    self.logger.warning(f"Timestamp field ignores value specification: {value_spec}")
                return str(time.time())
            
            elif field_type == 'str':
                return self.generate_string(value_spec)

            elif field_type == 'int':
                return self.generate_integer(value_spec)
            
            else:
                self.logger.error(f"Unsupported field type: {field_type}")
                sys.exit(1)
                
        except Exception:
            self.logger.exception(f"Error generating value for type '{field_type}'")
            sys.exit(1)
    

    def generate_string(self, value_spec):
        value_spec = value_spec.strip()
        
        if value_spec == 'rand':
            return str(uuid.uuid4())
        
        elif value_spec.startswith('rand(') and value_spec.endswith(')'):
            self.logger.error(f"Invalid rand(range) usage for string type: {value_spec}")
            sys.exit(1)

        elif value_spec.startswith('[') and value_spec.endswith(']'):
            try:
                try:
                    choices = json.loads(value_spec)
                except json.JSONDecodeError:
                    choices = ast.literal_eval(value_spec)

                if not isinstance(choices, list):
                    raise ValueError("Not a list")
                return random.choice(choices)
            except:
                self.logger.exception(f"Invalid list format for string: {value_spec}")
                sys.exit(1)
        
        elif not value_spec:
            return "" 
        else:
            return value_spec

    
    def generate_integer(self, value_spec):
        value_spec = value_spec.strip()
        
        if value_spec == 'rand':
            return random.randint(0, 10000)
        
        elif value_spec.startswith('rand(') and value_spec.endswith(')'):
            try:
                range_str = value_spec[5:-1]
                parts = range_str.split(',')
                if len(parts) != 2:
                    raise ValueError("Invalid range format")
                start, end = int(parts[0].strip()), int(parts[1].strip())
                return random.randint(start, end)
            except Exception as e:
                self.logger.exception(f"Invalid rand range for integer: {value_spec} - {e}")
                sys.exit(1)
        
        elif value_spec.startswith('[') and value_spec.endswith(']'):
            try:
                try:
                    choices = json.loads(value_spec)
                except json.JSONDecodeError:
                    choices = ast.literal_eval(value_spec)

                if not isinstance(choices, list):
                    raise ValueError("Not a list")
                return random.choice(choices)
            except:
                self.logger.exception(f"Invalid list format for integer: {value_spec}")
                sys.exit(1)
        
        elif not value_spec:
            return None
        
        else:
            try:
                return int(value_spec)
            except ValueError:
                self.logger.exception(f"Cannot convert '{value_spec}' to integer")
                sys.exit(1)

    
    def generate_line(self, schema):
        line = {}
        for key, value_spec in schema.items():
            field_type, spec = value_spec.split(':', 1)
            line[key] = self.generate_value(field_type.strip(), spec.strip())
        return line
    
    
    def generate_file(self, args, file_index, total_files):
        try:
            filename = self.generate_filename(args, file_index, total_files)
            filepath = os.path.join(args.path_to_save_files, filename)
            
            self.logger.info(f"Generating file: {filename}")
            
            with open(filepath, 'w') as f:
                for i in range(args.data_lines):
                    line = self.generate_line(args.data_schema)
                    f.write(json.dumps(line) + '\n')
                    
                    if args.files_count == 0 and i == 0:
                        print(json.dumps(line))
            
            self.logger.info(f"Completed file: {filename}")
            return filename
            
        except Exception:
            self.logger.exception(f"Error generating file {file_index}")
            return None
    
    
    def generate_filename(self, args, file_index, total_files):
        base_name = args.file_name
        
        if total_files == 1 and args.files_count != 0:
            return f"{base_name}.json"
        
        if args.file_prefix == 'count':
            return f"{base_name}_{file_index + 1}.json"
        elif args.file_prefix == 'random':
            return f"{base_name}_{random.randint(1000, 9999)}.json"
        elif args.file_prefix == 'uuid':
            return f"{base_name}_{uuid.uuid4()}.json"
        else:
            return f"{base_name}.json"
    

    def clear_path(self, args):
        if not args.clear_path:
            return
        
        pattern = f"{args.file_name}*.json"
        cleared_count = 0
        
        for file_path in Path(args.path_to_save_files).glob(pattern):
            try:
                file_path.unlink()
                cleared_count += 1
            except Exception as e:
                self.logger.warning(f"No file to delete in {file_path}: {e}")
        
        if cleared_count > 0:
            self.logger.info(f"Cleared {cleared_count} existing files")
