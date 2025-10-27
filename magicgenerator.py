import argparse
import configparser
import json
import logging
import multiprocessing
import os
import random
import sys
import time
import uuid
import ast
from pathlib import Path


class DataGenerator:
    def __init__(self, defaults=None):
        self.defaults = defaults or {}
        self.logger = self.setup_logging()
    
    def setup_logging(self):
        logger = logging.getLogger(__name__)
        if logger.handlers:
            return logger

        logger.setLevel(logging.INFO)
        fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

        log_file = self.defaults.get('log_file', 'magicgenerator.log')
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        return logger
    
    def parse_schema(self, schema_input):

        try:
            if os.path.isfile(schema_input):
                with open(schema_input, 'r') as f:
                    schema = json.load(f)
            else:
                schema = json.loads(schema_input)
            
            self.validate_schema(schema)
            return schema
        except json.JSONDecodeError as e:
            self.logger.exception(f"Invalid JSON schema: {e}")
            sys.exit(1)
        except Exception:
            self.logger.exception("Error parsing schema")
            sys.exit(1)
    


    def validate_schema(self, schema):
        if not isinstance(schema, dict):
            self.logger.error("Schema must be a dictionary")
            sys.exit(1)

        for key, value in schema.items():
            if not isinstance(value, str):
                self.logger.error(f"Schema value for '{key}' must be a string")
                sys.exit(1)

            if ':' not in value:
                self.logger.error(f"Schema value for '{key}' must contain ':' separator")
                sys.exit(1)

            left_type = value.split(':', 1)[0].strip()
            if left_type not in ('timestamp', 'str', 'int'):
                self.logger.error(f"Unsupported field type in schema for '{key}': {left_type}")
                sys.exit(1)

    
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
                self.logger.warning(f"Could not delete {file_path}: {e}")
        
        if cleared_count > 0:
            self.logger.info(f"Cleared {cleared_count} existing files")


class MagicGenerator:    
    def __init__(self):
        self.defaults = self._load_defaults()
        self.generator = DataGenerator(self.defaults)
    
    def _load_defaults(self):
        config = configparser.ConfigParser()
        default_file = 'default.ini'
        
        if os.path.exists(default_file):
            config.read(default_file)
        else:
            config['DEFAULTS'] = {
                'path_to_save_files': '.',
                'files_count': '1',
                'file_name': 'data',
                'file_prefix': 'count',
                'data_lines': '1000',
                'multiprocessing': '1',
                'log_file': 'magicgenerator.log'
            }
            with open(default_file, 'w') as f:
                config.write(f)
        
        return dict(config['DEFAULTS'])
    
    def parse_arguments(self):
        parser = argparse.ArgumentParser(
            description='MagicGenerator - Test data generator',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        
        parser.add_argument(
            'path_to_save_files',
            nargs='?',
            default=self.defaults.get('path_to_save_files', '.'),
            help='Path to save generated files'
        )
        
        parser.add_argument(
            '--files_count',
            type=int,
            default=int(self.defaults.get('files_count', '1')),
            help='Number of JSON files to generate'
        )
        
        parser.add_argument(
            '--file_name',
            default=self.defaults.get('file_name', 'data'),
            help='Base filename for generated files'
        )
        
        parser.add_argument(
            '--file_prefix',
            choices=['count', 'random', 'uuid'],
            default=self.defaults.get('file_prefix', 'count'),
            help='Prefix type for multiple files'
        )
        
        parser.add_argument(
            '--data_schema',
            required=True,
            help='Data schema as JSON string or path to JSON file'
        )
        
        parser.add_argument(
            '--data_lines',
            type=int,
            default=int(self.defaults.get('data_lines', '1000')),
            help='Number of lines per file'
        )
        
        parser.add_argument(
            '--clear_path',
            action='store_true',
            help='Clear existing files before generation'
        )
        
        parser.add_argument(
            '--multiprocessing',
            type=int,
            default=int(self.defaults.get('multiprocessing', '1')),
            help='Number of processes for parallel generation'
        )
        
        return parser.parse_args()
    
    def validate_arguments(self, args):
        if os.path.exists(args.path_to_save_files) and not os.path.isdir(args.path_to_save_files):
            self.generator.logger.error(f"Path exists but is not a directory: {args.path_to_save_files}")
            sys.exit(1)
        
        if args.files_count != 0:
            os.makedirs(args.path_to_save_files, exist_ok=True)
        
        if args.files_count < 0:
            self.generator.logger.error("files_count must be >= 0")
            sys.exit(1)
        
        if args.data_lines < 1:
            self.generator.logger.error("data_lines must be >= 1")
            sys.exit(1)
        
        if args.multiprocessing < 1:
            self.generator.logger.error("multiprocessing must be >= 1")
            sys.exit(1)
        
        cpu_count = os.cpu_count() or 1
        if args.multiprocessing > cpu_count:
            self.generator.logger.warning(f"Reducing multiprocessing from {args.multiprocessing} to {cpu_count}")
            args.multiprocessing = cpu_count
        
        args.data_schema = self.generator.parse_schema(args.data_schema)
    
    def generate_data_parallel(self, args):
        if args.files_count == 0:
            for i in range(args.data_lines):
                line = self.generator.generate_line(args.data_schema)
                print(json.dumps(line))
            return

        files_per_process = max(1, args.files_count // args.multiprocessing)

        self.generator.logger.info(f"Starting {args.multiprocessing} processes for {args.files_count} files")

        with multiprocessing.Pool(processes=args.multiprocessing) as pool:
            results = []
            for i in range(args.multiprocessing):
                start_idx = i * files_per_process
                end_idx = start_idx + files_per_process
                if i == args.multiprocessing - 1:
                    end_idx = args.files_count

                files_to_generate = end_idx - start_idx
                if files_to_generate > 0:
                    result = pool.apply_async(
                        self.generate_files_chunk,
                        (args, start_idx, files_to_generate)
                    )
                    results.append(result)

            for result in results:
                result.get()
    
    def generate_files_chunk(self, args, start_index, num_files):
        generator = DataGenerator(self.defaults)
        for i in range(num_files):
            generator.generate_file(args, start_index + i, args.files_count)
    
    def run(self):
        try:
            args = self.parse_arguments()
            self.generator.logger.info("Starting data generation")
            
            if args.clear_path:
                self.generator.clear_path(args)
            
            if args.multiprocessing > 1 and args.files_count > 1:
                self.generate_data_parallel(args)
            else:
                if args.files_count == 0:
                    for i in range(args.data_lines):
                        line = self.generator.generate_line(args.data_schema)
                        print(json.dumps(line))
                else:
                    for i in range(args.files_count):
                        self.generator.generate_file(args, i, args.files_count)
            
            self.generator.logger.info("Data generation completed successfully")
            
        except KeyboardInterrupt:
            self.generator.logger.info("Generation interrupted by user")
            sys.exit(1)
        except Exception:
            self.generator.logger.exception("Unexpected error")
            sys.exit(1)


def main():
    generator = MagicGenerator()
    generator.run()


if __name__ == '__main__':
    main()

