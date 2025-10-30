import pytest
import json
from magicgenerator import DataGenerator, MagicGenerator


class TestDataGenerator:
    def setup_method(self):
        self.generator = DataGenerator()
    
    def test_parse_schema_from_string(self):
        schema_str = '{"name": "str:rand", "age": "int:rand(1, 100)"}'
        schema = self.generator.parse_schema(schema_str)
        assert schema["name"] == "str:rand"
        assert schema["age"] == "int:rand(1, 100)"
    
    def test_parse_schema_from_file(self, tmp_path):
        schema_data = {"date": "timestamp:", "type": "str:['a','b']"}
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(json.dumps(schema_data))
        
        schema = self.generator.parse_schema(str(schema_file))
        assert schema["date"] == "timestamp:"
        assert schema["type"] == "str:['a','b']"
    
    @pytest.mark.parametrize("field_type,value_spec,expected_type", [
        ("timestamp", "", str),
        ("str", "rand", str),
        ("str", "fixed_value", str),
        ("str", "", str),
        ("int", "rand", int),
        ("int", "rand(1,10)", int),
        ("int", "42", int),
        ("int", "", type(None)),
    ])
    def test_generate_value_types(self, field_type, value_spec, expected_type):
        result = self.generator.generate_value(field_type, value_spec)
        assert isinstance(result, expected_type)
    
    @pytest.mark.parametrize("schema_str", [
        '{"name": "str:rand", "age": "int:rand(1,50)"}',
        '{"type": "str:[\\"client\\",\\"partner\\"]", "active": "int:[0,1]"}',
        '{"id": "int:rand", "description": "str:"}',
    ])
    def test_generate_line_valid_schemas(self, schema_str):
        schema = json.loads(schema_str)
        line = self.generator.generate_line(schema)
        
        for key in schema.keys():
            assert key in line
            assert line[key] is not None
    
    def test_generate_string_rand(self):
        result = self.generator.generate_string("rand")
        assert isinstance(result, str)
        assert len(result) == 36  
    
    def test_generate_string_from_list(self):
        result = self.generator.generate_string('["a","b","c"]')
        assert result in ["a", "b", "c"]
    
    def test_generate_integer_rand_range(self):
        result = self.generator.generate_integer("rand(5, 10)")
        assert 5 <= result <= 10
    
    def test_generate_integer_from_list(self):
        result = self.generator.generate_integer("[1,2,3,4,5]")
        assert result in [1, 2, 3, 4, 5]


class DummyArgs:
    def __init__(self, path_to_save_files, files_count, file_name, file_prefix, 
                 data_schema, data_lines, clear_path, multiprocessing):
        self.path_to_save_files = path_to_save_files
        self.files_count = files_count
        self.file_name = file_name
        self.file_prefix = file_prefix
        self.data_schema = data_schema
        self.data_lines = data_lines
        self.clear_path = clear_path
        self.multiprocessing = multiprocessing


