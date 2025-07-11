#!/usr/bin/env python3
"""
High-Performance Combined API Key Scraper
Uses async processing for maximum speed and efficiency
"""

import asyncio
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from typing import List, Dict, Optional

from async_github_scraper import AsyncGitHubScraper
from async_gitlab_scraper import AsyncGitLabScraper

def safe_print(text):
    """Safe print function that handles emojis on Windows"""
    try:
        print(text)
    except UnicodeEncodeError:
        import unicodedata
        normalized = unicodedata.normalize('NFKD', text)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        print(ascii_text)

class HighPerformanceCombinedScraper:
    def __init__(self, github_tokens: List[str] = None, gitlab_tokens: List[str] = None, gitlab_url: str = "https://gitlab.com"):
        self.github_tokens = github_tokens or []
        self.gitlab_tokens = gitlab_tokens or []
        self.gitlab_url = gitlab_url
        
        # Initialize scrapers
        self.github_scraper = AsyncGitHubScraper(self.github_tokens) if self.github_tokens else None
        self.gitlab_scraper = AsyncGitLabScraper(self.gitlab_tokens, gitlab_url) if self.gitlab_tokens else None
        
        # Performance tracking
        self.start_time = None
        self.total_keys_found = 0
        self.repos_scanned = 0
        
        # Provider information
        self.providers = {
            'openai': {'name': 'OpenAI', 'emoji': '🤖'},
            'claude': {'name': 'Claude/Anthropic', 'emoji': '🧠'},
            'gemini': {'name': 'Gemini/Google', 'emoji': '💎'}
        }
        
    async def search_all_platforms_async(self, selected_providers: List[str] = None, max_pages_github: int = 5, max_pages_gitlab: int = 3) -> Dict[str, List[Dict]]:
        """Search all platforms asynchronously for maximum performance"""
        safe_print("🚀 HIGH-PERFORMANCE ASYNC SEARCH STARTING...")
        safe_print("⚡ Using concurrent processing for maximum speed!")
        
        self.start_time = time.time()
        
        # Prepare tasks for concurrent execution
        tasks = []
        
        # Determine which providers to search
        providers_to_search = selected_providers or ['openai', 'claude', 'gemini']
        
        safe_print(f"🎯 Searching for: {', '.join([self.providers[p]['emoji'] + ' ' + self.providers[p]['name'] for p in providers_to_search])}")
        
        # GitHub tasks
        if self.github_scraper:
            for provider in providers_to_search:
                task_name = f"github_{provider}"
                task = asyncio.create_task(
                    self.github_scraper.search_and_scan(provider, max_pages_github),
                    name=task_name
                )
                tasks.append((task, 'github', provider))
                
        # GitLab tasks  
        if self.gitlab_scraper:
            for provider in providers_to_search:
                task_name = f"gitlab_{provider}"
                task = asyncio.create_task(
                    self.gitlab_scraper.search_and_scan(provider, max_pages_gitlab),
                    name=task_name
                )
                tasks.append((task, 'gitlab', provider))
        
        if not tasks:
            safe_print("❌ No platforms available to search!")
            return {}
            
        safe_print(f"⚡ Running {len(tasks)} concurrent search tasks...")
        
        # Execute all tasks concurrently
        results = {}
        completed_tasks = 0
        
        for task, platform, provider in tasks:
            try:
                keys = await task
                key = f"{platform}_{provider}"
                results[key] = keys
                completed_tasks += 1
                
                safe_print(f"✅ [{completed_tasks}/{len(tasks)}] {platform.title()} {provider} search complete: {len(keys)} keys found")
                
            except Exception as e:
                safe_print(f"❌ Error in {platform} {provider} search: {e}")
                results[f"{platform}_{provider}"] = []
        
        # Calculate performance stats
        elapsed_time = time.time() - self.start_time
        total_keys = sum(len(keys) for keys in results.values())
        
        safe_print(f"\n🎯 ASYNC SEARCH COMPLETE!")
        safe_print(f"⏱️  Total time: {elapsed_time:.2f} seconds")
        safe_print(f"🔑 Total keys found: {total_keys}")
        safe_print(f"⚡ Keys per second: {total_keys/elapsed_time:.2f}")
        
        return results
        
    def save_results_by_provider(self, results: Dict[str, List[Dict]]):
        """Save results to provider-specific files with performance info"""
        provider_totals = {'openai': 0, 'claude': 0, 'gemini': 0}
        
        # Group results by provider across platforms
        by_provider = {'openai': [], 'claude': [], 'gemini': []}
        
        for key, keys in results.items():
            platform, provider = key.split('_', 1)
            by_provider[provider].extend(keys)
            provider_totals[provider] += len(keys)
            
        # Save each provider's keys
        for provider, keys in by_provider.items():
            if keys:
                filename = f"{provider}_combined_async.txt"
                self.save_provider_keys(keys, provider, filename)
                
        # Create summary file
        self.create_performance_summary(provider_totals, results)
        
    def save_provider_keys(self, keys: List[Dict], provider: str, filename: str):
        """Save keys for a specific provider"""
        emoji = self.providers[provider]['emoji']
        provider_name = self.providers[provider]['name']
        
        # Sort keys by platform then by repository/project name
        keys.sort(key=lambda x: (x.get('platform', ''), x.get('repository', x.get('project_name', ''))))
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{emoji} {provider_name.upper()} API KEYS - HIGH-PERFORMANCE SCAN\n")
            f.write(f"Scan completed: {datetime.now()}\n")
            f.write(f"Total keys found: {len(keys)}\n")
            f.write("=" * 80 + "\n\n")
            
            for key_info in keys:
                platform = 'GitHub' if 'repository' in key_info else 'GitLab'
                platform_emoji = '🐙' if platform == 'GitHub' else '🦊'
                
                f.write(f"{emoji}{platform_emoji} {provider_name.upper()} KEY FOUND:\n")
                f.write(f"Key: {key_info['key']}\n")
                f.write(f"Provider: {provider.upper()}\n")
                f.write(f"Platform: {platform}\n")
                
                if 'repository' in key_info:
                    # GitHub format
                    f.write(f"Repository: {key_info['repository']}\n")
                    f.write(f"File: {key_info['file_path']}\n")
                    f.write(f"URL: {key_info['file_url']}\n")
                else:
                    # GitLab format
                    f.write(f"Project: {key_info['project_name']}\n")
                    f.write(f"File: {key_info['file_path']}\n")
                    f.write(f"URL: {key_info['gitlab_url']}\n")
                    
                f.write(f"Found at: {key_info['found_at']}\n")
                f.write("-" * 60 + "\n\n")
                
        safe_print(f"💾 Saved {len(keys)} {provider} keys to {filename}")
        
    def create_performance_summary(self, provider_totals: Dict[str, int], results: Dict[str, List[Dict]]):
        """Create a performance summary file"""
        filename = "performance_summary.txt"
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        total_keys = sum(provider_totals.values())
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("🚀 HIGH-PERFORMANCE API KEY SCAN SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Scan completed: {datetime.now()}\n")
            f.write(f"Total scan time: {elapsed_time:.2f} seconds\n")
            f.write(f"Total keys found: {total_keys}\n")
            f.write(f"Keys per second: {total_keys/elapsed_time:.2f}\n\n")
            
            f.write("RESULTS BY PROVIDER:\n")
            f.write("-" * 30 + "\n")
            for provider, count in provider_totals.items():
                emoji = self.providers[provider]['emoji']
                name = self.providers[provider]['name']
                f.write(f"{emoji} {name}: {count} keys\n")
                
            f.write("\nRESULTS BY PLATFORM:\n")
            f.write("-" * 30 + "\n")
            
            github_total = sum(len(keys) for key, keys in results.items() if key.startswith('github_'))
            gitlab_total = sum(len(keys) for key, keys in results.items() if key.startswith('gitlab_'))
            
            f.write(f"🐙 GitHub: {github_total} keys\n")
            f.write(f"🦊 GitLab: {gitlab_total} keys\n")
            
            f.write("\nDETAILED BREAKDOWN:\n")
            f.write("-" * 30 + "\n")
            for key, keys in results.items():
                platform, provider = key.split('_', 1)
                emoji = self.providers[provider]['emoji']
                platform_emoji = '🐙' if platform == 'github' else '🦊'
                f.write(f"{platform_emoji}{emoji} {platform.title()} {provider.title()}: {len(keys)} keys\n")
                
        safe_print(f"📊 Performance summary saved to {filename}")
        
    def print_performance_stats(self, results: Dict[str, List[Dict]]):
        """Print performance statistics"""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        total_keys = sum(len(keys) for keys in results.values())
        
        safe_print("\n" + "=" * 70)
        safe_print("🎯 HIGH-PERFORMANCE SCAN RESULTS")
        safe_print("=" * 70)
        safe_print(f"⏱️  Total scan time: {elapsed_time:.2f} seconds")
        safe_print(f"🔑 Total keys found: {total_keys}")
        safe_print(f"⚡ Average keys per second: {total_keys/elapsed_time:.2f}")
        
        # Platform breakdown
        github_total = sum(len(keys) for key, keys in results.items() if key.startswith('github_'))
        gitlab_total = sum(len(keys) for key, keys in results.items() if key.startswith('gitlab_'))
        
        safe_print(f"\n📊 Platform Breakdown:")
        safe_print(f"   🐙 GitHub: {github_total} keys")
        safe_print(f"   🦊 GitLab: {gitlab_total} keys")
        
        # Provider breakdown
        provider_totals = {'openai': 0, 'claude': 0, 'gemini': 0}
        for key, keys in results.items():
            _, provider = key.split('_', 1)
            provider_totals[provider] += len(keys)
            
        safe_print(f"\n🎯 Provider Breakdown:")
        for provider, total in provider_totals.items():
            emoji = self.providers[provider]['emoji']
            name = self.providers[provider]['name']
            safe_print(f"   {emoji} {name}: {total} keys")
            
        safe_print("=" * 70)

