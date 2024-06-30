import os
import sys
import argparse
import logging
from datetime import datetime
from collections import defaultdict, Counter
from configparser import ConfigParser
import json

# External dependencies
from exiftool import ExifToolHelper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AnalyzeTakeout:
    def __init__(self, root_folder, export_folder):
        self.root_folder = root_folder
        self.export_folder = export_folder
        self.known_export_folder = os.path.join(export_folder, 'known_file_analysis')
        self.unknown_files_folder = os.path.join(export_folder, 'unknown_file_analysis')
        self.file_counts = defaultdict(int)
        self.file_sizes = []
        self.creation_dates = []
        self.unknown_files = []
        logging.info(f"Initialized AnalyzeTakeout with root_folder={root_folder} and export_folder={export_folder}")

    def load_config(self):
        config = ConfigParser()
        config.read('config.ini')
        picture_extensions = config.get('Extensions', 'PICTURE_EXTENSIONS').split(', ')
        video_extensions = config.get('Extensions', 'VIDEO_EXTENSIONS').split(', ')
        return {
            'picture_extensions': picture_extensions,
            'video_extensions': video_extensions
        }

    def escape_special_characters(self, file_path):
        """Escape special characters in the file path."""
        return file_path.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t").replace(" ", "\\ ")

    def get_photo_date(self, file_path):
        """Extract creation date from photo metadata."""
        try:
            with ExifToolHelper() as et:
                metadata = et.get_tags(files=file_path, tags='EXIF:DateTimeOriginal')
                if metadata and 'EXIF:DateTimeOriginal' in metadata[0]:
                    return datetime.strptime(metadata[0]['EXIF:DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')
        except Exception as e:
            logging.error(f"Failed to get photo date for {file_path}: {e}")
        return None

    def analyze_files(self, extensions):
        """Analyze files in the given folder."""
        logging.info("Starting file analysis...")
        for root, _, files in os.walk(self.root_folder):
            for file in files:
                file_extension = os.path.splitext(file)[1].lower()
                if file_extension in extensions:
                    self.process_file(os.path.join(root, file), file_extension)
                else:
                    self.unknown_files.append(os.path.join(root, file))

        logging.info("File analysis completed.")

    def process_file(self, file_path, file_extension):
        """Process a single file and update the metrics."""
        try:
            file_size = os.path.getsize(file_path)
            creation_date = self.get_photo_date(file_path) or datetime.fromtimestamp(os.path.getctime(file_path))

            self.file_counts[file_extension] += 1
            self.file_sizes.append(file_size)
            self.creation_dates.append(creation_date)
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}")
            self.unknown_files.append(file_path)

    def export_metrics(self):
        """Export the collected metrics to files."""
        os.makedirs(self.known_export_folder, exist_ok=True)
        self.export_file_counts()
        self.export_file_size_distribution()
        self.export_creation_date_distribution()

    def export_file_counts(self):
        """Export the counts of known media files."""
        path = os.path.join(self.known_export_folder, "file_counts.json")
        with open(path, 'w') as f:
            json.dump(self.file_counts, f, indent=4)
        logging.info(f"Exported file counts to {path}")

    def format_size(self, size):
        """Format file size to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

    def export_file_size_distribution(self):
        """Export the file size distribution."""
        total_size = sum(self.file_sizes)
        average_size = total_size / len(self.file_sizes) if self.file_sizes else 0

        size_ranges = [
            (0, 10 * 1024, "0-10KB"),
            (10 * 1024, 100 * 1024, "10KB-100KB"),
            (100 * 1024, 1024 * 1024, "100KB-1MB"),
            (1024 * 1024, 10 * 1024 * 1024, "1MB-10MB"),
            (10 * 1024 * 1024, 100 * 1024 * 1024, "10MB-100MB"),
            (100 * 1024 * 1024, 1024 * 1024 * 1024, "100MB-1GB"),
            (1024 * 1024 * 1024, float('inf'), "1GB+")
        ]

        size_distribution = Counter()
        for size in self.file_sizes:
            for lower, upper, label in size_ranges:
                if lower <= size < upper:
                    size_distribution[label] += 1
                    break

        distribution = {
            "total_size": self.format_size(total_size),
            "average_size": self.format_size(average_size),
            "size_distribution": size_distribution
        }

        path = os.path.join(self.known_export_folder, "file_size_distribution.json")
        with open(path, 'w') as f:
            json.dump(distribution, f, indent=4)
        logging.info(f"Exported file size distribution to {path}")

    def export_creation_date_distribution(self):
        """Export the distribution of file creation dates."""
        date_counts = defaultdict(int)
        for date in self.creation_dates:
            key = date.strftime('%Y-%m')
            date_counts[key] += 1

        path = os.path.join(self.known_export_folder, "creation_date_distribution.json")
        with open(path, 'w') as f:
            json.dump(date_counts, f, indent=4)
        logging.info(f"Exported creation date distribution to {path}")

    def export_unknown_files(self):
        """Export unknown file paths to a text file."""
        logging.info("Exporting unknown files...")
        os.makedirs(self.unknown_files_folder, exist_ok=True)
        export_path = os.path.join(self.unknown_files_folder, "unknown_files.txt")
        try:
            with open(export_path, 'w') as f:
                for file_path in self.unknown_files:
                    abs_path = os.path.abspath(file_path)
                    f.write(self.escape_special_characters(abs_path) + '\n')
            logging.info(f"Unknown files exported to {export_path}")
        except IOError as e:
            logging.error(f"Error writing to file {export_path}: {e}")
            sys.exit(1)

def main():
    """Main function to parse arguments and run the analysis."""
    parser = argparse.ArgumentParser(description="Count pictures and videos in a folder.")
    parser.add_argument('folder', type=str, help='Path to the folder')
    parser.add_argument('export_folder', type=str, help='Folder to export metrics')

    args = parser.parse_args()

    analyzer = AnalyzeTakeout(args.folder, args.export_folder)
    config = analyzer.load_config()
    extensions = set(config['picture_extensions'] + config['video_extensions'])
    analyzer.analyze_files(extensions)
    analyzer.export_metrics()
    analyzer.export_unknown_files()

if __name__ == "__main__":
    main()