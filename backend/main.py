from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import asyncio
from playwright.async_api import async_playwright, Browser, Page

app = FastAPI(title="Website Authentication Component Detector API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Playwright browser instance
_playwright = None
_browser: Optional[Browser] = None

@app.on_event("startup")
async def startup_event():
    """Initialize Playwright browser on startup"""
    global _playwright, _browser
    try:
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
    except Exception as e:
        print(f"Warning: Could not initialize Playwright browser: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Close Playwright browser on shutdown"""
    global _browser, _playwright
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()

def is_login_url(url: str) -> bool:
    """Check if URL appears to be a login/signin page"""
    url_lower = url.lower()
    login_keywords = ['login', 'signin', 'sign-in', 'sign_in', 'auth', 'authenticate', 'log-in']
    return any(keyword in url_lower for keyword in login_keywords)

async def find_and_click_login_link(page: Page, base_url: str) -> bool:
    """Find and click login/signin link on the current page"""
    try:
        # Common selectors for login links
        login_selectors = [
            'a[href*="login"]',
            'a[href*="signin"]',
            'a[href*="sign-in"]',
            'a[href*="auth"]',
            'a:has-text("Sign in")',
            'a:has-text("Sign In")',
            'a:has-text("Login")',
            'a:has-text("Log in")',
            'a:has-text("Log In")',
            'button:has-text("Sign in")',
            'button:has-text("Login")',
        ]
        
        # Domain-specific selectors
        domain = base_url.lower()
        if 'amazon.com' in domain:
            login_selectors.extend([
                '#nav-link-accountList',
                'a[href*="ap/signin"]',
            ])
        elif 'github.com' in domain:
            login_selectors.extend([
                'a[href="/login"]',
            ])
        elif 'linkedin.com' in domain:
            login_selectors.extend([
                'a[href*="/login"]',
            ])
        
        for selector in login_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    # Check if element is visible
                    is_visible = await element.is_visible()
                    if is_visible:
                        print(f"Found login link with selector: {selector}")
                        await element.click()
                        await asyncio.sleep(2)  # Wait for navigation
                        return True
            except:
                continue
        
        return False
    except Exception as e:
        print(f"Error finding login link: {e}")
        return False

async def scrape_with_playwright(url: str) -> Optional[str]:
    """Scrape website using Playwright for JavaScript-rendered content"""
    global _browser
    if not _browser:
        return None
    
    try:
        context = await _browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US'
        )
        page = await context.new_page()
        
        # Parse URL to get base domain
        from urllib.parse import urlparse
        parsed = urlparse(url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
        
        # Check if URL is already a login page
        is_login = is_login_url(url)
        
        if not is_login:
            # Step 1: Visit homepage first
            print(f"URL doesn't appear to be a login page, visiting homepage: {base_domain}")
            try:
                await page.goto(base_domain, wait_until='domcontentloaded', timeout=15000)
                await asyncio.sleep(2)  # Wait for page to load
                
                # Step 2: Try to find and click login link
                print("Searching for login link on homepage...")
                login_clicked = await find_and_click_login_link(page, base_domain)
                
                if not login_clicked:
                    # If couldn't find login link, try common login URLs
                    print("Could not find login link, trying common login URLs...")
                    common_login_paths = ['/login', '/signin', '/sign-in', '/auth/login']
                    for path in common_login_paths:
                        try:
                            login_url = f"{base_domain}{path}"
                            await page.goto(login_url, wait_until='domcontentloaded', timeout=15000)
                            await asyncio.sleep(2)
                            # Check if we're on a login page now
                            html_check = await page.content()
                            if 'password' in html_check.lower() or 'login' in html_check.lower():
                                print(f"Successfully navigated to login page: {login_url}")
                                break
                        except:
                            continue
            except Exception as e:
                print(f"Error visiting homepage: {e}, trying original URL...")
                await page.goto(url, wait_until='domcontentloaded', timeout=20000)
        else:
            # URL is already a login page, but for some sites (like Amazon) we still need to visit homepage first
            if 'amazon.com' in base_domain.lower():
                try:
                    print("Visiting Amazon homepage to establish session...")
                    await page.goto('https://www.amazon.com', wait_until='domcontentloaded', timeout=15000)
                    await asyncio.sleep(2)  # Wait for cookies/session
                    
                    # Then navigate to signin
                    login_clicked = await find_and_click_login_link(page, base_domain)
                    if not login_clicked:
                        await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                except:
                    await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            else:
                # Direct navigation to login URL
                await page.goto(url, wait_until='domcontentloaded', timeout=20000)
        
        # Wait for page to fully load and JavaScript to execute
        await asyncio.sleep(3)
        
        # Try to wait for login form elements to appear
        try:
            await page.wait_for_selector('input[type="password"], input[type="email"], input[name*="email"], input[name*="user"], input[id*="email"]', timeout=8000)
            await asyncio.sleep(1)  # Additional wait after elements appear
        except:
            # Even if selector doesn't appear, continue to get HTML
            pass
        
        # Get the rendered HTML
        html = await page.content()
        
        await context.close()
        return html
    except Exception as e:
        print(f"Playwright scraping error for {url}: {e}")
        return None


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
        # Enhanced headers to mimic real browser
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
        
        html = None
        static_success = False
        needs_playwright = False
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=headers)
                
                # Accept 200 and redirect status codes
                if response.status_code in [200, 301, 302, 303, 307, 308]:
                    html = response.text
                    static_success = True
                    
                    # Check if we got meaningful content
                    if len(html) > 500:
                        # Detect authentication components from static HTML
                        auth_component = detect_auth_components(html, url)
                        
                        # If found authentication component, return success
                        if auth_component.found:
                            return ScrapeResult(
                                url=url,
                                success=True,
                                authComponent=auth_component
                            )
                        
                        # If static method worked but no auth found, check if we need to use Playwright
                        html_lower = html.lower()
                        needs_playwright = (
                            len(html) < 1000 or
                            'captcha' in html_lower or
                            ('robot' in html_lower and 'detected' in html_lower) or
                            'access denied' in html_lower or
                            'please enable javascript' in html_lower or
                            ('amazon.com' in url.lower() and 'ap_error' in html_lower and len(html) < 5000)
                        )
                        
                        # If URL is not a login URL and no auth found, try Playwright to find login link
                        if not auth_component.found and not is_login_url(url):
                            needs_playwright = True
                            print(f"No login form found on homepage, will use Playwright to find login link...")
                        
                        # If static method worked, no auth found, and no need for Playwright, return result
                        if not needs_playwright:
                            return ScrapeResult(
                                url=url,
                                success=True,
                                authComponent=auth_component
                            )
            except httpx.TimeoutException:
                needs_playwright = True  # Will try Playwright
            except Exception as e:
                needs_playwright = True  # Will try Playwright
        
        # If static method failed, detected issues, or needs to find login link, try Playwright
        if needs_playwright or not static_success or (html and len(html) < 1000):
            print(f"Trying Playwright for {url}...")
            playwright_html = await scrape_with_playwright(url)
            
            if playwright_html and len(playwright_html) > 500:
                auth_component = detect_auth_components(playwright_html, url)
                return ScrapeResult(
                    url=url,
                    success=True,
                    authComponent=auth_component
                )
            elif static_success and html:
                # Playwright failed, but we have static HTML, return that
                auth_component = detect_auth_components(html, url)
                return ScrapeResult(
                    url=url,
                    success=True,
                    authComponent=auth_component
                )
        
        # Both methods failed
        if not static_success:
            return ScrapeResult(
                url=url,
                success=False,
                error="Both static HTTP and Playwright methods failed"
            )
        else:
            # Static method succeeded but no auth found
            auth_component = detect_auth_components(html, url)
            return ScrapeResult(
                url=url,
                success=True,
                authComponent=auth_component
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