def load_tokens_from_env():
    """Load tokens from .env file"""
    load_dotenv()
    
    # GitHub tokens
    github_tokens_str = os.getenv('GITHUB_TOKENS', '')
    github_tokens = [token.strip() for token in github_tokens_str.split(',') if token.strip()] if github_tokens_str else []
    
    # GitLab tokens  
    gitlab_tokens_str = os.getenv('GITLAB_TOKENS', '')
    gitlab_tokens = [token.strip() for token in gitlab_tokens_str.split(',') if token.strip()] if gitlab_tokens_str else []
    
    # GitLab URL
    gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.com')
    
    return {
        'github_tokens': github_tokens,
        'gitlab_tokens': gitlab_tokens,
        'gitlab_url': gitlab_url
    }

async def main():
    """High-performance main function"""
    safe_print("🚀 HIGH-PERFORMANCE COMBINED API KEY SCRAPER")
    safe_print("⚡ Async + Concurrent + Smart Filtering = Maximum Speed!")
    safe_print("=" * 70)
    
    # Load configuration
    config = load_tokens_from_env()
    github_tokens = config['github_tokens']
    gitlab_tokens = config['gitlab_tokens']
    gitlab_url = config['gitlab_url']
    
    # Display configuration
    safe_print(f"\n📁 Configuration:")
    safe_print(f"   🐙 GitHub tokens: {len(github_tokens)}")
    safe_print(f"   🦊 GitLab tokens: {len(gitlab_tokens)}")
    safe_print(f"   🌐 GitLab URL: {gitlab_url}")
    
    if not github_tokens and not gitlab_tokens:
        safe_print("❌ No tokens found! Please configure .env file.")
        return
        
    # Provider selection
    safe_print("\n🔑 Select API Key Providers:")
    safe_print("1. 🤖 OpenAI only")
    safe_print("2. 🧠 Claude only") 
    safe_print("3. 💎 Gemini only")
    safe_print("4. 🤖🧠 OpenAI + Claude")
    safe_print("5. 🤖💎 OpenAI + Gemini")
    safe_print("6. 🧠💎 Claude + Gemini")
    safe_print("7. 🤖🧠💎 All providers (RECOMMENDED)")
    
    try:
        choice = int(input("Enter choice (1-7) [7]: ").strip() or "7")
    except ValueError:
        choice = 7
        
    provider_mappings = {
        1: ['openai'],
        2: ['claude'], 
        3: ['gemini'],
        4: ['openai', 'claude'],
        5: ['openai', 'gemini'],
        6: ['claude', 'gemini'],
        7: ['openai', 'claude', 'gemini']
    }
    
    selected_providers = provider_mappings.get(choice, ['openai', 'claude', 'gemini'])
    
    # Search configuration
    safe_print(f"\n⚙️  Search Configuration:")
    try:
        max_pages_github = int(input("GitHub pages to scan (1-10) [5]: ").strip() or "5")
        max_pages_github = max(1, min(10, max_pages_github))
    except ValueError:
        max_pages_github = 5
        
    try:
        max_pages_gitlab = int(input("GitLab pages to scan (1-5) [3]: ").strip() or "3")
        max_pages_gitlab = max(1, min(5, max_pages_gitlab))
    except ValueError:
        max_pages_gitlab = 3
        
    # Initialize scraper
    scraper = HighPerformanceCombinedScraper(github_tokens, gitlab_tokens, gitlab_url)
    
    # Run async search
    safe_print(f"\n🚀 Starting high-performance async search...")
    safe_print(f"⚡ This will be MUCH faster than the old version!")
    
    results = await scraper.search_all_platforms_async(
        selected_providers=selected_providers,
        max_pages_github=max_pages_github,
        max_pages_gitlab=max_pages_gitlab
    )
    
    # Save and display results
    scraper.save_results_by_provider(results)
    scraper.print_performance_stats(results)
    
    safe_print(f"\n✅ High-performance scan complete!")
    safe_print(f"📁 Results saved to provider-specific files")

if __name__ == "__main__":
    asyncio.run(main())
