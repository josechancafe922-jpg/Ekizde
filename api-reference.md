# 📚 API Reference - Advanced API Key Scanner

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Async/Await](https://img.shields.io/badge/Async-Await%20Support-green.svg)](README.md)
[![Type Hints](https://img.shields.io/badge/Type-Hints%20Enabled-purple.svg)](README.md)

**Complete API reference for the Advanced API Key Scanner with detailed class documentation, method signatures, and usage examples.**

---

## 📋 Table of Contents

1. [Getting Started](#-getting-started)
2. [Authentication Setup](#-authentication-setup)
3. [Core Classes](#-core-classes)
4. [High-Performance Scanners](#-high-performance-scanners)
5. [Continuous Monitoring](#-continuous-monitoring)
6. [Utility Functions](#-utility-functions)
7. [Configuration](#-configuration)
8. [Error Handling](#-error-handling)
9. [Examples](#-examples)

---

## 🚀 Getting Started

### **Installation**
```bash
pip install -r requirements.txt
```

### **Basic Usage**
```python
import asyncio
from high_performance_scraper import HighPerformanceBatchScraper

async def main():
    scanner = HighPerformanceBatchScraper(
        github_tokens=['ghp_token1', 'ghp_token2'],
        gitlab_tokens=['glpat_token1']
    )
    
    await scanner.run_batch_scan(
        providers=['openai', 'claude', 'gemini'],
        max_pages_github=5,
        max_pages_gitlab=3
    )

asyncio.run(main())
```

---

## 🔐 Authentication Setup

### **GitHub Personal Access Token**

#### **Step 1: Navigate to GitHub Settings**
1. Go to [GitHub Settings](https://github.com/settings/tokens)
2. Click **"Developer settings"** in the left sidebar
3. Click **"Personal access tokens"**
4. Click **"Tokens (classic)"**

#### **Step 2: Generate New Token**
1. Click **"Generate new token"** → **"Generate new token (classic)"**
2. Add a descriptive **Note**: `API Key Scanner - Security Research`
3. Set **Expiration**: Choose based on your needs (30-90 days recommended)

#### **Step 3: Select Scopes**
```
Required Scopes:
✅ public_repo - Access public repositories
✅ read:user - Read user profile information

Optional Scopes (for enhanced features):
✅ repo - Full repository access (if scanning private repos)
✅ read:org - Read organization data
```

#### **Step 4: Generate and Copy Token**
1. Click **"Generate token"**
2. **Copy the token immediately** (you won't see it again)
3. Token format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### **Step 5: Add to Environment**
```bash
# Add to .env file
GITHUB_TOKENS=ghp_your_token_here,ghp_second_token_here
```

### **GitLab Personal Access Token**

#### **Step 1: Navigate to GitLab Settings**
1. Go to [GitLab Personal Access Tokens](https://gitlab.com/-/user_settings/personal_access_tokens)
2. Or navigate: **Avatar** → **Settings** → **Access Tokens**

#### **Step 2: Create New Token**
1. **Token name**: `API Key Scanner - Security Research`
2. **Expiration date**: Choose based on your needs
3. **Description**: `For scanning public repositories for exposed API keys`

#### **Step 3: Select Scopes**
```
Required Scopes:
✅ read_api - Read access to API
✅ read_repository - Read repository data

Optional Scopes (for enhanced features):
✅ read_user - Read user information
✅ read_project - Read project information
```

#### **Step 4: Create and Copy Token**
1. Click **"Create personal access token"**
2. **Copy the token immediately** (you won't see it again)
3. Token format: `glpat-xxxxxxxxxxxxxxxxxxxx`

#### **Step 5: Add to Environment**
```bash
# Add to .env file
GITLAB_TOKENS=glpat_your_token_here,glpat_second_token_here
```

### **Complete .env Configuration**
```bash
# GitHub Personal Access Tokens (comma-separated for multiple)
GITHUB_TOKENS=ghp_token1,ghp_token2,ghp_token3

# GitLab Personal Access Tokens (comma-separated for multiple)
GITLAB_TOKENS=glpat_token1,glpat_token2

# GitLab URL (optional, defaults to https://gitlab.com)
GITLAB_URL=https://gitlab.com

# Performance Settings
MAX_CONCURRENT_REQUESTS=15
MAX_FILE_SIZE=1048576
CACHE_TIMEOUT_HOURS=1
```

---

## 🏗️ Core Classes

### **HighPerformanceBatchScraper**

#### **Class Definition**
```python
class HighPerformanceBatchScraper:
    def __init__(
        self,
        github_tokens: List[str] = None,
        gitlab_tokens: List[str] = None,
        gitlab_url: str = "https://gitlab.com"
    ):
        """
        Initialize high-performance batch scraper
        
        Args:
            github_tokens: List of GitHub personal access tokens
            gitlab_tokens: List of GitLab personal access tokens
            gitlab_url: GitLab instance URL
        """
```

#### **Key Methods**

##### **`run_batch_scan()`**
```python
async def run_batch_scan(
    self,
    providers: List[str],
    max_pages_github: int = 5,
    max_pages_gitlab: int = 3
) -> None:
    """
    Run complete batch scan for API keys
    
    Args:
        providers: List of providers to scan ['openai', 'claude', 'gemini']
        max_pages_github: Maximum pages to fetch from GitHub
        max_pages_gitlab: Maximum pages to fetch from GitLab
        
    Returns:
        None: Results are saved to provider-specific files
        
    Raises:
        ValueError: If no providers specified
        ConnectionError: If API tokens are invalid
        
    Example:
        >>> scanner = HighPerformanceBatchScraper(tokens)
        >>> await scanner.run_batch_scan(['openai', 'claude'], 10, 5)
    """
```

##### **`search_github_repositories()`**
```python
async def search_github_repositories(
    self,
    providers: List[str],
    max_pages: int = 5
) -> List[dict]:
    """
    Search GitHub repositories for provider-specific content
    
    Args:
        providers: List of API providers to search for
        max_pages: Maximum search result pages to process
        
    Returns:
        List[dict]: List of repository objects
        
    Example:
        >>> repos = await scanner.search_github_repositories(['openai'], 3)
        >>> print(f"Found {len(repos)} repositories")
    """
```

##### **`scan_github_repository()`**
```python
async def scan_github_repository(self, repo: dict) -> List[Dict]:
    """
    Scan a single GitHub repository for API keys
    
    Args:
        repo: Repository object from GitHub API
        
    Returns:
        List[Dict]: List of found API keys with metadata
        
    Example:
        >>> keys = await scanner.scan_github_repository(repo_data)
        >>> for key in keys:
        >>>     print(f"Found {key['provider']} key in {key['file']}")
    """
```

#### **Properties**
```python
@property
def stats(self) -> Dict[str, Any]:
    """
    Get current scanning statistics
    
    Returns:
        Dict containing:
        - repos_scanned: Number of repositories processed
        - files_scanned: Number of files analyzed
        - keys_found: Total API keys discovered
        - start_time: Scan start timestamp
        - end_time: Scan completion timestamp
    """
```

### **HighPerformanceContinuousMonitor**

#### **Class Definition**
```python
class HighPerformanceContinuousMonitor:
    def __init__(
        self,
        github_tokens: List[str] = None,
        gitlab_tokens: List[str] = None,
        gitlab_url: str = "https://gitlab.com"
    ):
        """
        Initialize continuous monitoring system
        
        Args:
            github_tokens: List of GitHub personal access tokens
            gitlab_tokens: List of GitLab personal access tokens
            gitlab_url: GitLab instance URL
        """
```

#### **Key Methods**

##### **`run_continuous_monitoring()`**
```python
async def run_continuous_monitoring(self, check_interval: int = 300) -> None:
    """
    Start continuous monitoring for new repositories
    
    Args:
        check_interval: Seconds between monitoring cycles
        
    Returns:
        None: Runs indefinitely until stopped
        
    Example:
        >>> monitor = HighPerformanceContinuousMonitor(tokens)
        >>> await monitor.run_continuous_monitoring(300)  # Check every 5 minutes
    """
```

##### **`search_new_github_repos()`**
```python
async def search_new_github_repos(self, since_minutes: int = 30) -> List[dict]:
    """
    Search for new GitHub repositories created recently
    
    Args:
        since_minutes: Look for repos created in last N minutes
        
    Returns:
        List[dict]: List of new repository objects
        
    Example:
        >>> new_repos = await monitor.search_new_github_repos(60)
        >>> print(f"Found {len(new_repos)} new repositories")
    """
```

##### **`monitor_cycle()`**
```python
async def monitor_cycle(self, check_interval: int = 300) -> int:
    """
    Execute a single monitoring cycle
    
    Args:
        check_interval: Interval configuration for context
        
    Returns:
        int: Number of new API keys found in this cycle
        
    Example:
        >>> keys_found = await monitor.monitor_cycle(300)
        >>> print(f"Cycle completed: {keys_found} new keys found")
    """
```

---

## 🔧 Utility Functions

### **Token Management**

#### **`load_tokens_from_env()`**
```python
def load_tokens_from_env() -> Dict[str, Any]:
    """
    Load API tokens from environment variables
    
    Returns:
        Dict containing:
        - github_tokens: List of GitHub tokens
        - gitlab_tokens: List of GitLab tokens
        - gitlab_url: GitLab instance URL
        
    Example:
        >>> config = load_tokens_from_env()
        >>> print(f"Loaded {len(config['github_tokens'])} GitHub tokens")
    """
```

#### **`validate_token()`**
```python
async def validate_token(token: str, platform: str) -> bool:
    """
    Validate if an API token is active and has required permissions
    
    Args:
        token: API token to validate
        platform: 'github' or 'gitlab'
        
    Returns:
        bool: True if token is valid and has required scopes
        
    Example:
        >>> is_valid = await validate_token('ghp_token', 'github')
        >>> print(f"Token is {'valid' if is_valid else 'invalid'}")
    """
```

### **File Processing**

#### **`extract_keys_from_content()`**
```python
def extract_keys_from_content(
    content: str,
    provider: str = None
) -> List[Dict]:
    """
    Extract API keys from file content using regex patterns
    
    Args:
        content: File content to analyze
        provider: Specific provider to search for (optional)
        
    Returns:
        List[Dict]: List of API key objects with metadata
        
    Example:
        >>> keys = extract_keys_from_content(file_content, 'openai')
        >>> for key in keys:
        >>>     print(f"Found {key['provider']} key: {key['key'][:10]}...")
    """
```

#### **`should_scan_file()`**
```python
def should_scan_file(file_path: str, file_size: int = 0) -> bool:
    """
    Determine if a file should be scanned based on filtering rules
    
    Args:
        file_path: Path to the file
        file_size: Size of the file in bytes
        
    Returns:
        bool: True if file should be scanned
        
    Example:
        >>> should_scan = should_scan_file('src/config.py', 1024)
        >>> print(f"Scan file: {should_scan}")
    """
```

### **Cache Management**

#### **`init_cache_db()`**
```python
def init_cache_db(cache_path: str = 'scanner_cache.db') -> None:
    """
    Initialize SQLite cache database
    
    Args:
        cache_path: Path to cache database file
        
    Example:
        >>> init_cache_db('custom_cache.db')
    """
```

#### **`is_repo_cached()`**
```python
def is_repo_cached(repo_id: str, platform: str) -> bool:
    """
    Check if repository was recently scanned
    
    Args:
        repo_id: Unique repository identifier
        platform: 'github' or 'gitlab'
        
    Returns:
        bool: True if repository is in cache
        
    Example:
        >>> cached = is_repo_cached('12345', 'github')
        >>> print(f"Repository cached: {cached}")
    """
```

---

## 🎯 Configuration Classes

### **ScannerConfig**
```python
class ScannerConfig:
    """Configuration class for scanner settings"""
    
    def __init__(self):
        self.max_concurrent_requests: int = 15
        self.max_file_size: int = 1024 * 1024  # 1MB
        self.cache_timeout_hours: int = 1
        self.rate_limit_delay: float = 0.1
        
    @classmethod
    def from_env(cls) -> 'ScannerConfig':
        """Load configuration from environment variables"""
        config = cls()
        config.max_concurrent_requests = int(os.getenv('MAX_CONCURRENT_REQUESTS', 15))
        config.max_file_size = int(os.getenv('MAX_FILE_SIZE', 1024 * 1024))
        config.cache_timeout_hours = int(os.getenv('CACHE_TIMEOUT_HOURS', 1))
        return config
```

### **ProviderConfig**
```python
class ProviderConfig:
    """Configuration for API key providers"""
    
    PROVIDERS = {
        'openai': {
            'name': 'OpenAI',
            'pattern': r"sk-[a-zA-Z0-9]{48}",
            'search_terms': ['openai', 'gpt', 'chatgpt', 'sk-', 'OPENAI_API_KEY'],
            'emoji': '🤖'
        },
        'claude': {
            'name': 'Claude/Anthropic',
            'pattern': r"sk-ant-[a-zA-Z0-9_-]{30,50}",
            'search_terms': ['claude', 'anthropic', 'sk-ant-', 'CLAUDE_API_KEY'],
            'emoji': '🧠'
        },
        'gemini': {
            'name': 'Gemini/Google',
            'pattern': r"AIza[a-zA-Z0-9_-]{35}",
            'search_terms': ['gemini', 'google', 'AIza', 'GOOGLE_API_KEY'],
            'emoji': '💎'
        }
    }
```

---

## ⚠️ Error Handling

### **Exception Classes**

#### **`ScannerError`**
```python
class ScannerError(Exception):
    """Base exception for scanner errors"""
    pass
```

#### **`AuthenticationError`**
```python
class AuthenticationError(ScannerError):
    """Raised when API token authentication fails"""
    
    def __init__(self, platform: str, message: str):
        self.platform = platform
        super().__init__(f"{platform} authentication failed: {message}")
```

#### **`RateLimitError`**
```python
class RateLimitError(ScannerError):
    """Raised when API rate limits are exceeded"""
    
    def __init__(self, platform: str, reset_time: int):
        self.platform = platform
        self.reset_time = reset_time
        super().__init__(f"{platform} rate limit exceeded. Reset at {reset_time}")
```

#### **`ConfigurationError`**
```python
class ConfigurationError(ScannerError):
    """Raised when configuration is invalid"""
    
    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}")
```

### **Error Handling Examples**

#### **Basic Error Handling**
```python
try:
    scanner = HighPerformanceBatchScraper(github_tokens, gitlab_tokens)
    await scanner.run_batch_scan(['openai', 'claude'])
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    print(f"Try again after: {e.reset_time}")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

#### **Advanced Error Handling with Retry**
```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def scan_with_retry(scanner, providers):
    try:
        return await scanner.run_batch_scan(providers)
    except RateLimitError as e:
        print(f"Rate limited, retrying in {e.reset_time} seconds...")
        await asyncio.sleep(e.reset_time)
        raise
```

---

## 📊 Response Objects

### **APIKey Object**
```python
class APIKey:
    """Represents a found API key"""
    
    def __init__(self, key: str, provider: str, **metadata):
        self.key = key
        self.provider = provider
        self.platform = metadata.get('platform')
        self.repository = metadata.get('repository')
        self.file = metadata.get('file')
        self.url = metadata.get('url')
        self.found_at = metadata.get('found_at')
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'key': self.key,
            'provider': self.provider,
            'platform': self.platform,
            'repository': self.repository,
            'file': self.file,
            'url': self.url,
            'found_at': self.found_at
        }
```

### **ScanResult Object**
```python
class ScanResult:
    """Represents scan results for a repository"""
    
    def __init__(self, repository: str, platform: str):
        self.repository = repository
        self.platform = platform
        self.keys_found: List[APIKey] = []
        self.files_scanned: int = 0
        self.scan_duration: float = 0.0
        self.errors: List[str] = []
        
    def add_key(self, key: APIKey) -> None:
        """Add a found API key to results"""
        self.keys_found.append(key)
        
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of scan results"""
        return {
            'repository': self.repository,
            'platform': self.platform,
            'keys_found': len(self.keys_found),
            'files_scanned': self.files_scanned,
            'scan_duration': self.scan_duration,
            'errors': len(self.errors)
        }
```

---

## 🔍 Advanced Usage Examples

### **Custom Provider Integration**
```python
class CustomScanner(HighPerformanceBatchScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add custom provider patterns
        self.key_patterns.update({
            'custom_api': r"ca-[a-zA-Z0-9]{32}",
            'another_service': r"as_[a-zA-Z0-9]{40}"
        })
        
        self.search_terms.update({
            'custom_api': ['custom_api', 'ca-', 'CUSTOM_API_KEY'],
            'another_service': ['another_service', 'as_', 'ANOTHER_API_KEY']
        })
    
    async def scan_custom_provider(self, provider: str) -> List[Dict]:
        """Scan for custom provider API keys"""
        return await self.search_github_repositories([provider], max_pages=3)
```

### **Batch Processing with Callbacks**
```python
class CallbackScanner(HighPerformanceBatchScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callbacks = {}
    
    def register_callback(self, event: str, callback: callable):
        """Register callback for specific events"""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
    
    async def emit_event(self, event: str, data: Any):
        """Emit event to registered callbacks"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                await callback(data)
    
    async def scan_github_repository(self, repo: dict) -> List[Dict]:
        """Override to emit events"""
        await self.emit_event('repo_scan_start', repo)
        
        keys = await super().scan_github_repository(repo)
        
        await self.emit_event('repo_scan_complete', {
            'repo': repo,
            'keys_found': len(keys)
        })
        
        return keys

# Usage
scanner = CallbackScanner(github_tokens, gitlab_tokens)

async def on_repo_complete(data):
    print(f"Completed scanning {data['repo']['name']}: {data['keys_found']} keys")

scanner.register_callback('repo_scan_complete', on_repo_complete)
await scanner.run_batch_scan(['openai'])
```

### **Custom File Filtering**
```python
class CustomFilterScanner(HighPerformanceBatchScraper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.custom_filters = []
    
    def add_custom_filter(self, filter_func: callable):
        """Add custom file filtering function"""
        self.custom_filters.append(filter_func)
    
    def should_scan_file(self, file_path: str, file_size: int = 0) -> bool:
        """Override with custom filtering"""
        # Run default filtering first
        if not super().should_scan_file(file_path, file_size):
            return False
        
        # Apply custom filters
        for filter_func in self.custom_filters:
            if not filter_func(file_path, file_size):
                return False
        
        return True

# Usage
scanner = CustomFilterScanner(github_tokens, gitlab_tokens)

# Only scan Python files
scanner.add_custom_filter(lambda path, size: path.endswith('.py'))

# Skip test files
scanner.add_custom_filter(lambda path, size: 'test' not in path.lower())

await scanner.run_batch_scan(['openai'])
```

---

## 🎯 Performance Optimization APIs

### **Performance Monitoring**
```python
class PerformanceMonitor:
    """Monitor scanner performance metrics"""
    
    def __init__(self, scanner):
        self.scanner = scanner
        self.metrics = {
            'start_time': time.time(),
            'requests_made': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0
        }
    
    def record_request(self, platform: str, duration: float):
        """Record API request metrics"""
        self.metrics['requests_made'] += 1
        self.metrics.setdefault(f'{platform}_requests', 0)
        self.metrics[f'{platform}_requests'] += 1
        self.metrics.setdefault(f'{platform}_avg_duration', [])
        self.metrics[f'{platform}_avg_duration'].append(duration)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        runtime = time.time() - self.metrics['start_time']
        return {
            'runtime_seconds': runtime,
            'requests_per_second': self.metrics['requests_made'] / runtime,
            'cache_hit_rate': self.metrics['cache_hits'] / 
                             (self.metrics['cache_hits'] + self.metrics['cache_misses']),
            'error_rate': self.metrics['errors'] / self.metrics['requests_made'],
            'total_requests': self.metrics['requests_made']
        }
```

### **Rate Limiting Management**
```python
class RateLimitManager:
    """Manage API rate limits across multiple tokens"""
    
    def __init__(self, tokens: List[str], platform: str):
        self.tokens = tokens
        self.platform = platform
        self.limits = {
            token: {
                'remaining': 5000 if platform == 'github' else 1000,
                'reset_time': time.time() + 3600,
                'last_used': 0
            } for token in tokens
        }
    
    def get_best_token(self) -> str:
        """Get token with highest remaining quota"""
        return max(self.tokens, key=lambda t: self.limits[t]['remaining'])
    
    def update_limits(self, token: str, remaining: int, reset_time: int):
        """Update rate limit information from API response"""
        self.limits[token]['remaining'] = remaining
        self.limits[token]['reset_time'] = reset_time
        self.limits[token]['last_used'] = time.time()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        return {
            'total_tokens': len(self.tokens),
            'active_tokens': len([t for t in self.tokens if self.limits[t]['remaining'] > 0]),
            'total_remaining': sum(self.limits[t]['remaining'] for t in self.tokens),
            'next_reset': min(self.limits[t]['reset_time'] for t in self.tokens)
        }
```

---

## 🔄 Async Context Managers

### **Scanner Session Management**
```python
class ScannerSession:
    """Async context manager for scanner sessions"""
    
    def __init__(self, scanner):
        self.scanner = scanner
        
    async def __aenter__(self):
        await self.scanner.create_sessions()
        return self.scanner
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.scanner.close_sessions()
        if hasattr(self.scanner, 'cache_db'):
            self.scanner.cache_db.close()

# Usage
async with ScannerSession(scanner) as session:
    await session.run_batch_scan(['openai', 'claude'])
```

---

## 📈 Metrics and Logging

### **Structured Logging**
```python
import logging
import json

class StructuredLogger:
    """Structured logging for scanner operations"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_scan_start(self, repo: str, platform: str):
        """Log scan start event"""
        self.logger.info(json.dumps({
            'event': 'scan_start',
            'repository': repo,
            'platform': platform,
            'timestamp': time.time()
        }))
    
    def log_keys_found(self, repo: str, count: int, providers: List[str]):
        """Log keys found event"""
        self.logger.info(json.dumps({
            'event': 'keys_found',
            'repository': repo,
            'count': count,
            'providers': providers,
            'timestamp': time.time()
        }))
```

---

**📚 This API reference provides comprehensive documentation for all classes, methods, and functions in the Advanced API Key Scanner. Use these APIs to build custom security scanning solutions and integrate with your existing security infrastructure.**
