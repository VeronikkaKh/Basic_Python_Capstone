import argparse
import configparser
import json
import multiprocessing
import os
import sys
from datagenerator import DataGenerator


class MagicGenerator:
    def __init__(self):
        self.defaults = self._load_defaults()
        self.generator = DataGenerator(self.defaults)

    def _load_defaults(self):
        cfg = configparser.ConfigParser()
        default_file = 'default.ini'
        defaults = {
            'path_to_save_files': '.', 'files_count': '1', 'file_name': 'data',
            'file_prefix': 'count', 'data_lines': '1000', 'multiprocessing': '1',
            'log_file': 'magicgenerator.log'
        }
        if os.path.exists(default_file):
            cfg.read(default_file)
            return dict(cfg['DEFAULTS'])
        cfg['DEFAULTS'] = defaults
        with open(default_file, 'w') as f:
            cfg.write(f)
        return defaults

    def parse_arguments(self):
        parser = argparse.ArgumentParser(
            description='MagicGenerator - Test data generator',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        parser.add_argument('path_to_save_files', nargs='?',
                            default=self.defaults.get('path_to_save_files', '.'),
                            help='Path to save generated files')
        parser.add_argument('--files_count', type=int,
                            default=int(self.defaults.get('files_count', '1')),
                            help='Number of JSON files to generate')
        parser.add_argument('--file_name', default=self.defaults.get('file_name', 'data'),
                            help='Base filename for generated files')
        parser.add_argument('--file_prefix', choices=['count', 'random', 'uuid'],
                            default=self.defaults.get('file_prefix', 'count'),
                            help='Prefix type for multiple files')
        parser.add_argument('--data_schema', required=True,
                            help='Data schema as JSON string or path to JSON file')
        parser.add_argument('--data_lines', type=int,
                            default=int(self.defaults.get('data_lines', '1000')),
                            help='Number of lines per file')
        parser.add_argument('--clear_path', action='store_true',
                            help='Clear existing files before generation')
        parser.add_argument('--multiprocessing', type=int,
                            default=int(self.defaults.get('multiprocessing', '1')),
                            help='Number of processes for parallel generation')
        return parser.parse_args()

    def validate_arguments(self, args):
        if os.path.exists(args.path_to_save_files) and not os.path.isdir(args.path_to_save_files):
            self.generator.logger.error(f"Path exists but is not a directory: {args.path_to_save_files}")
            sys.exit(1)
        if args.files_count != 0:
            os.makedirs(args.path_to_save_files, exist_ok=True)
        if args.files_count < 0 or args.data_lines < 1 or args.multiprocessing < 0:
            self.generator.logger.error("Invalid numeric arguments: files_count>=0, data_lines>=1, multiprocessing>=0")
            sys.exit(1)
        cpu = os.cpu_count() or 1
        if args.multiprocessing > cpu:
            self.generator.logger.warning(f"Reducing multiprocessing from {args.multiprocessing} to {cpu}")
            args.multiprocessing = cpu
        try:
            args.data_schema = self.generator.parse_schema(args.data_schema)
        except ValueError as e:
            self.generator.logger.error(str(e))
            sys.exit(1)

    def generate_data_parallel(self, args):
        if args.files_count == 0:
            for i in range(args.data_lines):
                line = self.generator.generate_line(args.data_schema)
                print(json.dumps(line))
            return
        files_per_proc = max(1, args.files_count // args.multiprocessing)
        self.generator.logger.info(f"Starting {args.multiprocessing} processes for {args.files_count} files")
        with multiprocessing.Pool(processes=args.multiprocessing) as pool:
            tasks = []
            for i in range(args.multiprocessing):
                start = i * files_per_proc
                end = min(args.files_count, (i + 1) * files_per_proc)
                if start < end:
                    tasks.append(pool.apply_async(self.generate_files_chunk, (args, start, end - start)))
            for r in tasks:
                r.get()

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
