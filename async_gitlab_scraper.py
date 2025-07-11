#!/usr/bin/env python3
"""
High-Performance Async GitLab API Scraper
Optimized for speed with concurrent processing and smart filtering
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

class AsyncGitLabScraper:
    def __init__(self, tokens: List[str], gitlab_url: str = "https://gitlab.com"):
        self.tokens = [token.strip() for token in tokens if token.strip()]
        self.gitlab_url = gitlab_url
        self.base_url = f"{gitlab_url}/api/v4"
        self.session = None
        
        # Performance optimizations
        self.max_concurrent_requests = 8  # GitLab is more restrictive
        self.max_file_size = 1024 * 1024  # 1MB limit
        self.scan_extensions = {'.py', '.js', '.env', '.config', '.txt', '.md', '.json', '.yaml', '.yml', '.ini', '.conf'}
        
        # API key patterns
        self.key_patterns = {
            'openai': re.compile(r"sk-[a-zA-Z0-9]{48}"),
            'claude': re.compile(r"sk-ant-[a-zA-Z0-9_-]{30,50}"),
            'gemini': re.compile(r"AIza[a-zA-Z0-9_-]{35}")
        }
        
        # Rate limiting per token
        self.token_limits = {token: {'remaining': 1000, 'reset_time': 0} for token in self.tokens}
        
        # Repository cache
        self.cache_db = 'gitlab_repo_cache.db'
        self.init_cache_db()
        
        # Results
        self.found_keys = []
        
    def init_cache_db(self):
        """Initialize SQLite database for GitLab repository caching"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gitlab_scanned_repos (
                project_id INTEGER PRIMARY KEY,
                name_with_namespace TEXT,
                last_scanned TIMESTAMP,
                keys_found INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
        
    def is_project_recently_scanned(self, project_id: int, hours: int = 24) -> bool:
        """Check if project was scanned recently"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cursor.execute(
            'SELECT last_scanned FROM gitlab_scanned_repos WHERE project_id = ? AND last_scanned > ?',
            (project_id, cutoff_time)
        )
        result = cursor.fetchone()
        conn.close()
        return result is not None
        
    def mark_project_scanned(self, project_id: int, name_with_namespace: str, keys_found: int = 0):
        """Mark project as scanned"""
        conn = sqlite3.connect(self.cache_db)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO gitlab_scanned_repos (project_id, name_with_namespace, last_scanned, keys_found)
            VALUES (?, ?, ?, ?)
        ''', (project_id, name_with_namespace, datetime.now(), keys_found))
        conn.commit()
        conn.close()
        
    def should_scan_file(self, file_path: str, file_size: int = 0) -> bool:
        """Smart file filtering for GitLab"""
        # Skip if too large
        if file_size > self.max_file_size:
            return False
            
        # Check extension
        file_ext = Path(file_path).suffix.lower()
        if file_ext and file_ext not in self.scan_extensions:
            return False
            
        # Skip common non-text paths
        skip_patterns = [
            'node_modules/', 'venv/', '__pycache__/', '.git/',
            'dist/', 'build/', 'target/', 'vendor/', 'public/',
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
        """Update rate limit info from GitLab response headers"""
        if 'ratelimit-remaining' in headers:
            self.token_limits[token]['remaining'] = int(headers['ratelimit-remaining'])
        if 'ratelimit-reset' in headers:
            self.token_limits[token]['reset_time'] = int(headers['ratelimit-reset'])
            
    async def create_session(self):
        """Create aiohttp session for GitLab"""
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'High-Performance-GitLab-Scanner/2.0'}
        )
        
    async def close_session(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            
    async def make_request(self, url: str, params: dict = None) -> Optional[dict]:
        """Make async HTTP request to GitLab API"""
        token = self.get_best_token()
        
        # Check rate limits
        limits = self.token_limits[token]
        if limits['remaining'] < 5 and limits['reset_time'] > time.time():
            wait_time = limits['reset_time'] - time.time() + 1
            if wait_time > 0:
                await asyncio.sleep(min(wait_time, 60))
                
        headers = {'PRIVATE-TOKEN': token}
        
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                self.update_rate_limits(token, response.headers)
                
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    print(f"⚠️  Rate limited on GitLab token {token[:8]}...")
                    self.token_limits[token]['remaining'] = 0
                    await asyncio.sleep(1)
                    return None
                elif response.status == 404:
                    return None
                else:
                    print(f"❌ GitLab HTTP {response.status} for {url}")
                    return None
                    
        except asyncio.TimeoutError:
            print(f"⏰ GitLab timeout for {url}")
            return None
        except Exception as e:
            print(f"❌ GitLab error for {url}: {e}")
            return None
            
    def extract_keys_from_content(self, content: str, provider: str = None) -> List[Dict]:
        """Extract API keys from content"""
        keys = []
        
        # Limit content size for performance
        if len(content) > 500000:
            content = content[:500000]
            
        if provider and provider in self.key_patterns:
            pattern = self.key_patterns[provider]
            matches = pattern.findall(content)
            for match in set(matches):
                keys.append({
                    'key': match,
                    'provider': provider,
                    'pattern': provider
                })
        else:
            for provider_name, pattern in self.key_patterns.items():
                matches = pattern.findall(content)
                for match in set(matches):
                    keys.append({
                        'key': match,
                        'provider': provider_name,
                        'pattern': provider_name
                    })
                    
        return keys
        
    async def get_file_content(self, project_id: int, file_path: str, ref: str = 'main') -> Optional[str]:
        """Get file content from GitLab"""
        # Try different branch names
        branches = ['main', 'master', 'develop']
        
        for branch in branches:
            url = f"{self.base_url}/projects/{project_id}/repository/files/{file_path.replace('/', '%2F')}/raw"
            params = {'ref': branch}
            
            try:
                token = self.get_best_token()
                headers = {'PRIVATE-TOKEN': token}
                
                async with self.session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        content = await response.text(encoding='utf-8', errors='ignore')
                        return content
                        
            except Exception as e:
                continue
                
        return None
        
    async def search_projects(self, query: str, max_pages: int = 3, provider: str = None) -> List[dict]:
        """Search GitLab projects with optimized queries"""
        projects = []
        
        # Optimized search terms
        search_terms = {
            'openai': ['openai', 'chatgpt', 'gpt', 'sk-'],
            'claude': ['claude', 'anthropic', 'sk-ant'],
            'gemini': ['gemini', 'google ai', 'AIza']
        }
        
        terms_to_use = []
        if provider and provider in search_terms:
            terms_to_use = search_terms[provider]
        else:
            # Use subset of all terms
            for terms in search_terms.values():
                terms_to_use.extend(terms[:2])
                
        # Search with different terms concurrently
        tasks = []
        for term in terms_to_use[:4]:  # Limit concurrent searches
            task = self.search_single_term(term, max_pages)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect unique projects
        seen_projects = set()
        for result in results:
            if isinstance(result, list):
                for project in result:
                    project_id = project.get('id')
                    if project_id and project_id not in seen_projects:
                        seen_projects.add(project_id)
                        projects.append(project)
                        
        return projects
        
    async def search_single_term(self, search_term: str, max_pages: int) -> List[dict]:
        """Search GitLab for a single term"""
        projects = []
        
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/projects"
            params = {
                'search': search_term,
                'order_by': 'last_activity_at',
                'sort': 'desc',
                'visibility': 'public',
                'page': page,
                'per_page': 20
            }
            
            data = await self.make_request(url, params)
            if not data:
                break
                
            if not isinstance(data, list):
                break
                
            projects.extend(data)
            
            # Small delay between pages
            await asyncio.sleep(0.2)
            
        return projects
        
    async def scan_project(self, project: dict, provider: str = None) -> List[Dict]:
        """Scan GitLab project for API keys"""
        project_id = project['id']
        project_name = project['name_with_namespace']
        
        # Skip if recently scanned
        if self.is_project_recently_scanned(project_id):
            return []
            
        print(f"🔍 Scanning GitLab project {project_name}...")
        
        # Get project tree
        url = f"{self.base_url}/projects/{project_id}/repository/tree"
        params = {'recursive': True, 'per_page': 100}
        
        tree_data = await self.make_request(url, params)
        if not tree_data:
            return []
            
        # Filter files to scan
        files_to_scan = []
        for item in tree_data:
            if item['type'] == 'blob':  # Regular file
                file_path = item['path']
                if self.should_scan_file(file_path):
                    files_to_scan.append(item)
                    
        # Limit files per project
        files_to_scan = files_to_scan[:15]
        
        # Scan files concurrently
        tasks = []
        for file_item in files_to_scan:
            task = self.scan_file(project_id, project_name, file_item, provider)
            tasks.append(task)
            
        file_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        project_keys = []
        for result in file_results:
            if isinstance(result, list):
                project_keys.extend(result)
                
        # Mark as scanned
        self.mark_project_scanned(project_id, project_name, len(project_keys))
        
        return project_keys
        
    async def scan_file(self, project_id: int, project_name: str, file_item: dict, provider: str = None) -> List[Dict]:
        """Scan individual file in GitLab project"""
        file_path = file_item['path']
        
        # Get file content
        content = await self.get_file_content(project_id, file_path)
        if not content:
            return []
            
        # Extract keys
        keys = self.extract_keys_from_content(content, provider)
        
        # Add metadata
        for key_info in keys:
            key_info.update({
                'project_id': project_id,
                'project_name': project_name,
                'file_path': file_path,
                'gitlab_url': f"{self.gitlab_url}/{project_name}/-/blob/main/{file_path}",
                'found_at': datetime.now().isoformat()
            })
            
        return keys
        
    async def search_and_scan(self, provider: str = None, max_pages: int = 3) -> List[Dict]:
        """Main GitLab search and scan function"""
        print(f"🚀 Starting async GitLab search for {provider or 'all'} API keys...")
        
        await self.create_session()
        
        try:
            # Search projects
            query = "api" if not provider else provider
            projects = await self.search_projects(query, max_pages, provider)
            
            print(f"📊 Found {len(projects)} GitLab projects to scan")
            
            # Scan projects concurrently with rate limiting
            semaphore = asyncio.Semaphore(self.max_concurrent_requests)
            
            async def scan_with_semaphore(project):
                async with semaphore:
                    return await self.scan_project(project, provider)
                    
            tasks = [scan_with_semaphore(project) for project in projects]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect all keys
            all_keys = []
            for result in results:
                if isinstance(result, list):
                    all_keys.extend(result)
                    
            self.found_keys.extend(all_keys)
            print(f"✅ GitLab scan complete! Found {len(all_keys)} keys")
            
            return all_keys
            
        finally:
            await self.close_session()
            
    def save_keys_to_file(self, keys: List[Dict], provider: str = None):
        """Save GitLab keys to provider-specific files"""
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
            filename = f"{key_provider}_gitlab_async.txt"
            
            with open(filename, 'a', encoding='utf-8') as f:
                for key_info in provider_keys:
                    emoji = {'openai': '🤖', 'claude': '🧠', 'gemini': '💎'}.get(key_provider, '🔑')
                    f.write(f"{emoji}🦊 {key_provider.upper()} KEY FOUND:\n")
                    f.write(f"Key: {key_info['key']}\n")
                    f.write(f"Provider: {key_provider.upper()}\n")
                    f.write(f"Platform: GitLab\n")
                    f.write(f"Project: {key_info['project_name']}\n")
                    f.write(f"File: {key_info['file_path']}\n")
                    f.write(f"URL: {key_info['gitlab_url']}\n")
                    f.write(f"Found at: {key_info['found_at']}\n")
                    f.write("-" * 60 + "\n\n")
                    
            print(f"💾 Saved {len(provider_keys)} {key_provider} keys to {filename}")

async def main():
    """Example usage"""
    tokens = ['your_gitlab_token_here']
    scraper = AsyncGitLabScraper(tokens)
    
    keys = await scraper.search_and_scan('openai', max_pages=2)
    scraper.save_keys_to_file(keys, 'openai')

if __name__ == "__main__":
    asyncio.run(main())
