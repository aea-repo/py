#!/usr/bin/env python3
"""
Chrome Bookmark Link Checker
Imports Chrome bookmarks, tests URLs for HTTP 200 status, and removes broken links.
"""

import json
import requests
from urllib.parse import urlparse
import argparse
import sys
from typing import Dict, List, Any
import time

class BookmarkChecker:
    def __init__(self, timeout: int = 10, delay: float = 0.5):
        """
        Initialize the bookmark checker.
        
        Args:
            timeout: Request timeout in seconds
            delay: Delay between requests in seconds
        """
        self.timeout = timeout
        self.delay = delay
        self.session = requests.Session()
        # Set a user agent to avoid being blocked
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def load_bookmarks(self, file_path: str) -> Dict[str, Any]:
        """Load Chrome bookmarks from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Bookmark file '{file_path}' not found.")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in bookmark file '{file_path}'.")
            sys.exit(1)
    
    def save_bookmarks(self, bookmarks: Dict[str, Any], file_path: str) -> None:
        """Save bookmarks back to JSON file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(bookmarks, f, indent=2, ensure_ascii=False)
    
    def test_url(self, url: str) -> bool:
        """
        Test if URL returns HTTP 200 status code.
        
        Args:
            url: URL to test
            
        Returns:
            True if URL returns 200, False otherwise
        """
        try:
            # Validate URL format
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                print(f"  ❌ Invalid URL format: {url}")
                return False
            
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if response.status_code == 200:
                print(f"  ✅ OK: {url}")
                return True
            else:
                print(f"  ❌ Status {response.status_code}: {url}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error accessing {url}: {str(e)}")
            return False
    
    def process_bookmark_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Recursively process bookmark items and remove broken links.
        
        Args:
            items: List of bookmark items
            
        Returns:
            List of bookmark items with broken links removed
        """
        valid_items = []
        
        for item in items:
            if item.get('type') == 'url':
                # This is a bookmark link
                url = item.get('url', '')
                name = item.get('name', 'Unnamed')
                
                print(f"Testing: {name}")
                if self.test_url(url):
                    valid_items.append(item)
                else:
                    print(f"  🗑️  Removing broken bookmark: {name}")
                
                # Add delay between requests to be respectful
                time.sleep(self.delay)
                
            elif item.get('type') == 'folder':
                # This is a folder, process its children recursively
                folder_name = item.get('name', 'Unnamed Folder')
                print(f"\n📁 Processing folder: {folder_name}")
                
                children = item.get('children', [])
                valid_children = self.process_bookmark_items(children)
                
                # Keep folder even if it becomes empty (user might want to refill it)
                item['children'] = valid_children
                valid_items.append(item)
                
                print(f"📁 Finished folder: {folder_name}")
        
        return valid_items
    
    def clean_bookmarks(self, input_file: str, output_file: str = None) -> None:
        """
        Main function to clean bookmarks.
        
        Args:
            input_file: Path to Chrome bookmarks file
            output_file: Path to save cleaned bookmarks (optional)
        """
        if output_file is None:
            output_file = input_file.replace('.json', '_cleaned.json')
        
        print(f"Loading bookmarks from: {input_file}")
        bookmarks = self.load_bookmarks(input_file)
        
        # Chrome bookmarks structure: roots -> bookmark_bar/other -> children
        total_processed = 0
        total_removed = 0
        
        for root_name, root_data in bookmarks.get('roots', {}).items():
            if isinstance(root_data, dict) and 'children' in root_data:
                print(f"\n🔍 Processing bookmark root: {root_name}")
                
                original_count = self.count_urls(root_data['children'])
                cleaned_children = self.process_bookmark_items(root_data['children'])
                new_count = self.count_urls(cleaned_children)
                
                root_data['children'] = cleaned_children
                
                removed = original_count - new_count
                total_processed += original_count
                total_removed += removed
                
                print(f"Root '{root_name}': {original_count} → {new_count} bookmarks ({removed} removed)")
        
        print(f"\n📊 Summary:")
        print(f"  Total bookmarks processed: {total_processed}")
        print(f"  Broken bookmarks removed: {total_removed}")
        print(f"  Valid bookmarks remaining: {total_processed - total_removed}")
        
        print(f"\n💾 Saving cleaned bookmarks to: {output_file}")
        self.save_bookmarks(bookmarks, output_file)
        print("✅ Done!")
    
    def count_urls(self, items: List[Dict[str, Any]]) -> int:
        """Count total number of URL bookmarks in items."""
        count = 0
        for item in items:
            if item.get('type') == 'url':
                count += 1
            elif item.get('type') == 'folder':
                count += self.count_urls(item.get('children', []))
        return count


def main():
    parser = argparse.ArgumentParser(
        description='Clean Chrome bookmarks by removing broken links',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bookmark_checker.py bookmarks.json
  python bookmark_checker.py bookmarks.json -o clean_bookmarks.json
  python bookmark_checker.py bookmarks.json --timeout 15 --delay 1.0
        """
    )
    
    parser.add_argument('input_file', help='Path to Chrome bookmarks JSON file')
    parser.add_argument('-o', '--output', help='Output file path (default: input_file_cleaned.json)')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds (default: 10)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests in seconds (default: 0.5)')
    
    args = parser.parse_args()
    
    print("🔗 Chrome Bookmark Link Checker")
    print("=" * 40)
    
    checker = BookmarkChecker(timeout=args.timeout, delay=args.delay)
    checker.clean_bookmarks(args.input_file, args.output)


if __name__ == '__main__':
    main()