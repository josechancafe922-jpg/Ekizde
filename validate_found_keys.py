#!/usr/bin/env python3
"""
API Key File Validator
Interactive script to validate API keys from provider-specific files
Supports OpenAI, Claude/Anthropic, and Gemini/Google API keys
"""

import requests
import time
import re
import os
import glob
from datetime import datetime

def safe_print(text):
    """Safely print text with emoji support on Windows"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback for Windows without proper Unicode support
        import unicodedata
        normalized = unicodedata.normalize('NFKD', text)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        print(ascii_text)

class FileKeyValidator:
    def __init__(self):
        self.results = {
            'valid': [],
            'invalid': [],
            'unknown': []
        }
        
        # Define patterns for different API key types
        self.key_patterns = {
            'openai': r"sk-[a-zA-Z0-9]{48}",
            'claude': r"sk-ant-[a-zA-Z0-9_-]{30,50}",
            'gemini': r"AIza[a-zA-Z0-9_-]{35}"
        }
        
        # Provider information
        self.providers = {
            'openai': {
                'name': 'OpenAI',
                'emoji': '🤖',
                'files': ['openai_combined.txt', 'openai_continuous.txt']
            },
            'claude': {
                'name': 'Claude/Anthropic',
                'emoji': '🧠',
                'files': ['claude_combined.txt', 'claude_continuous.txt']
            },
            'gemini': {
                'name': 'Gemini/Google',
                'emoji': '💎',
                'files': ['gemini_combined.txt', 'gemini_continuous.txt']
            }
        }
    
    def get_available_files(self):
        """Get all available key files in the current directory"""
        available_files = []
        
        # Look for provider-specific files
        for provider, info in self.providers.items():
            for filename in info['files']:
                if os.path.exists(filename):
                    available_files.append({
                        'filename': filename,
                        'provider': provider,
                        'name': info['name'],
                        'emoji': info['emoji']
                    })
        
        # Also check for legacy files
        legacy_files = ['found_combined_keys.txt', 'found_github_keys.txt']
        for filename in legacy_files:
            if os.path.exists(filename):
                available_files.append({
                    'filename': filename,
                    'provider': 'mixed',
                    'name': 'Mixed/Legacy',
                    'emoji': '🔑'
                })
        
        return available_files
    
    def detect_provider_from_filename(self, filename):
        """Detect provider from filename"""
        filename_lower = filename.lower()
        if 'openai' in filename_lower:
            return 'openai'
        elif 'claude' in filename_lower:
            return 'claude'
        elif 'gemini' in filename_lower:
            return 'gemini'
        else:
            return 'mixed'
    
    def detect_key_type(self, key):
        """Detect the type of API key based on its format"""
        for key_type, pattern in self.key_patterns.items():
            if re.match(pattern, key):
                return key_type
        return "unknown"
    
    
    def extract_keys_from_file(self, filename, expected_provider=None):
        """Extract all API keys from a specific file"""
        if not os.path.exists(filename):
            safe_print(f"❌ File '{filename}' not found!")
            return []
        
        safe_print(f"📖 Reading keys from {filename}...")
        
        keys_found = []
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # If expected provider is specified, only look for that type
            if expected_provider and expected_provider in self.key_patterns:
                pattern = self.key_patterns[expected_provider]
                found_keys = re.findall(pattern, content)
                for key in set(found_keys):  # Remove duplicates
                    keys_found.append({
                        'key': key,
                        'type': expected_provider,
                        'source_file': filename
                    })
            else:
                # Extract all types of keys
                all_keys = set()  # Use set to avoid duplicates
                
                # Extract OpenAI keys
                openai_keys = re.findall(self.key_patterns['openai'], content)
                for key in openai_keys:
                    all_keys.add((key, 'openai'))
                
                # Extract Claude keys
                claude_keys = re.findall(self.key_patterns['claude'], content)
                for key in claude_keys:
                    all_keys.add((key, 'claude'))
                
                # Extract Gemini keys
                gemini_keys = re.findall(self.key_patterns['gemini'], content)
                for key in gemini_keys:
                    all_keys.add((key, 'gemini'))
                
                # Convert to list format
                for key, key_type in all_keys:
                    keys_found.append({
                        'key': key,
                        'type': key_type,
                        'source_file': filename
                    })
            
            safe_print(f"📊 Found {len(keys_found)} unique API keys in {filename}")
            
            # Count by type
            if keys_found:
                type_counts = {}
                for key_info in keys_found:
                    key_type = key_info['type']
                    type_counts[key_type] = type_counts.get(key_type, 0) + 1
                
                for key_type, count in type_counts.items():
                    emoji = self.providers.get(key_type, {}).get('emoji', '🔑')
                    name = self.providers.get(key_type, {}).get('name', key_type.upper())
                    safe_print(f"   {emoji} {name} keys: {count}")
            
        except Exception as e:
            safe_print(f"❌ Error reading file: {e}")
            return []
        
        return keys_found
    
    def validate_openai_key(self, key):
        """Validate OpenAI API key"""
        try:
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            
            # Try to get models list (lightweight request)
            response = requests.get(
                "https://api.openai.com/v1/models",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Valid - API responds successfully"
            elif response.status_code == 401:
                return False, "Invalid - Authentication failed"
            elif response.status_code == 403:
                return False, "Invalid - Forbidden (possibly revoked)"
            elif response.status_code == 429:
                return None, "Rate limited - Try again later"
            else:
                return None, f"Unknown status code: {response.status_code}"
        
        except requests.exceptions.Timeout:
            return None, "Timeout - API not responding"
        except requests.exceptions.ConnectionError:
            return None, "Connection error"
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def validate_claude_key(self, key):
        """Validate Claude/Anthropic API key"""
        try:
            headers = {
                "x-api-key": key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Try a simple completion request
            data = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "Hi"}]
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Valid - API responds successfully"
            elif response.status_code == 401:
                return False, "Invalid - Authentication failed"
            elif response.status_code == 403:
                return False, "Invalid - Forbidden (possibly revoked)"
            elif response.status_code == 429:
                return None, "Rate limited - Try again later"
            else:
                return None, f"Unknown status code: {response.status_code}"
        
        except requests.exceptions.Timeout:
            return None, "Timeout - API not responding"
        except requests.exceptions.ConnectionError:
            return None, "Connection error"
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def validate_gemini_key(self, key):
        """Validate Gemini/Google API key"""
        try:
            # Try to get models list
            response = requests.get(
                f"https://generativelanguage.googleapis.com/v1/models?key={key}",
                timeout=10
            )
            
            if response.status_code == 200:
                return True, "Valid - API responds successfully"
            elif response.status_code == 400:
                return False, "Invalid - Bad request (invalid key)"
            elif response.status_code == 403:
                return False, "Invalid - Forbidden (possibly revoked)"
            elif response.status_code == 429:
                return None, "Rate limited - Try again later"
            else:
                return None, f"Unknown status code: {response.status_code}"
        
        except requests.exceptions.Timeout:
            return None, "Timeout - API not responding"
        except requests.exceptions.ConnectionError:
            return None, "Connection error"
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def validate_key(self, key, key_type):
        """Validate a single API key based on its type"""
        if key_type == "openai":
            return self.validate_openai_key(key)
        elif key_type == "claude":
            return self.validate_claude_key(key)
        elif key_type == "gemini":
            return self.validate_gemini_key(key)
        else:
            return None, "Unknown key type"
    
    def validate_all_keys(self, keys, source_description=""):
        """Validate all keys from the list"""
        if not keys:
            safe_print("❌ No keys to validate!")
            return
            
        safe_print(f"\n🔍 VALIDATING API KEYS{source_description}...")
        safe_print("=" * 70)
        safe_print("⚠️  This may take several minutes depending on the number of keys")
        safe_print("⏱️  Using 1-second delays between requests to respect rate limits")
        safe_print("=" * 70)
        
        for i, key_info in enumerate(keys, 1):
            key = key_info['key']
            key_type = key_info['type']
            source_file = key_info.get('source_file', 'unknown')
            
            safe_print(f"\n[{i}/{len(keys)}] Testing {key_type.upper()} key: {key[:20]}... (from {source_file})")
            
            # Validate the key
            is_valid, message = self.validate_key(key, key_type)
            
            # Store result with additional info
            result_info = {
                'key': key,
                'type': key_type,
                'message': message,
                'source_file': source_file,
                'timestamp': datetime.now().isoformat()
            }
            
            if is_valid is True:
                self.results['valid'].append(result_info)
                safe_print(f"   ✅ VALID - {message}")
            elif is_valid is False:
                self.results['invalid'].append(result_info)
                safe_print(f"   ❌ INVALID - {message}")
            else:
                self.results['unknown'].append(result_info)
                safe_print(f"   ❓ UNKNOWN - {message}")
            
            # Rate limiting between validation attempts
            if i < len(keys):  # Don't sleep after the last key
                time.sleep(1)
        
        self.print_results()
        self.save_results()
        
    def validate_files(self, selected_files):
        """Validate keys from selected files"""
        all_keys = []
        
        for file_info in selected_files:
            filename = file_info['filename']
            provider = file_info['provider']
            
            # For provider-specific files, only extract that provider's keys
            expected_provider = provider if provider != 'mixed' else None
            
            keys = self.extract_keys_from_file(filename, expected_provider)
            all_keys.extend(keys)
        
        if not all_keys:
            safe_print("❌ No API keys found in the selected files!")
            return
        
        # Remove duplicates while preserving source file info
        unique_keys = []
        seen_keys = set()
        
        for key_info in all_keys:
            key = key_info['key']
            if key not in seen_keys:
                seen_keys.add(key)
                unique_keys.append(key_info)
        
        file_names = [f['filename'] for f in selected_files]
        source_desc = f" from {', '.join(file_names)}"
        
        safe_print(f"\n📊 Total unique keys to validate: {len(unique_keys)}")
        
        # Ask user to confirm
        confirm = input("\nDo you want to start validation? (y/n): ").strip().lower()
        
        if confirm != 'y':
            safe_print("Validation cancelled.")
            return
        
        # Start validation
        self.validate_all_keys(unique_keys, source_desc)
    
    def print_results(self):
        """Print validation results summary"""
        total_tested = len(self.results['valid']) + len(self.results['invalid']) + len(self.results['unknown'])
        
        safe_print("\n" + "=" * 70)
        safe_print("🎯 VALIDATION RESULTS SUMMARY")
        safe_print("=" * 70)
        safe_print(f"✅ Valid keys: {len(self.results['valid'])}")
        safe_print(f"❌ Invalid keys: {len(self.results['invalid'])}")
        safe_print(f"❓ Unknown status: {len(self.results['unknown'])}")
        safe_print(f"📊 Total tested: {total_tested}")
        safe_print("=" * 70)
        
        if self.results['valid']:
            safe_print(f"\n🚨 WORKING API KEYS FOUND:")
            for result in self.results['valid']:
                provider_emoji = self.providers.get(result['type'], {}).get('emoji', '🔑')
                safe_print(f"   {provider_emoji} {result['key']} ({result['type'].upper()}) - from {result.get('source_file', 'unknown')}")
                
        if self.results['invalid']:
            safe_print(f"\n❌ INVALID KEYS: {len(self.results['invalid'])}")
            
        if self.results['unknown']:
            safe_print(f"\n❓ UNKNOWN STATUS KEYS: {len(self.results['unknown'])}")
            safe_print("   These may be rate limited or have network issues")
    
    def save_results(self):
        """Save validation results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save all results
        results_filename = f"validation_results_{timestamp}.txt"
        with open(results_filename, "w", encoding='utf-8') as f:
            f.write(f"API Key Validation Results - {datetime.now()}\n")
            f.write("=" * 70 + "\n\n")
            
            total_tested = len(self.results['valid']) + len(self.results['invalid']) + len(self.results['unknown'])
            f.write(f"SUMMARY:\n")
            f.write(f"Valid keys: {len(self.results['valid'])}\n")
            f.write(f"Invalid keys: {len(self.results['invalid'])}\n")
            f.write(f"Unknown status: {len(self.results['unknown'])}\n")
            f.write(f"Total tested: {total_tested}\n\n")
            
            # Write results by category
            for status, results in self.results.items():
                if results:
                    f.write(f"{status.upper()} KEYS ({len(results)}):\n")
                    f.write("-" * 50 + "\n")
                    for result in results:
                        f.write(f"Key: {result['key']}\n")
                        f.write(f"Type: {result['type'].upper()}\n")
                        f.write(f"Source File: {result.get('source_file', 'unknown')}\n")
                        f.write(f"Status: {result['message']}\n")
                        f.write(f"Tested: {result['timestamp']}\n")
                        f.write("-" * 30 + "\n")
                    f.write("\n")
        
        safe_print(f"\n📄 Full results saved to: {results_filename}")
        
        # Save valid keys separately if any found
        if self.results['valid']:
            valid_filename = f"working_keys_{timestamp}.txt"
            with open(valid_filename, "w", encoding='utf-8') as f:
                f.write(f"WORKING API KEYS - {datetime.now()}\n")
                f.write("=" * 50 + "\n\n")
                f.write("⚠️  WARNING: These are working API keys!\n")
                f.write("Handle with care and respect provider usage policies.\n\n")
                
                # Group by provider
                by_provider = {}
                for result in self.results['valid']:
                    key_type = result['type']
                    if key_type not in by_provider:
                        by_provider[key_type] = []
                    by_provider[key_type].append(result)
                
                for provider, keys in by_provider.items():
                    provider_name = self.providers.get(provider, {}).get('name', provider.upper())
                    provider_emoji = self.providers.get(provider, {}).get('emoji', '🔑')
                    f.write(f"{provider_emoji} {provider_name} KEYS ({len(keys)}):\n")
                    f.write("-" * 40 + "\n")
                    for result in keys:
                        f.write(f"{result['key']} (from {result.get('source_file', 'unknown')})\n")
                    f.write("\n")
            
            safe_print(f"📄 Working keys saved to: {valid_filename}")
            safe_print(f"⚠️  WARNING: These are working API keys! Use responsibly!")
    
    def show_file_selection_menu(self):
        """Show interactive menu for file selection"""
        available_files = self.get_available_files()
        
        if not available_files:
            safe_print("❌ No key files found!")
            safe_print("Run the scrapers first to generate key files.")
            return None
        
        safe_print("\n📁 AVAILABLE KEY FILES:")
        safe_print("=" * 50)
        
        for i, file_info in enumerate(available_files, 1):
            emoji = file_info['emoji']
            name = file_info['name']
            filename = file_info['filename']
            
            # Get file size
            try:
                file_size = os.path.getsize(filename)
                if file_size > 0:
                    size_str = f"({file_size} bytes)"
                else:
                    size_str = "(empty)"
            except:
                size_str = "(error)"
            
            safe_print(f"{i}. {emoji} {name} - {filename} {size_str}")
        
        safe_print(f"{len(available_files) + 1}. 🔍 All files")
        safe_print("0. ❌ Cancel")
        
        while True:
            try:
                choice = input(f"\nSelect files to validate (comma-separated numbers, e.g., 1,2,3): ").strip()
                
                if choice == '0':
                    return None
                
                if choice == str(len(available_files) + 1):
                    return available_files
                
                # Parse comma-separated choices
                selected_indices = []
                for part in choice.split(','):
                    idx = int(part.strip())
                    if 1 <= idx <= len(available_files):
                        selected_indices.append(idx - 1)
                    else:
                        safe_print(f"❌ Invalid choice: {idx}")
                        raise ValueError()
                
                if not selected_indices:
                    safe_print("❌ No valid selections made!")
                    continue
                
                selected_files = [available_files[i] for i in selected_indices]
                
                safe_print(f"\n✅ Selected {len(selected_files)} file(s):")
                for file_info in selected_files:
                    safe_print(f"   {file_info['emoji']} {file_info['filename']}")
                
                return selected_files
                
            except (ValueError, IndexError):
                safe_print("❌ Invalid input! Please enter numbers separated by commas.")
                continue

def main():
    safe_print("🔍 API KEY FILE VALIDATOR")
    safe_print("Interactive validation of API keys from provider-specific files")
    safe_print("=" * 70)
    
    validator = FileKeyValidator()
    
    # Show file selection menu
    selected_files = validator.show_file_selection_menu()
    
    if not selected_files:
        safe_print("❌ No files selected. Exiting.")
        return
    
    # Validate the selected files
    validator.validate_files(selected_files)
    
    safe_print(f"\n✅ Validation complete!")
    safe_print(f"📁 Results saved in timestamped files")

if __name__ == "__main__":
    main()
