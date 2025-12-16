from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os

# Global browser driver (will be initialized on demand)
_driver: Optional[webdriver.Chrome] = None

app = FastAPI(title="Website Authentication Component Detector API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_browser_driver():
    """Get or create a Chrome browser driver"""
    global _driver
    if _driver is None:
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')  # Use new headless mode
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_experimental_option("detach", True)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Add additional options to avoid detection
            prefs = {
                "profile.default_content_setting_values": {
                    "notifications": 2
                },
                "profile.managed_default_content_settings": {
                    "images": 1
                }
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Get the correct chromedriver path
            base_path = ChromeDriverManager().install()
            # webdriver-manager sometimes returns wrong file, search for actual chromedriver
            import os
            import glob
            import subprocess
            
            # Search in the directory containing the returned path
            search_dir = os.path.dirname(base_path) if os.path.isfile(base_path) else base_path
            if not os.path.isdir(search_dir):
                search_dir = os.path.dirname(search_dir)
            
            # Find the actual chromedriver executable
            driver_path = None
            
            # Try common paths
            common_paths = [
                os.path.join(search_dir, 'chromedriver'),
                os.path.join(search_dir, 'chromedriver-mac-arm64', 'chromedriver'),
                os.path.join(search_dir, 'chromedriver-mac-x64', 'chromedriver'),
            ]
            
            for path in common_paths:
                if os.path.isfile(path):
                    driver_path = path
                    break
            
            # Fallback: manual search
            if not driver_path:
                for root, dirs, files in os.walk(search_dir):
                    for file in files:
                        if file == 'chromedriver' and not file.endswith('.txt') and not file.endswith('.md'):
                            full_path = os.path.join(root, file)
                            if os.path.isfile(full_path):
                                driver_path = full_path
                                break
                    if driver_path:
                        break
            
            if not driver_path or not os.path.isfile(driver_path):
                raise Exception(f"Could not find chromedriver executable in {search_dir}. Tried: {common_paths}")
            
            service = Service(driver_path)
            _driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"Warning: Could not initialize Chrome browser: {e}")
            import traceback
            traceback.print_exc()
            return None
    return _driver

def scrape_with_browser_sync(url: str) -> Optional[str]:
    """Scrape website using Selenium browser for JavaScript-rendered content"""
    import time
    driver = get_browser_driver()
    if not driver:
        return None
    
    try:
        # Execute script to hide webdriver property
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            '''
        })
        
        # For Amazon, visit homepage first and try to navigate to sign-in naturally
        if 'amazon.com' in url.lower():
            try:
                driver.get('https://www.amazon.com')
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(3)  # Wait for cookies/session and JavaScript to render
                
                # Try to find and click "Sign in" link on homepage (multiple strategies)
                sign_in_clicked = False
                try:
                    # Strategy 1: Find by link text
                    sign_in_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Sign in")
                    if not sign_in_links:
                        sign_in_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Sign In")
                    if not sign_in_links:
                        # Strategy 2: Find by CSS selector
                        sign_in_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='signin'], a[href*='ap/signin'], a[data-nav-role='signin']")
                    if not sign_in_links:
                        # Strategy 3: Find by ID
                        sign_in_links = driver.find_elements(By.ID, "nav-link-accountList")
                    
                    if sign_in_links:
                        print("Found sign-in link on homepage, clicking...")
                        # Scroll to element and click
                        driver.execute_script("arguments[0].scrollIntoView(true);", sign_in_links[0])
                        time.sleep(0.5)
                        sign_in_links[0].click()
                        time.sleep(5)  # Wait for navigation and page load
                        # Update current URL
                        current_url = driver.current_url
                        print(f"Navigated to: {current_url}")
                        sign_in_clicked = True
                except Exception as e:
                    print(f"Could not click sign-in link: {e}")
                    # Fall back to direct URL access
                    pass
                
                # If clicking didn't work or we want to use direct URL, navigate directly
                if not sign_in_clicked:
                    driver.get(url)
                    time.sleep(2)
            except:
                # If homepage visit fails, just go to the URL directly
                driver.get(url)
                time.sleep(2)
        
        driver.get(url)
        # Wait for page to load and any dynamic content
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Check current URL (may have redirected)
        current_url = driver.current_url
        
        # For Amazon, check if page is error/redirect page and wait for actual login page
        if 'amazon.com' in url.lower():
            html_preview = driver.page_source
            html_lower = html_preview.lower()
            
            # If page is short, contains error, or seems like redirect, wait for actual page to load
            if len(html_preview) < 5000 or 'error' in html_lower or 'login' in html_lower:
                print(f"Detected potential error/redirect page (length: {len(html_preview)}), waiting for actual login page...")
                initial_url = current_url
                initial_html_len = len(html_preview)
                
                # Wait for URL to change or page content to change significantly
                for i in range(15):  # Wait up to 15 seconds
                    time.sleep(1)
                    current_url = driver.current_url
                    html_check = driver.page_source
                    html_check_lower = html_check.lower()
                    
                    # Check if page content changed significantly (likely loaded actual page)
                    if (len(html_check) > 10000 and len(html_check) > initial_html_len * 2) or \
                       (len(html_check) > 5000 and 'password' in html_check_lower and 'input' in html_check_lower):
                        print(f"Page loaded successfully. URL: {current_url}, HTML length: {len(html_check)}")
                        break
                    # Also check if URL changed
                    if current_url != initial_url and 'signin' in current_url.lower():
                        print(f"URL changed to: {current_url}")
                        time.sleep(2)  # Wait a bit more after URL change
                        break
                
                # Additional wait for JavaScript to render after page loads
                time.sleep(3)
        
        # Additional wait for JavaScript to render (longer for complex sites like Amazon)
        time.sleep(5)
        
        # Try to wait for input fields to appear (for login pages)
        try:
            WebDriverWait(driver, 10).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[name*='email']")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[id*='email']")),
                )
            )
            time.sleep(2)  # Additional wait after inputs appear
        except:
            pass  # Continue even if inputs don't appear
        
        # Get the rendered HTML
        html = driver.page_source
        
        # If HTML is too short, might be an error page or redirect
        if len(html) < 1000:
            print(f"Warning: HTML is very short ({len(html)} chars), page might not have loaded correctly")
        
        return html
    except Exception as e:
        print(f"Browser scraping error for {url}: {e}")
        return None

async def scrape_with_browser(url: str) -> Optional[str]:
    """Async wrapper for browser scraping"""
    # Run in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, scrape_with_browser_sync, url)

class ScrapeRequest(BaseModel):
    url: Optional[str] = None
    urls: Optional[List[str]] = None

class AuthComponent(BaseModel):
    found: bool
    htmlSnippet: Optional[str] = None
    formElement: Optional[str] = None
    usernameInput: Optional[str] = None
    passwordInput: Optional[str] = None
    submitButton: Optional[str] = None
    method: Optional[str] = None
    action: Optional[str] = None

class ScrapeResult(BaseModel):
    url: str
    success: bool
    error: Optional[str] = None
    authComponent: Optional[AuthComponent] = None

def detect_auth_components(html: str, base_url: str) -> AuthComponent:
    """Detect authentication components in web pages with enhanced HTML parsing"""
    soup = BeautifulSoup(html, 'lxml')
    
    # Find password input fields
    password_inputs = soup.find_all('input', {'type': 'password'})
    
    if not password_inputs:
        return AuthComponent(found=False)
    
    # Find the nearest parent form containing the password input
    auth_form = None
    form_element = None
    
    for password_input in password_inputs:
        # First, try to find parent form
        form = password_input.find_parent('form')
        
        if form:
            auth_form = form
            form_element = form
            break
        
        # If no form tag found, search more broadly for containers with authentication elements
        # Look for divs, sections, or other containers that might contain login forms
        parent = password_input.parent
        max_depth = 10  # Limit search depth
        depth = 0
        
        while parent and parent.name and parent.name != 'body' and depth < max_depth:
            depth += 1
            
            # Check for username/email inputs in the same container
            # Look for various patterns: type, name, id, placeholder, aria-label
            username_patterns = [
                {'type': 'text'},
                {'type': 'email'},
                {'name': lambda x: x and any(k in x.lower() for k in ['user', 'login', 'email', 'account', 'phone'])},
                {'id': lambda x: x and any(k in x.lower() for k in ['user', 'login', 'email', 'account', 'phone'])},
                {'placeholder': lambda x: x and any(k in x.lower() for k in ['email', 'phone', 'user', 'account'])},
                {'aria-label': lambda x: x and any(k in x.lower() for k in ['email', 'phone', 'user', 'account'])},
            ]
            
            username_found = False
            for pattern in username_patterns:
                if parent.find('input', pattern):
                    username_found = True
                    break
            
            # Also check for password input in the same container
            password_found = parent.find('input', {'type': 'password'}) is not None
            
            # If we found both username and password in the same container, this is likely an auth form
            if username_found and password_found:
                auth_form = parent
                form_element = parent
                break
            
            # Also check for common authentication container classes/ids
            container_attrs = parent.attrs if hasattr(parent, 'attrs') else {}
            class_names = ' '.join(container_attrs.get('class', [])).lower() if 'class' in container_attrs else ''
            container_id = container_attrs.get('id', '').lower() if 'id' in container_attrs else ''
            
            auth_keywords = ['login', 'signin', 'sign-in', 'auth', 'authentication', 'form']
            if any(keyword in class_names or keyword in container_id for keyword in auth_keywords):
                if password_found:
                    auth_form = parent
                    form_element = parent
                    break
            
            parent = parent.parent
    
    # If still no form found, try to find the closest meaningful container
    if not auth_form:
        first_password = password_inputs[0]
        # Try to find a container div that likely contains the form
        parent = first_password.parent
        for _ in range(5):  # Go up to 5 levels
            if parent and parent.name:
                # Check if this container has multiple inputs (likely a form)
                all_inputs = parent.find_all('input')
                if len(all_inputs) >= 2:  # At least username and password
                    auth_form = parent
                    form_element = parent
                    break
            if parent:
                parent = parent.parent
            else:
                break
        
        # Last resort: use password input's parent container
        if not auth_form:
            if first_password.parent:
                auth_form = first_password.parent.parent if first_password.parent.parent else first_password.parent
            else:
                auth_form = first_password
    
    # Extract form-related information with enhanced patterns
    username_input = None
    if auth_form:
        # Try multiple patterns to find username input
        username_patterns = [
            {'type': 'text'},
            {'type': 'email'},
            {'type': 'tel'},  # Phone number
            {'name': lambda x: x and any(k in x.lower() for k in ['user', 'login', 'email', 'account', 'phone', 'mobile'])},
            {'id': lambda x: x and any(k in x.lower() for k in ['user', 'login', 'email', 'account', 'phone', 'mobile'])},
            {'placeholder': lambda x: x and any(k in x.lower() for k in ['email', 'phone', 'user', 'account', 'username'])},
            {'aria-label': lambda x: x and any(k in x.lower() for k in ['email', 'phone', 'user', 'account'])},
            {'autocomplete': lambda x: x and any(k in x.lower() for k in ['username', 'email', 'tel'])},
        ]
        
        for pattern in username_patterns:
            found = auth_form.find('input', pattern)
            if found:
                username_input = found
                break
    
    password_input = auth_form.find('input', {'type': 'password'}) if auth_form else None
    
    # Enhanced submit button detection
    submit_button = None
    if auth_form:
        submit_patterns = [
            {'type': 'submit'},
            {'type': 'button', 'class': lambda x: x and any(k in ' '.join(x).lower() if isinstance(x, list) else str(x).lower() for k in ['submit', 'login', 'sign'])},
            {'type': 'button', 'id': lambda x: x and any(k in x.lower() for k in ['submit', 'login', 'sign'])},
            {'type': 'button', 'name': lambda x: x and any(k in x.lower() for k in ['submit', 'login', 'sign'])},
        ]
        
        for pattern in submit_patterns:
            found = auth_form.find('input', pattern) or auth_form.find('button', pattern)
            if found:
                submit_button = found
                break
        
        # Also check button text content
        if not submit_button:
            buttons = auth_form.find_all('button')
            for button in buttons:
                text = button.get_text().lower() if button.get_text() else ''
                if any(k in text for k in ['sign in', 'login', 'log in', 'submit', 'continue', 'next']):
                    submit_button = button
                    break
    
    # Get form method and action
    method = 'GET'
    action = base_url
    
    if form_element and hasattr(form_element, 'get'):
        method = form_element.get('method', 'GET').upper()
        action_attr = form_element.get('action', '')
        if action_attr:
            try:
                action = urljoin(base_url, action_attr)
            except:
                action = base_url
        else:
            action = base_url
    
    return AuthComponent(
        found=True,
        htmlSnippet=str(auth_form).strip() if auth_form else '',
        formElement=str(form_element).strip() if form_element else '',
        usernameInput=str(username_input).strip() if username_input else '',
        passwordInput=str(password_input).strip() if password_input else '',
        submitButton=str(submit_button).strip() if submit_button else '',
        method=method,
        action=action,
    )

async def scrape_website(url: str) -> ScrapeResult:
    """Scrape website and detect authentication components"""
    try:
        # Validate URL format
        try:
            parsed = urlparse(url)
            if not parsed.scheme:
                url = f"https://{url}"
            parsed = urlparse(url)
            if not parsed.netloc:
                raise ValueError("Invalid URL")
        except:
            return ScrapeResult(
                url=url,
                success=False,
                error="Invalid URL format"
            )
        
        # First, try static HTTP method (faster)
        # Enhanced headers to mimic real browser and bypass anti-bot measures
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers)
                
                # Accept 200 and redirect status codes
                if response.status_code not in [200, 301, 302, 303, 307, 308]:
                    # If HTTP fails, try browser
                    print(f"HTTP request failed with status {response.status_code}, trying browser...")
                    html = await scrape_with_browser(url)
                    if html and len(html) > 500:
                        auth_component = detect_auth_components(html, url)
                        return ScrapeResult(
                            url=url,
                            success=True,
                            authComponent=auth_component
                        )
                    return ScrapeResult(
                        url=url,
                        success=False,
                        error=f"HTTP Error: {response.status_code} {response.reason_phrase}"
                    )
                
                html = response.text
                
                # Check for anti-bot indicators
                html_lower = html.lower()
                anti_bot_indicators = [
                    len(html) < 1000,  # Very short HTML (likely error/blocked page)
                    'captcha' in html_lower,
                    ('robot' in html_lower and 'detected' in html_lower),
                    'access denied' in html_lower,
                    'blocked' in html_lower,
                    ('cloudflare' in html_lower and 'checking' in html_lower),
                    'please enable javascript' in html_lower,
                    # For Amazon specifically - check for error pages
                    ('amazon.com' in url.lower() and 'ap_error' in html_lower and len(html) < 5000),
                    # Check if page mentions "login" but HTML is very short (likely redirect page)
                    ('login' in html_lower and len(html) < 3000 and 'password' not in html_lower),
                ]
                
                needs_browser = any(anti_bot_indicators)
                
                if needs_browser:
                    print(f"Anti-bot protection detected for {url}, switching to browser...")
                    browser_html = await scrape_with_browser(url)
                    if browser_html and len(browser_html) > 500:
                        # Check if browser got better results
                        browser_lower = browser_html.lower()
                        if len(browser_html) > len(html) * 2 or ('password' in browser_lower and 'password' not in html_lower):
                            print(f"Browser got better results (length: {len(browser_html)} vs {len(html)})")
                            html = browser_html
                        else:
                            print(f"Browser results similar, using HTTP result")
                    else:
                        print(f"Browser also failed, using HTTP result")
                
                # Detect authentication components
                auth_component = detect_auth_components(html, url)
                
                return ScrapeResult(
                    url=url,
                    success=True,
                    authComponent=auth_component
                )
                
            except httpx.TimeoutException:
                # Timeout - try browser as fallback
                print(f"HTTP request timeout for {url}, trying browser...")
                html = await scrape_with_browser(url)
                if html and len(html) > 500:
                    auth_component = detect_auth_components(html, url)
                    return ScrapeResult(
                        url=url,
                        success=True,
                        authComponent=auth_component
                    )
                return ScrapeResult(
                    url=url,
                    success=False,
                    error="Request timeout"
                )
            except Exception as e:
                # Other HTTP errors - try browser as fallback
                print(f"HTTP request error for {url}: {e}, trying browser...")
                html = await scrape_with_browser(url)
                if html and len(html) > 500:
                    auth_component = detect_auth_components(html, url)
                    return ScrapeResult(
                        url=url,
                        success=True,
                        authComponent=auth_component
                    )
                return ScrapeResult(
                    url=url,
                    success=False,
                    error=str(e) or "Unknown error occurred while scraping the website"
                )
    except httpx.TimeoutException:
        return ScrapeResult(
            url=url,
            success=False,
            error="Request timeout"
        )
    except Exception as e:
        return ScrapeResult(
            url=url,
            success=False,
            error=str(e) or "Unknown error occurred while scraping the website"
        )

@app.get("/")
async def root():
    return {"message": "Website Authentication Component Detector API"}

@app.post("/api/scrape", response_model=ScrapeResult)
async def scrape_single(request: ScrapeRequest):
    if not request.url:
        raise HTTPException(status_code=400, detail="Please provide url parameter")
    
    return await scrape_website(request.url)

@app.get("/api/scrape", response_model=ScrapeResult)
async def scrape_single_get(url: str):
    return await scrape_website(url)

@app.post("/api/scrape/batch")
async def scrape_batch(request: ScrapeRequest):
    if not request.urls:
        raise HTTPException(status_code=400, detail="Please provide urls parameter")
    
    import asyncio
    results = await asyncio.gather(*[scrape_website(url) for url in request.urls])
    return {"results": results}

@app.get("/api/predefined")
async def scrape_predefined():
    # Predefined 5 different types of websites (using static HTML sites)
    predefined_websites = [
        'https://github.com/login',
        'https://stackoverflow.com/users/login',
        'https://www.linkedin.com/login',
        'https://www.quora.com/login',
        'https://www.dropbox.com/login',
    ]
    
    import asyncio
    results = await asyncio.gather(*[scrape_website(url) for url in predefined_websites])
    return {"results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

