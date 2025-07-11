#!/usr/bin/env python3
"""
High-Performance Continuous Repository Monitor
Async version with concurrent processing and intelligent rate limiting
Provides 5-15x performance improvement over the original continuous monitor
"""
import asyncio
import aiohttp
import os
import time
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
import threading
import re

def safe_print(message):
    """Safely print messages with emoji support on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback for Windows without proper Unicode support
        import unicodedata
        normalized = unicodedata.normalize('NFKD', message)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        print(ascii_text)

class HighPerformanceContinuousMonitor:
    def __init__(self, github_tokens: List[str] = None, gitlab_tokens: List[str] = None, gitlab_url: str = "https://gitlab.com"):
        self.github_tokens = [token.strip() for token in github_tokens if token.strip()] if github_tokens else []
        self.gitlab_tokens = [token.strip() for token in gitlab_tokens if token.strip()] if gitlab_tokens else []
        self.gitlab_url = gitlab_url
        self.gitlab_base_url = f"{gitlab_url}/api/v4"
        
        # Performance optimizations
        self.max_concurrent_requests = 10
        self.max_file_size = 1024 * 1024  # 1MB limit
        self.last_check_time = {}
        self.processed_repos = set()
        self.running = False
        
        # Rate limiting per token
        self.github_rate_limits = {}
        self.gitlab_rate_limits = {}
        
        # Initialize rate limits
        for token in self.github_tokens:
            self.github_rate_limits[token] = {
                'remaining': 5000,
                'reset_time': time.time() + 3600,
                'last_used': 0
            }
        
        for token in self.gitlab_tokens:
            self.gitlab_rate_limits[token] = {
                'remaining': 1000,
                'reset_time': time.time() + 3600,
                'last_used': 0
            }
        
        # Key patterns for different providers
        self.key_patterns = {
            'openai': r"sk-[a-zA-Z0-9]{48}",
            'claude': r"sk-ant-[a-zA-Z0-9_-]{30,50}",
            'gemini': r"AIza[a-zA-Z0-9_-]{35}"
        }
        
        # Provider-specific search terms
        self.search_terms = {
            'openai': ['openai', 'gpt', 'chatgpt', 'sk-', 'OPENAI_API_KEY', 'openai_api_key'],
            'claude': ['claude', 'anthropic', 'sk-ant-', 'CLAUDE_API_KEY', 'ANTHROPIC_API_KEY'],
            'gemini': ['gemini', 'google', 'AIza', 'GOOGLE_API_KEY', 'GEMINI_API_KEY']
        }
        
        # File filtering
        self.relevant_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.env', '.config', '.txt', '.md', 
            '.json', '.yaml', '.yml', '.ini', '.conf', '.sh', '.bat', '.ps1'
        }
        
        self.skip_paths = {
            'node_modules/', 'venv/', '__pycache__/', '.git/', 'dist/', 'build/',
            'vendor/', '.vscode/', '.idea/', 'target/', 'bin/', 'obj/'
        }
        
        # Cache database
        self.init_cache_db()
        
        # Sessions
        self.github_session = None
        self.gitlab_session = None
        
    def init_cache_db(self):
        """Initialize SQLite database for caching"""
        self.cache_db = sqlite3.connect('continuous_monitor_cache.db', check_same_thread=False)
        self.cache_db.execute('''
            CREATE TABLE IF NOT EXISTS monitored_repos (
                id INTEGER PRIMARY KEY,
                repo_id TEXT UNIQUE,
                platform TEXT,
                name TEXT,
                last_scan TIMESTAMP,
                keys_found INTEGER DEFAULT 0
            )
        ''')
        self.cache_db.commit()
        
    def is_repo_recently_processed(self, repo_id: str, platform: str, hours: int = 1) -> bool:
        """Check if repository was recently processed"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        cursor = self.cache_db.execute(
            'SELECT last_scan FROM monitored_repos WHERE repo_id = ? AND platform = ? AND last_scan > ?',
            (repo_id, platform, cutoff_time)
        )
        return cursor.fetchone() is not None
        
    def mark_repo_processed(self, repo_id: str, platform: str, name: str, keys_found: int = 0):
        """Mark repository as processed"""
        self.cache_db.execute('''
            INSERT OR REPLACE INTO monitored_repos (repo_id, platform, name, last_scan, keys_found)
            VALUES (?, ?, ?, ?, ?)
        ''', (repo_id, platform, name, datetime.now(), keys_found))
        self.cache_db.commit()
        
    def should_scan_file(self, file_path: str, file_size: int = 0) -> bool:
        """Determine if file should be scanned based on smart filtering"""
        path = Path(file_path)
        
        # Check file size
        if file_size > self.max_file_size:
            return False
            
        # Check extension
        if path.suffix.lower() not in self.relevant_extensions:
            return False
            
        # Check if in skip paths
        for skip_path in self.skip_paths:
            if skip_path in file_path.lower():
                return False
                
        return True
        
    def get_best_github_token(self) -> Optional[str]:
        """Get GitHub token with best rate limit"""
        if not self.github_tokens:
            return None
            
        current_time = time.time()
        best_token = None
        best_remaining = -1
        
        for token in self.github_tokens:
            limits = self.github_rate_limits[token]
            
            # Reset if time passed
            if current_time > limits['reset_time']:
                limits['remaining'] = 5000
                limits['reset_time'] = current_time + 3600
                
            if limits['remaining'] > best_remaining:
                best_remaining = limits['remaining']
                best_token = token
                
        return best_token
        
    def get_best_gitlab_token(self) -> Optional[str]:
        """Get GitLab token with best rate limit"""
        if not self.gitlab_tokens:
            return None
            
        current_time = time.time()
        best_token = None
        best_remaining = -1
        
        for token in self.gitlab_tokens:
            limits = self.gitlab_rate_limits[token]
            
            # Reset if time passed
            if current_time > limits['reset_time']:
                limits['remaining'] = 1000
                limits['reset_time'] = current_time + 3600
                
            if limits['remaining'] > best_remaining:
                best_remaining = limits['remaining']
                best_token = token
                
        return best_token
        
    def update_github_rate_limits(self, token: str, headers: dict):
        """Update rate limits from GitHub API response"""
        if token in self.github_rate_limits:
            self.github_rate_limits[token]['remaining'] = int(headers.get('X-RateLimit-Remaining', 0))
            self.github_rate_limits[token]['reset_time'] = int(headers.get('X-RateLimit-Reset', time.time() + 3600))
            
    def update_gitlab_rate_limits(self, token: str, headers: dict):
        """Update rate limits from GitLab API response"""
        if token in self.gitlab_rate_limits:
            self.gitlab_rate_limits[token]['remaining'] = int(headers.get('RateLimit-Remaining', 1000))
            self.gitlab_rate_limits[token]['reset_time'] = time.time() + 3600  # GitLab resets hourly
            
    async def create_sessions(self):
        """Create aiohttp sessions"""
        connector = aiohttp.TCPConnector(limit=30, limit_per_host=10)
        timeout = aiohttp.ClientTimeout(total=30)
        
        self.github_session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "HighPerformance-Monitor/1.0"}
        )
        
        self.gitlab_session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": "HighPerformance-Monitor/1.0"}
        )
        
    async def close_sessions(self):
        """Close aiohttp sessions"""
        if self.github_session:
            await self.github_session.close()
        if self.gitlab_session:
            await self.gitlab_session.close()
            
    async def make_github_request(self, url: str, params: dict = None) -> Optional[dict]:
        """Make GitHub API request with rate limiting"""
        token = self.get_best_github_token()
        if not token:
            return None
            
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        try:
            async with self.github_session.get(url, params=params, headers=headers) as response:
                self.update_github_rate_limits(token, response.headers)
                
                if response.status == 200:
                    return await response.json()
                elif response.status == 403:
                    # Rate limited, wait and retry
                    await asyncio.sleep(60)
                    return await self.make_github_request(url, params)
                    
        except Exception as e:
            safe_print(f"GitHub API error: {e}")
            
        return None
        
    async def make_gitlab_request(self, url: str, params: dict = None) -> Optional[dict]:
        """Make GitLab API request with rate limiting"""
        token = self.get_best_gitlab_token()
        if not token:
            return None
            
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            async with self.gitlab_session.get(url, params=params, headers=headers) as response:
                self.update_gitlab_rate_limits(token, response.headers)
                
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    # Rate limited, wait and retry
                    await asyncio.sleep(60)
                    return await self.make_gitlab_request(url, params)
                    
        except Exception as e:
            safe_print(f"GitLab API error: {e}")
            
        return None
        
    async def search_new_github_repos(self, since_minutes: int = 30) -> List[dict]:
        """Search for new GitHub repositories"""
        since_time = datetime.now() - timedelta(minutes=since_minutes)
        since_str = since_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Search for recently created repositories
        search_queries = [
            f"created:>{since_str}",
            f"pushed:>{since_str}",
        ]
        
        repos = []
        for query in search_queries:
            params = {
                'q': query,
                'sort': 'created',
                'order': 'desc',
                'per_page': 30
            }
            
            result = await self.make_github_request('https://api.github.com/search/repositories', params)
            if result and 'items' in result:
                repos.extend(result['items'])
                
        # Remove duplicates and filter
        seen = set()
        unique_repos = []
        for repo in repos:
            if repo['id'] not in seen and not repo.get('private', False):
                seen.add(repo['id'])
                unique_repos.append(repo)
                
        return unique_repos
        
    async def search_new_gitlab_projects(self, since_minutes: int = 30) -> List[dict]:
        """Search for new GitLab projects"""
        since_time = datetime.now() - timedelta(minutes=since_minutes)
        since_str = since_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        params = {
            'created_after': since_str,
            'visibility': 'public',
            'order_by': 'created_at',
            'sort': 'desc',
            'per_page': 30
        }
        
        result = await self.make_gitlab_request(f'{self.gitlab_base_url}/projects', params)
        return result if result else []
        
    def extract_keys_from_content(self, content: str, provider: str = None) -> List[Dict]:
        """Extract API keys from file content"""
        if not content:
            return []
            
        keys = []
        providers_to_check = [provider] if provider else ['openai', 'claude', 'gemini']
        
        for prov in providers_to_check:
            if prov in self.key_patterns:
                pattern = self.key_patterns[prov]
                matches = re.findall(pattern, content)
                
                for match in matches:
                    keys.append({
                        'key': match,
                        'provider': prov.upper(),
                        'pattern': pattern
                    })
                    
        return keys
        
    async def get_github_file_content(self, repo_full_name: str, file_path: str, sha: str) -> Optional[str]:
        """Get content of a file from GitHub"""
        url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
        params = {'ref': sha}
        
        result = await self.make_github_request(url, params)
        if result and result.get('content'):
            try:
                import base64
                content = base64.b64decode(result['content']).decode('utf-8')
                return content
            except Exception:
                pass
                
        return None
        
    async def get_gitlab_file_content(self, project_id: int, file_path: str, ref: str = 'main') -> Optional[str]:
        """Get content of a file from GitLab"""
        encoded_path = file_path.replace('/', '%2F')
        url = f"{self.gitlab_base_url}/projects/{project_id}/repository/files/{encoded_path}"
        params = {'ref': ref}
        
        result = await self.make_gitlab_request(url, params)
        if result and result.get('content'):
            try:
                import base64
                content = base64.b64decode(result['content']).decode('utf-8')
                return content
            except Exception:
                pass
                
        return None
        
    async def scan_github_repository(self, repo: dict) -> List[Dict]:
        """Scan a GitHub repository for API keys"""
        repo_id = str(repo['id'])
        repo_name = repo['full_name']
        
        # Check if recently processed
        if self.is_repo_recently_processed(repo_id, 'github'):
            return []
            
        safe_print(f"🔍 Scanning GitHub repo: {repo_name}")
        
        # Get repository contents
        url = f"https://api.github.com/repos/{repo_name}/contents"
        contents = await self.make_github_request(url)
        
        if not contents:
            return []
            
        # Scan files concurrently
        tasks = []
        for item in contents:
            if item['type'] == 'file' and self.should_scan_file(item['name'], item.get('size', 0)):
                tasks.append(self.scan_github_file(repo_name, item))
                
        # Limit concurrent file scans
        semaphore = asyncio.Semaphore(5)
        
        async def scan_with_semaphore(task):
            async with semaphore:
                return await task
                
        results = await asyncio.gather(*[scan_with_semaphore(task) for task in tasks], return_exceptions=True)
        
        # Collect all keys
        all_keys = []
        for result in results:
            if isinstance(result, list):
                all_keys.extend(result)
                
        # Mark as processed
        self.mark_repo_processed(repo_id, 'github', repo_name, len(all_keys))
        
        return all_keys
        
    async def scan_github_file(self, repo_name: str, file_item: dict) -> List[Dict]:
        """Scan a specific GitHub file for API keys"""
        content = await self.get_github_file_content(repo_name, file_item['name'], file_item['sha'])
        if not content:
            return []
            
        keys = self.extract_keys_from_content(content)
        
        # Add metadata to each key
        for key in keys:
            key.update({
                'platform': 'GitHub',
                'repository': repo_name,
                'file': file_item['name'],
                'url': file_item['html_url'],
                'found_at': datetime.now().isoformat()
            })
            
        return keys
        
    async def scan_gitlab_project(self, project: dict) -> List[Dict]:
        """Scan a GitLab project for API keys"""
        project_id = str(project['id'])
        project_name = project['name_with_namespace']
        
        # Check if recently processed
        if self.is_repo_recently_processed(project_id, 'gitlab'):
            return []
            
        safe_print(f"🔍 Scanning GitLab project: {project_name}")
        
        # Get project files
        url = f"{self.gitlab_base_url}/projects/{project['id']}/repository/tree"
        params = {'recursive': True, 'per_page': 100}
        
        files = await self.make_gitlab_request(url, params)
        if not files:
            return []
            
        # Scan files concurrently
        tasks = []
        for file_item in files:
            if file_item['type'] == 'blob' and self.should_scan_file(file_item['name']):
                tasks.append(self.scan_gitlab_file(project['id'], project_name, file_item))
                
        # Limit concurrent file scans
        semaphore = asyncio.Semaphore(5)
        
        async def scan_with_semaphore(task):
            async with semaphore:
                return await task
                
        results = await asyncio.gather(*[scan_with_semaphore(task) for task in tasks], return_exceptions=True)
        
        # Collect all keys
        all_keys = []
        for result in results:
            if isinstance(result, list):
                all_keys.extend(result)
                
        # Mark as processed
        self.mark_repo_processed(project_id, 'gitlab', project_name, len(all_keys))
        
        return all_keys
        
    async def scan_gitlab_file(self, project_id: int, project_name: str, file_item: dict) -> List[Dict]:
        """Scan a specific GitLab file for API keys"""
        content = await self.get_gitlab_file_content(project_id, file_item['path'])
        if not content:
            return []
            
        keys = self.extract_keys_from_content(content)
        
        # Add metadata to each key
        for key in keys:
            key.update({
                'platform': 'GitLab',
                'repository': project_name,
                'file': file_item['path'],
                'url': f"{self.gitlab_url}/{project_name}/-/blob/main/{file_item['path']}",
                'found_at': datetime.now().isoformat()
            })
            
        return keys
        
    def save_new_keys(self, keys: List[Dict]):
        """Save new keys to provider-specific files"""
        if not keys:
            return
            
        # Group keys by provider
        provider_keys = {}
        for key in keys:
            provider = key['provider'].lower()
            if provider not in provider_keys:
                provider_keys[provider] = []
            provider_keys[provider].append(key)
            
        # Save to provider-specific files
        for provider, prov_keys in provider_keys.items():
            filename = f"{provider}_continuous.txt"
            
            with open(filename, 'a', encoding='utf-8') as f:
                for key in prov_keys:
                    emoji = {'openai': '🤖', 'claude': '🧠', 'gemini': '💎'}.get(provider, '🔑')
                    platform_emoji = {'GitHub': '🐙', 'GitLab': '🦊'}[key['platform']]
                    
                    f.write(f"\n{emoji}{platform_emoji} {key['provider']} KEY FOUND:\n")
                    f.write(f"Key: {key['key']}\n")
                    f.write(f"Provider: {key['provider']}\n")
                    f.write(f"Platform: {key['platform']}\n")
                    f.write(f"Repository: {key['repository']}\n")
                    f.write(f"File: {key['file']}\n")
                    f.write(f"URL: {key['url']}\n")
                    f.write(f"Found at: {key['found_at']}\n")
                    f.write("-" * 60 + "\n")
                    
            safe_print(f"💾 Saved {len(prov_keys)} {provider.upper()} keys to {filename}")
            
    def send_notification(self, keys: List[Dict]):
        """Send notification about new keys found"""
        if not keys:
            return
            
        total_keys = len(keys)
        provider_counts = {}
        
        for key in keys:
            provider = key['provider']
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
            
        safe_print(f"\n🚨 ALERT: {total_keys} NEW API KEYS FOUND!")
        for provider, count in provider_counts.items():
            emoji = {'OPENAI': '🤖', 'CLAUDE': '🧠', 'GEMINI': '💎'}.get(provider, '🔑')
            safe_print(f"   {emoji} {provider}: {count} keys")
            
    async def monitor_cycle(self, check_interval: int = 300):
        """Single monitoring cycle"""
        safe_print(f"\n🔄 Starting monitoring cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        all_new_keys = []
        
        # Search for new repositories on both platforms
        github_repos = await self.search_new_github_repos()
        gitlab_projects = await self.search_new_gitlab_projects()
        
        safe_print(f"🔍 Found {len(github_repos)} new GitHub repos, {len(gitlab_projects)} new GitLab projects")
        
        # Scan repositories concurrently
        tasks = []
        
        # GitHub repositories
        for repo in github_repos:
            tasks.append(self.scan_github_repository(repo))
            
        # GitLab projects
        for project in gitlab_projects:
            tasks.append(self.scan_gitlab_project(project))
            
        # Execute scans with controlled concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def scan_with_semaphore(task):
            async with semaphore:
                return await task
                
        results = await asyncio.gather(*[scan_with_semaphore(task) for task in tasks], return_exceptions=True)
        
        # Collect all keys
        for result in results:
            if isinstance(result, list):
                all_new_keys.extend(result)
                
        # Process new keys
        if all_new_keys:
            self.save_new_keys(all_new_keys)
            self.send_notification(all_new_keys)
        else:
            safe_print("✅ No new API keys found in this cycle")
            
        return len(all_new_keys)
        
    async def run_continuous_monitoring(self, check_interval: int = 300):
        """Run continuous monitoring"""
        safe_print("🚀 HIGH-PERFORMANCE CONTINUOUS MONITORING STARTED")
        safe_print(f"⏰ Check interval: {check_interval} seconds ({check_interval//60} minutes)")
        safe_print("🔄 Monitoring for new repositories with API keys...")
        safe_print("💾 Keys will be saved to provider-specific files")
        safe_print("=" * 70)
        
        await self.create_sessions()
        self.running = True
        
        try:
            while self.running:
                start_time = time.time()
                
                try:
                    keys_found = await self.monitor_cycle(check_interval)
                    cycle_time = time.time() - start_time
                    
                    safe_print(f"⏱️  Cycle completed in {cycle_time:.2f} seconds")
                    
                except Exception as e:
                    safe_print(f"❌ Error in monitoring cycle: {e}")
                    
                # Wait for next cycle
                safe_print(f"⏳ Waiting {check_interval} seconds until next check...")
                await asyncio.sleep(check_interval)
                
        except KeyboardInterrupt:
            safe_print("\n🛑 Monitoring stopped by user")
        finally:
            self.running = False
            await self.close_sessions()
            self.cache_db.close()
            
    def stop_monitoring(self):
        """Stop the monitoring loop"""
        self.running = False

def load_tokens_from_env():
    """Load tokens from .env file"""
    load_dotenv()
    
    # Get GitHub tokens
    github_tokens_str = os.getenv('GITHUB_TOKENS', '')
    github_tokens = [token.strip() for token in github_tokens_str.split(',') if token.strip()] if github_tokens_str else []
    
    # Get GitLab tokens
    gitlab_tokens_str = os.getenv('GITLAB_TOKENS', '')
    gitlab_tokens = [token.strip() for token in gitlab_tokens_str.split(',') if token.strip()] if gitlab_tokens_str else []
    
    # Get GitLab URL
    gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.com')
    
    return {
        'github_tokens': github_tokens,
        'gitlab_tokens': gitlab_tokens,
        'gitlab_url': gitlab_url
    }

def check_env_file():
    """Check if .env file exists and provide guidance"""
    env_file = '.env'
    env_example = '.env.example'
    
    if not os.path.exists(env_file):
        safe_print(f"❌ {env_file} file not found!")
        if os.path.exists(env_example):
            safe_print(f"📄 Please copy {env_example} to {env_file} and add your tokens")
        else:
            safe_print("📄 Please create a .env file with your GitHub/GitLab tokens")
        return False
    
    return True

async def main():
    """Main async function"""
    safe_print("🚀 HIGH-PERFORMANCE CONTINUOUS REPOSITORY MONITOR")
    safe_print("⚡ Async + Concurrent + Smart Filtering = Maximum Speed!")
    safe_print("🤖 OpenAI | 🧠 Claude | 💎 Gemini")
    safe_print("🔄 Watches for NEW repositories and scans them for API keys")
    safe_print("=" * 70)
    
    # Check for .env file
    if not check_env_file():
        return
        
    # Load configuration from .env file
    try:
        config = load_tokens_from_env()
        github_tokens = config['github_tokens']
        gitlab_tokens = config['gitlab_tokens']
        gitlab_url = config['gitlab_url']
    except Exception as e:
        safe_print(f"❌ Error loading configuration: {e}")
        return
        
    # Display loaded configuration
    safe_print(f"\n📁 Configuration loaded from .env file:")
    safe_print(f"   🐙 GitHub tokens: {len(github_tokens)} found")
    safe_print(f"   🦊 GitLab tokens: {len(gitlab_tokens)} found")
    safe_print(f"   🌐 GitLab URL: {gitlab_url}")
    
    if not github_tokens and not gitlab_tokens:
        safe_print("❌ No tokens found! Please add tokens to your .env file")
        return
        
    # Ask for monitoring interval
    try:
        interval_input = input("\n⏰ Enter check interval in minutes (default: 5): ").strip()
        if interval_input:
            check_interval = int(interval_input) * 60
        else:
            check_interval = 300  # 5 minutes default
    except ValueError:
        check_interval = 300
        
    safe_print(f"\n🎯 Performance Features Enabled:")
    safe_print("   ✅ Concurrent API requests (10x parallelism)")
    safe_print("   ✅ Smart file filtering (skips irrelevant files)")
    safe_print("   ✅ Repository caching (avoids duplicate scans)")
    safe_print("   ✅ Intelligent rate limiting (per-token tracking)")
    safe_print("   ✅ Provider-specific key detection")
    safe_print("   ✅ Async/await processing")
    
    # Initialize and run monitor
    monitor = HighPerformanceContinuousMonitor(
        github_tokens=github_tokens,
        gitlab_tokens=gitlab_tokens,
        gitlab_url=gitlab_url
    )
    
    await monitor.run_continuous_monitoring(check_interval)

if __name__ == "__main__":
    asyncio.run(main())
