#!/usr/bin/env python3
"""
High-Performance Async GitHub API Scraper
Optimized for speed with concurrent processing, smart filtering, and efficient rate limiting
"""

import asyncio
import aiohttp
import re
import time
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple
import os
from pathlib import Path

class AsyncGitHubScraper:
    def __init__(self, tokens: List[str]):
        self.tokens = [token.strip() for token in tokens if token.strip()]
        self.current_token_index = 0
        self.session = None
        
        # Performance optimizations
        self.max_concurrent_requests = 10
        self.max_file_size = 1024 * 1024  # 1MB limit
        self.scan_extensions = {'.py', '.js', '.env', '.config', '.txt', '.md', '.json', '.yaml', '.yml', '.ini', '.conf'}
        
        # API key patterns
        self.key_patterns = {
            'openai': re.compile(r"sk-[a-zA-Z0-9]{48}"),
            'claude': re.compile(r"sk-ant-[a-zA-Z0-9_-]{30,50}"),
            'gemini': re.compile(r"AIza[a-zA-Z0-9_-]{35}")
        }
        
        # Rate limiting per token
        self.token_limits = {token: {'remaining': 5000, 'reset_time': 0} for token in self.tokens}
        
        # Repository cache to avoid duplicates
        self.cache_db = 'repo_cache.db'
        self.init_cache_db()
        
        # Results tracking
        self.found_keys = []
        self.processed_repos = set()
        
    def init_cache_db(self):
        """Initialize SQLite database for repository caching"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scanned_repos (
                repo_id INTEGER PRIMARY KEY,
                full_name TEXT UNIQUE,
                last_scanned TIMESTAMP,
                keys_found INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
        
    def is_repo_recently_scanned(self, repo_id: int, hours: int = 24) -> bool:
        """Check if repository was scanned recently"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cursor.execute(
            'SELECT last_scanned FROM scanned_repos WHERE repo_id = ? AND last_scanned > ?',
            (repo_id, cutoff_time)
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None
        
    def mark_repo_scanned(self, repo_id: int, full_name: str, keys_found: int = 0):
        """Mark repository as scanned"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO scanned_repos (repo_id, full_name, last_scanned, keys_found)
            VALUES (?, ?, ?, ?)
        ''', (repo_id, full_name, datetime.now(), keys_found))
        conn.commit()
        conn.close()
        
    def should_scan_file(self, file_path: str, file_size: int) -> bool:
        """Smart file filtering to skip irrelevant files"""
        # Skip if too large
        if file_size > self.max_file_size:
            return False
            
        # Check extension
        file_ext = Path(file_path).suffix.lower()
        if file_ext and file_ext not in self.scan_extensions:
            return False
            
        # Skip common non-text files
        skip_patterns = [
            'node_modules/', 'venv/', '__pycache__/', '.git/',
            'dist/', 'build/', 'target/', 'vendor/',
            '.jpg', '.png', '.gif', '.pdf', '.zip', '.tar'
        ]
        
        file_path_lower = file_path.lower()
        for pattern in skip_patterns:
            if pattern in file_path_lower:
                return False
                
        return True
        
    def get_best_token(self) -> str:
        """Get token with highest remaining rate limit"""
        best_token = None
        best_remaining = 0
        
        for token in self.tokens:
            limits = self.token_limits[token]
            if limits['remaining'] > best_remaining:
                best_remaining = limits['remaining']
                best_token = token
                
        return best_token or self.tokens[0]
        
    def update_rate_limits(self, token: str, headers: dict):
        """Update rate limit info from response headers"""
        if 'x-ratelimit-remaining' in headers:
            self.token_limits[token]['remaining'] = int(headers['x-ratelimit-remaining'])
        if 'x-ratelimit-reset' in headers:
            self.token_limits[token]['reset_time'] = int(headers['x-ratelimit-reset'])
            
    async def create_session(self):
        """Create aiohttp session with connection pooling"""
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=20,  # Per host limit
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'High-Performance-API-Key-Scanner/2.0'}
        )
        
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            
    async def make_request(self, url: str, params: dict = None) -> Optional[dict]:
        """Make async HTTP request with automatic rate limiting and token rotation"""
        token = self.get_best_token()
        
        # Check if we need to wait for rate limit reset
        limits = self.token_limits[token]
        if limits['remaining'] < 10 and limits['reset_time'] > time.time():
            wait_time = limits['reset_time'] - time.time() + 1
            if wait_time > 0:
                await asyncio.sleep(min(wait_time, 60))  # Max 1 minute wait
                
        headers = {'Authorization': f'token {token}'}
        
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                self.update_rate_limits(token, response.headers)
                
                if response.status == 200:
                    return await response.json()
                elif response.status == 403:
                    # Rate limited, try different token
                    print(f"⚠️  Rate limited on token {token[:8]}...")
                    self.token_limits[token]['remaining'] = 0
                    return None
                elif response.status == 404:
                    return None
                else:
                    print(f"❌ HTTP {response.status} for {url}")
                    return None
                    
        except asyncio.TimeoutError:
            print(f"⏰ Timeout for {url}")
            return None
        except Exception as e:
            print(f"❌ Error for {url}: {e}")
            return None
            
    def extract_keys_from_content(self, content: str, provider: str = None) -> List[Dict]:
        """Extract API keys from content with early exit optimization"""
        keys = []
        
        # If specific provider requested, only search for that
        if provider and provider in self.key_patterns:
            pattern = self.key_patterns[provider]
            matches = pattern.findall(content)
            for match in set(matches):  # Remove duplicates
                keys.append({
                    'key': match,
                    'provider': provider,
                    'pattern': provider
                })
        else:
            # Search all patterns but exit early if content is too large
            if len(content) > 500000:  # 500KB limit for full scan
                content = content[:500000]
                
            for provider_name, pattern in self.key_patterns.items():
                matches = pattern.findall(content)
                for match in set(matches):
                    keys.append({
                        'key': match,
                        'provider': provider_name,
                        'pattern': provider_name
                    })
                    
        return keys
        
    async def get_file_content(self, repo_full_name: str, file_path: str, sha: str) -> Optional[str]:
        """Get file content via GitHub API"""
        url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
        params = {'ref': sha}
        
        data = await self.make_request(url, params)
        if not data:
            return None
            
        try:
            # GitHub returns base64 encoded content
            import base64
            content = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
            return content
        except Exception as e:
            print(f"❌ Error decoding file {file_path}: {e}")
            return None
            
    async def search_repositories(self, query: str, max_pages: int = 5, provider: str = None) -> List[dict]:
        """Search repositories with optimized queries"""
        all_repos = []
        
        # Optimized search queries
        search_queries = {
            'openai': [
                f'{query} "sk-" language:python',
                f'{query} "sk-proj" language:javascript', 
                f'{query} "OPENAI_API_KEY" language:python',
                f'{query} "openai.api_key" language:python'
            ],
            'claude': [
                f'{query} "sk-ant-" language:python',
                f'{query} "anthropic" "api" language:python',
                f'{query} "ANTHROPIC_API_KEY"'
            ],
            'gemini': [
                f'{query} "AIza" language:python',
                f'{query} "GOOGLE_API_KEY" language:python',
                f'{query} "gemini" "api" language:python'
            ]
        }
        
        queries_to_use = []
        if provider and provider in search_queries:
            queries_to_use = search_queries[provider]
        else:
            # Use all queries but limit to avoid hitting limits
            for prov_queries in search_queries.values():
                queries_to_use.extend(prov_queries[:2])  # Limit per provider
                
        # Execute searches concurrently
        tasks = []
        for search_query in queries_to_use[:6]:  # Limit total queries
            task = self.search_single_query(search_query, max_pages)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all repositories
        seen_repos = set()
        for result in results:
            if isinstance(result, list):
                for repo in result:
                    repo_id = repo.get('id')
                    if repo_id and repo_id not in seen_repos:
                        seen_repos.add(repo_id)
                        all_repos.append(repo)
                        
        return all_repos
        
    async def search_single_query(self, query: str, max_pages: int) -> List[dict]:
        """Search a single query across multiple pages"""
        repos = []
        
        for page in range(1, max_pages + 1):
            url = "https://api.github.com/search/repositories"
            params = {
                'q': query,
                'sort': 'updated',
                'order': 'desc',
                'page': page,
                'per_page': 30
            }
            
            data = await self.make_request(url, params)
            if not data or 'items' not in data:
                break
                
            page_repos = data['items']
            if not page_repos:
                break
                
            repos.extend(page_repos)
            
            # Small delay between pages
            await asyncio.sleep(0.1)
            
        return repos
        
    async def scan_repository(self, repo: dict, provider: str = None) -> List[Dict]:
        """Scan a repository for API keys with smart filtering"""
        repo_id = repo['id']
        repo_name = repo['full_name']
        
        # Skip if recently scanned
        if self.is_repo_recently_scanned(repo_id):
            return []
            
        print(f"🔍 Scanning {repo_name}...")
        
        # Get repository contents
        url = f"https://api.github.com/repos/{repo_name}/contents"
        contents = await self.make_request(url)
        
        if not contents:
            return []
            
        # Filter files to scan
        files_to_scan = []
        for item in contents:
            if item['type'] == 'file':
                file_path = item['path']
                file_size = item.get('size', 0)
                
                if self.should_scan_file(file_path, file_size):
                    files_to_scan.append(item)
                    
        # Limit files per repo to avoid overwhelming
        files_to_scan = files_to_scan[:20]
        
        # Scan files concurrently
        tasks = []
        for file_item in files_to_scan:
            task = self.scan_file(repo_name, file_item, provider)
            tasks.append(task)
            
        file_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        repo_keys = []
        for result in file_results:
            if isinstance(result, list):
                repo_keys.extend(result)
                
        # Mark as scanned
        self.mark_repo_scanned(repo_id, repo_name, len(repo_keys))
        
        return repo_keys
        
    async def scan_file(self, repo_name: str, file_item: dict, provider: str = None) -> List[Dict]:
        """Scan individual file for API keys"""
        file_path = file_item['path']
        
        # Get file content
        content = await self.get_file_content(repo_name, file_path, file_item['sha'])
        if not content:
            return []
            
        # Extract keys
        keys = self.extract_keys_from_content(content, provider)
        
        # Add metadata
        for key_info in keys:
            key_info.update({
                'repository': repo_name,
                'file_path': file_path,
                'file_url': file_item.get('html_url', ''),
                'found_at': datetime.now().isoformat()
            })
            
        return keys
        
    async def search_and_scan(self, provider: str = None, max_pages: int = 5) -> List[Dict]:
        """Main search and scan function"""
        print(f"🚀 Starting async search for {provider or 'all'} API keys...")
        
        await self.create_session()
        
        try:
            # Search repositories
            query = "api key" if not provider else f"{provider} api"
            repos = await self.search_repositories(query, max_pages, provider)
            
            print(f"📊 Found {len(repos)} repositories to scan")
            
            # Scan repositories concurrently with semaphore for rate limiting
            semaphore = asyncio.Semaphore(self.max_concurrent_requests)
            
            async def scan_with_semaphore(repo):
                async with semaphore:
                    return await self.scan_repository(repo, provider)
                    
            tasks = [scan_with_semaphore(repo) for repo in repos]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect all keys
            all_keys = []
            for result in results:
                if isinstance(result, list):
                    all_keys.extend(result)
                    
            self.found_keys.extend(all_keys)
            print(f"✅ Scan complete! Found {len(all_keys)} keys")
            
            return all_keys
            
        finally:
            await self.close_session()
            
    def save_keys_to_file(self, keys: List[Dict], provider: str = None):
        """Save keys to provider-specific files"""
        if not keys:
            return
            
        # Group by provider
        by_provider = {}
        for key_info in keys:
            key_provider = key_info['provider']
            if key_provider not in by_provider:
                by_provider[key_provider] = []
            by_provider[key_provider].append(key_info)
            
        # Save to separate files
        for key_provider, provider_keys in by_provider.items():
            filename = f"{key_provider}_combined_async.txt"
            
            with open(filename, 'a', encoding='utf-8') as f:
                for key_info in provider_keys:
                    emoji = {'openai': '🤖', 'claude': '🧠', 'gemini': '💎'}.get(key_provider, '🔑')
                    f.write(f"{emoji}🐙 {key_provider.upper()} KEY FOUND:\n")
                    f.write(f"Key: {key_info['key']}\n")
                    f.write(f"Provider: {key_provider.upper()}\n")
                    f.write(f"Platform: GitHub\n")
                    f.write(f"Repository: {key_info['repository']}\n")
                    f.write(f"File: {key_info['file_path']}\n")
                    f.write(f"URL: {key_info['file_url']}\n")
                    f.write(f"Found at: {key_info['found_at']}\n")
                    f.write("-" * 60 + "\n\n")
                    
            print(f"💾 Saved {len(provider_keys)} {key_provider} keys to {filename}")

async def main():
    """Example usage"""
    # This would be called from your main scraper
    tokens = ['your_github_token_here']  # Add your tokens
    scraper = AsyncGitHubScraper(tokens)
    
    # Search for OpenAI keys
    keys = await scraper.search_and_scan('openai', max_pages=3)
    scraper.save_keys_to_file(keys, 'openai')

if __name__ == "__main__":
    asyncio.run(main())
