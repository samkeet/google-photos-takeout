import os
import shutil
import argparse
import json
import sys
import logging
from configparser import ConfigParser
from collections import defaultdict
from exiftool import ExifToolHelper

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CleanupTakeout:
    def __init__(self, root_folder, output_file, exif_metadata_file, dry_run=False):
        self.root_folder = root_folder
        self.output_file = output_file
        self.exif_metadata_file = exif_metadata_file
        self.dry_run = dry_run
        self.photo_extensions, self.video_extensions = self.load_config()
        self.all_extensions = self.photo_extensions + self.video_extensions

    def load_config(self):
        """Load extensions from a config file."""
        config = ConfigParser()
        config.read('config.ini')
        picture_extensions = tuple(config.get('Extensions', 'PICTURE_EXTENSIONS').split(', '))
        video_extensions = tuple(config.get('Extensions', 'VIDEO_EXTENSIONS').split(', '))
        return picture_extensions, video_extensions

    def find_files_by_extension(self):
        """Walk through the folder structure and categorize files by their extension."""
        file_dict = defaultdict(list)
        for root, _, files in os.walk(self.root_folder):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.all_extensions:
                    file_dict[ext].append(os.path.join(root, file))
        return dict(file_dict)

    def extract_metadata(self, files):
        """Extract metadata for files using ExifTool."""
        metadata = {}
        with ExifToolHelper() as et:
            metadata = et.get_metadata_batch(files)
        return metadata

    def delete_empty_folders(self):
        """Delete empty directories and print which directories are kept due to containing media files."""
        for root, dirs, files in os.walk(self.root_folder, topdown=False):
            if not files and not dirs:
                if not self.dry_run:
                    os.rmdir(root)
                    logging.info(f"Deleted empty folder: {root}")
                else:
                    logging.info(f"Would delete empty folder: {root}")
            else:
                logging.info(f"Would keep folder: {root}")

    def process_folders(self):
        """Process each folder to find media files, extract metadata, and optionally delete empty folders."""
        files_by_extension = self.find_files_by_extension()
        all_media_files = [file for files in files_by_extension.values() for file in files]
        metadata = self.extract_metadata(all_media_files)

        if not self.dry_run:
            self.delete_empty_folders()

        # Output processing results
        with open(self.output_file, 'w') as f:
            json.dump(list(files_by_extension.keys()), f, indent=4)

        with open(self.exif_metadata_file, 'w') as f:
            json.dump(metadata, f, indent=4)

def main():
    parser = argparse.ArgumentParser(description="Organize media files and clean up folders.")
    parser.add_argument('root_folder', type=str, help='Root folder to clean up')
    parser.add_argument('output_file', type=str, help='Output file for listing extensions found')
    parser.add_argument('exif_metadata_file', type=str, help='Output file for EXIF metadata')
    parser.add_argument('--dry-run', action='store_true', help='Run the script without making any changes')

    args = parser.parse_args()

    if not os.path.isdir(args.root_folder):
        logging.error("Invalid directory specified.")
        sys.exit(1)

    cleanup = CleanupTakeout(args.root_folder, args.output_file, args.exif_metadata_file, args.dry_run)
    cleanup.process_folders()

if __name__ == "__main__":
    main()