class TestMagicGenerator:
    def setup_method(self):
        self.magic_gen = MagicGenerator()
    
    def test_clear_path_action(self, tmp_path):
        test_files = [
            tmp_path / "data_1.json",
            tmp_path / "data_2.json",
            tmp_path / "other_file.txt"
        ]
        
        for file in test_files:
            file.write_text("test content")
        
        args = DummyArgs(
            path_to_save_files=str(tmp_path),
            files_count=1,
            file_name="data",
            file_prefix="count",
            data_schema={},
            data_lines=1,
            clear_path=True,
            multiprocessing=1
        )
        
        self.magic_gen.generator.clear_path(args)

        assert not (tmp_path / "data_1.json").exists()
        assert not (tmp_path / "data_2.json").exists()
        assert (tmp_path / "other_file.txt").exists()
    
    def test_file_generation_single(self, tmp_path):
        schema = {"name": "str:rand", "count": "int:rand(1,5)"}
        
        args = DummyArgs(
            path_to_save_files=str(tmp_path),
            files_count=1,
            file_name="test",
            file_prefix="count",
            data_schema=schema,
            data_lines=5,
            clear_path=False,
            multiprocessing=1
        )
        
        result = self.magic_gen.generator.generate_file(args, 0, 1)
        assert result == "test.json"
        assert (tmp_path / "test.json").exists()
        
        with open(tmp_path / "test.json", 'r') as f:
            lines = f.readlines()
            assert len(lines) == 5
            for line in lines:
                data = json.loads(line.strip())
                assert "name" in data
                assert "count" in data
    
    def test_multiprocessing_file_count(self, tmp_path):
        schema = {"id": "int:rand"}
        
        args = DummyArgs(
            path_to_save_files=str(tmp_path),
            files_count=4,
            file_name="multi",
            file_prefix="count",
            data_schema=schema,
            data_lines=10,
            clear_path=False,
            multiprocessing=2
        )
        
        self.magic_gen.generator.clear_path(args)
        
        for i in range(args.files_count):
            self.magic_gen.generator.generate_file(args, i, args.files_count)
        
        expected_files = {"multi_1.json", "multi_2.json", "multi_3.json", "multi_4.json"}
        actual_files = {f.name for f in tmp_path.glob("*.json")}
        assert expected_files == actual_files
    
    def test_filename_generation(self, tmp_path):
        generator = DataGenerator()
        
        args = DummyArgs(
            path_to_save_files=str(tmp_path),
            file_name="data",
            file_prefix="count",
            files_count=3,
            data_lines=1,
            data_schema={},
            clear_path=False,
            multiprocessing=1
        )
        
        filename1 = generator.generate_filename(args, 0, 3)
        assert filename1 == "data_1.json"
        
        filename2 = generator.generate_filename(args, 1, 3)
        assert filename2 == "data_2.json"
        
        args.files_count = 1
        filename_single = generator.generate_filename(args, 0, 1)
        assert filename_single == "data.json"
    
    def test_invalid_schema_handling(self):
        generator = DataGenerator()

        with pytest.raises(ValueError):
            generator.parse_schema("invalid json")
        
        with pytest.raises(SystemExit):
            generator.generate_value("invalid_type", "value")
    
    def test_console_output_mode(self, capsys):
        schema = {"message": "str:hello"}
        
        args = DummyArgs(
            path_to_save_files=".",
            files_count=0,
            file_name="test",
            file_prefix="count", 
            data_schema=schema,
            data_lines=3,
            clear_path=False,
            multiprocessing=1
        )
        
        lines = []
        for i in range(3):
            line = self.magic_gen.generator.generate_line(schema)
            lines.append(json.dumps(line))
            print(json.dumps(line))
        
        captured = capsys.readouterr()
        output_lines = captured.out.strip().split('\n')
        
        assert len(output_lines) == 3
        for line in output_lines:
            data = json.loads(line)
            assert data["message"] == "hello"
    
    def test_schema_validation(self):
        generator = DataGenerator()
        
        valid_schema = {"name": "str:rand", "age": "int:25"}
        generator.validate_schema(valid_schema)  

        with pytest.raises(ValueError):
            generator.validate_schema("not a dict")

        with pytest.raises(ValueError):
            generator.validate_schema({"name": 123})

        with pytest.raises(ValueError):
            generator.validate_schema({"name": "str_rand"})


class TestIntegration:
    def test_end_to_end_generation(self, tmp_path):
        schema = {
            "timestamp": "timestamp:",
            "user_id": "str:rand",
            "category": "str:['A','B','C']",
            "score": "int:rand(1,100)"
        }
        
        schema_file = tmp_path / "test_schema.json"
        schema_file.write_text(json.dumps(schema))
        
        magic_gen = MagicGenerator()
        
        generator = DataGenerator()
        parsed_schema = generator.parse_schema(str(schema_file))
        
        for i in range(3):
            line = generator.generate_line(parsed_schema)
            assert "timestamp" in line
            assert "user_id" in line
            assert "category" in line
            assert "score" in line
            assert line["category"] in ['A', 'B', 'C']
            assert 1 <= line["score"] <= 100


if __name__ == '__main__':
    pytest.main([__file__, "-v"])

