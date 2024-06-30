import os
import json
import pytest
from analyze_takeout import AnalyzeTakeout

@pytest.fixture
def setup_environment(tmp_path):
    # Create a temporary directory structure and sample files
    sample_files = tmp_path / "sample_files"
    sample_files.mkdir()
    
    # Sample known files
    (sample_files / "sample.jpg").write_text("This is a sample jpg file.")
    (sample_files / "sample.heic").write_text("This is a sample png file.")
    
    # Sample unknown file
    (sample_files / "README.md").write_text("This is an unknown file.")
    
    return str(sample_files)

def test_load_config():
    analyzer = AnalyzeTakeout("", "")
    config = analyzer.load_config()
    assert '.jpg' in config['picture_extensions']
    assert '.mp4' in config['video_extensions']

def test_analyze_files(setup_environment):
    analyzer = AnalyzeTakeout(setup_environment, setup_environment)
    config = analyzer.load_config()
    extensions = set(config['picture_extensions'] + config['video_extensions'])
    
    analyzer.analyze_files(extensions)
    
    assert len(analyzer.file_counts) == 2  # Two known extensions
    assert analyzer.file_counts['.jpg'] == 1
    assert analyzer.file_counts['.heic'] == 1
    assert len(analyzer.unknown_files) == 1  # One unknown file

def test_export_metrics(setup_environment):
    analyzer = AnalyzeTakeout(setup_environment, setup_environment)
    config = analyzer.load_config()
    extensions = set(config['picture_extensions'] + config['video_extensions'])
    
    analyzer.analyze_files(extensions)
    analyzer.export_metrics()
    
    file_counts_path = os.path.join(analyzer.known_export_folder, "file_counts.json")
    with open(file_counts_path, 'r') as f:
        file_counts = json.load(f)
    
    assert file_counts['.jpg'] == 1
    assert file_counts['.heic'] == 1

def test_export_unknown_files(setup_environment):
    analyzer = AnalyzeTakeout(setup_environment, setup_environment)
    config = analyzer.load_config()
    extensions = set(config['picture_extensions'] + config['video_extensions'])
    
    analyzer.analyze_files(extensions)
    analyzer.export_unknown_files()
    
    unknown_files_path = os.path.join(analyzer.unknown_files_folder, "unknown_files.txt")
    with open(unknown_files_path, 'r') as f:
        unknown_files = f.read().strip().split('\n')
    
    assert len(unknown_files) == 1
    assert "README.md" in unknown_files[0]
