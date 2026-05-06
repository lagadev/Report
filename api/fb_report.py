import requests
import random
import re
import logging
import json
from typing import Optional, Tuple, List
from datetime import datetime

logger = logging.getLogger(__name__)


class FacebookReporter:
    """
    Facebook Help Center impersonation report automation.
    
    Uses the Facebook Help Center contact form (ID: 295309487309948)
    to report impersonating profiles.
    
    Note: Facebook requires various dynamic tokens (fb_dtsg, lsd, etc.)
    that are extracted from the help page before submitting.
    """

    HELP_PAGE_URL = "https://www.facebook.com/help/contact/295309487309948"
    SUBMIT_URL = "https://www.facebook.com/ajax/help/contact/submit/page"

    HEADERS_TEMPLATE = {
        "authority": "www.facebook.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,ar-DZ;q=0.8,ar;q=0.7,fr;q=0.6,hu;q=0.5",
        "content-type": "application/x-www-form-urlencoded",
        "dpr": "1",
        "origin": "https://www.facebook.com",
        "referer": "https://www.facebook.com/help/contact/295309487309948",
        "sec-ch-prefers-color-scheme": "dark",
        "sec-ch-ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "sec-ch-ua-full-version-list": '"Not A(Brand";v="99.0.0.0", "Google Chrome";v="121.0.6167.85", "Chromium";v="121.0.6167.85"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.85 Mobile Safari/537.36",
        "x-asbd-id": "129477",
        "x-fb-lsd": None,  # Will be extracted from page
        "cookie": None     # Will be set dynamically
    }

    USER_AGENTS = [
        "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.85 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.64 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone14,3; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.85 Safari/537.36",
    ]

    LETTERS = 'qwertyuiopasdfghjklzxcvbnm._1234567890'

    def __init__(
        self,
        target_profile_url: str,
        imposter_full_name: str,
        your_full_name: str,
        your_email: str,
        imposter_email_or_phone: Optional[str] = None,
        additional_info: Optional[str] = None,
        use_proxy: bool = False,
        proxy_protocol: Optional[str] = None,
        proxy_list: Optional[List[str]] = None,
        timeout: int = 10
    ):
        self.target_profile_url = target_profile_url
        self.imposter_full_name = imposter_full_name
        self.your_full_name = your_full_name
        self.your_email = your_email
        self.imposter_email_or_phone = imposter_email_or_phone or ""
        self.additional_info = additional_info or ""
        self.use_proxy = use_proxy
        self.proxy_protocol = proxy_protocol
        self.proxy_list = proxy_list or []
        self.timeout = timeout
        self.report_count = 0

    def _get_random_user_agent(self) -> str:
        """Get a random user-agent from the pool."""
        return random.choice(self.USER_AGENTS)

    def _generate_random_email(self) -> str:
        """Generate a random email for each request."""
        boy = "".join(random.choice(self.LETTERS) for _ in range(10))
        return f"{boy}@gmail.com"

    def _extract_page_tokens(self, html: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Extract required tokens (fb_dtsg, lsd, revision, hsi) from the help page HTML.
        These change periodically and are required for form submission.
        """
        fb_dtsg = None
        lsd = None
        revision = None
        hsi = None

        # Extract fb_dtsg
        match = re.search(r'name="fb_dtsg"[^>]+value="([^"]+)"', html)
        if match:
            fb_dtsg = match.group(1)

        # Extract lsd (LSD token)
        match = re.search(r'name="lsd"[^>]+value="([^"]+)"', html)
        if match:
            lsd = match.group(1)

        # Extract revision (__rev)
        match = re.search(r'"revision":\s*"?(\d+)"?', html)
        if match:
            revision = match.group(1)

        # Extract hsi
        match = re.search(r'"hsi":\s*"?(\d+)"?', html)
        if match:
            hsi = match.group(1)

        # Fallback: try to extract from server JS init data
        if not fb_dtsg or not lsd:
            match = re.search(r'LSD",\[\],{"token":"([^"]+)"', html)
            if match:
                lsd = match.group(1)
            match = re.search(r'DTSGInitialData",\[\],{"token":"([^"]+)"', html)
            if match:
                fb_dtsg = match.group(1)

        return fb_dtsg, lsd, revision, hsi

    def _extract_cookies_from_response(self, response) -> dict:
        """Extract cookies from a requests response."""
        cookies = {}
        for cookie in response.cookies:
            cookies[cookie.name] = cookie.value
        return cookies

    def _get_proxy_dict(self) -> Optional[dict]:
        """Build proxy dict from available proxies."""
        if not self.use_proxy or not self.proxy_list:
            return None
        proxy_addr = random.choice(self.proxy_list)
        return {self.proxy_protocol: proxy_addr}

    def _fetch_help_page(self) -> Tuple[Optional[str], Optional[dict], Optional[str]]:
        """
        Fetch the Facebook help contact page to extract tokens and cookies.
        
        Returns:
            Tuple of (html_content, cookies_dict, error_message)
        """
        headers = {
            "User-Agent": self._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        
        proxies = self._get_proxy_dict()

        try:
            session = requests.Session()
            resp = session.get(
                self.HELP_PAGE_URL,
                headers=headers,
                proxies=proxies,
                timeout=self.timeout
            )
            
            if resp.status_code == 200:
                cookies = self._extract_cookies_from_response(resp)
                return resp.text, cookies, None
            else:
                return None, None, f"Help page returned HTTP {resp.status_code}"
                
        except requests.exceptions.Timeout:
            return None, None, "Timeout fetching help page"
        except requests.exceptions.ProxyError as e:
            return None, None, f"Proxy error: {e}"
        except Exception as e:
            return None, None, f"Error fetching help page: {e}"

    def _build_payload(
        self,
        fb_dtsg: str,
        lsd: str,
        revision: str,
        hsi: str,
        email: str
    ) -> str:
        """
        Build the form payload for the impersonation report.
        Form ID: 295309487309948
        """
        now = datetime.now()
        timestamp = str(int(datetime.timestamp(now)))

        # These field IDs correspond to the form fields in the impersonation report form
        payload = {
            # Form identification
            "support_form_id": "295309487309948",
            "support_form_locale_id": "en_US",
            "support_form_hidden_fields": "{}",
            "support_form_fact_false_fields": "[]",
            
            # Tokens
            "lsd": lsd,
            "fb_dtsg": fb_dtsg,
            "jazoest": "2931",
            
            # Form fields - the field IDs need to match the help center form
            # "Your full name"
            "Field107542598198311": self.your_full_name,
            # "Your contact email address"
            "Field679904240792544": email,
            # "Full name on the impostor profile"
            "Field156667621008765": self.imposter_full_name,
            # "Email address or phone number on impostor profile"
            "Field198417678561124": self.imposter_email_or_phone,
            # "Link (URL) to the impostor profile"
            "Field706618506277058": self.target_profile_url,
            # "Additional info"
            "Field479060842982671": self.additional_info,
            
            # System fields
            "__user": "0",
            "__a": "1",
            "__req": str(random.randint(1, 9)),
            "__hs": f"19552.BP:DEFAULT.2.0.0.0",
            "dpr": "1",
            "__ccg": "GOOD",
            "__rev": revision or "1007841948",
            "__s": "s4c6vz:napxo9:n9ncx2",
            "__hsi": hsi or "7255652935514227640",
            "__dyn": "7xe6E5aQ1PyUbFuC1swgE98nwgU6C7UW8xi642-7E2vwXw5ux60Vo1upE4W0OE2WxO2O1Vwooa81VohwnU1e42C220qu1Tw40wdq0Ho2ewnE3fw6iw4vwbS1Lw4Cwcq",
            "__csr": "",
            "__spin_r": revision or "1007841948",
            "__spin_b": "trunk",
            "__spin_t": timestamp,
        }
        
        # Build URL-encoded string
        return "&".join(f"{k}={requests.utils.quote(str(v), safe='')}" for k, v in payload.items())

    def send_report(self) -> Tuple[bool, str]:
        """
        Send a single Facebook impersonation report.
        
        This performs two steps:
        1. Fetch the help page to get dynamic tokens (fb_dtsg, lsd)
        2. Submit the report form with those tokens
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Step 1: Fetch help page and extract tokens
        html, cookies, error = self._fetch_help_page()
        
        if error or not html:
            return False, f"Failed to fetch help page: {error}"
        
        fb_dtsg, lsd, revision, hsi = self._extract_page_tokens(html)
        
        if not fb_dtsg or not lsd:
            logger.warning("Could not extract fb_dtsg or lsd from page, using fallback values")
            fb_dtsg = fb_dtsg or "NOnDe"
            lsd = lsd or "AVq5uabXj48"
        
        # Step 2: Generate email and build payload
        email = self._generate_random_email()
        payload = self._build_payload(fb_dtsg, lsd, revision, hsi, email)
        
        # Build headers
        headers = dict(self.HEADERS_TEMPLATE)
        headers["x-fb-lsd"] = lsd
        headers["User-Agent"] = self._get_random_user_agent()
        
        # Build cookie string
        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            headers["cookie"] = cookie_str
        
        proxies = self._get_proxy_dict()
        
        # Step 3: Submit the report
        try:
            resp = requests.post(
                self.SUBMIT_URL,
                data=payload,
                headers=headers,
                proxies=proxies,
                timeout=self.timeout
            )
            
            if resp.status_code == 200:
                self.report_count += 1
                # Try to parse response for additional info
                try:
                    resp_data = resp.text
                    if "success" in resp_data.lower():
                        return True, "Report submitted successfully"
                    else:
                        return True, f"Report sent (HTTP 200). Response: {resp_data[:200]}"
                except:
                    return True, "Report submitted successfully (HTTP 200)"
            else:
                return False, f"Server returned HTTP {resp.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Request timed out during submission"
        except requests.exceptions.ProxyError as e:
            return False, f"Proxy error during submission: {e}"
        except Exception as e:
            return False, f"Submission error: {e}"

    def report_once(self) -> Tuple[bool, str, int]:
        """Send a single report and return structured result."""
        success, message = self.send_report()
        return success, message, 1 if success else 0

    def report_burst(self, count: int = 5) -> Tuple[bool, str, int]:
        """
        Send multiple reports in burst mode.
        
        Args:
            count: Number of reports (max 30 to avoid rate limiting)
            
        Returns:
            Tuple of (overall_success, summary_message, total_sent)
        """
        count = min(count, 30)  # Safety cap for Facebook
        success_count = 0
        fail_count = 0
        last_error = ""
        
        for i in range(count):
            success, message = self.send_report()
            
            if success:
                success_count += 1
            else:
                fail_count += 1
                last_error = message
            
            # Small delay between requests to avoid rate limiting
            if i < count - 1:
                import time
                time.sleep(random.uniform(1.0, 3.0))
        
        message = (
            f"Burst complete: {success_count}/{count} reports sent successfully"
            + (f", {fail_count} failed" if fail_count > 0 else "")
            + (f". Last error: {last_error}" if fail_count > 0 and last_error else "")
        )
        
        return success_count > 0, message, success_count
