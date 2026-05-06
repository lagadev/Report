import requests
import random
import os
import logging
from datetime import datetime
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class InstagramReporter:
    """
    Instagram help center report sender.
    Abuses the Instagram help center contact form to send reports.
    """

    HELP_URL = "https://help.instagram.com/ajax/help/contact/submit/page"
    REFERER = "https://help.instagram.com/contact/723586364339719"

    HEADERS = {
        "Host": "help.instagram.com",
        "x-fb-lsd": "AVq5uabXj48",
        "x-asbd-id": "129477",
        "sec-ch-ua-mobile": "?1",
        "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; Plume L2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.88 Mobile Safari/537.36",
        "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
        "sec-ch-ua-platform": '"Android"',
        "content-type": "application/x-www-form-urlencoded",
        "accept": "*/*",
        "origin": "https://help.instagram.com",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://help.instagram.com/contact/723586364339719",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9,ar-DZ;q=0.8,ar;q=0.7,fr;q=0.6,hu;q=0.5",
        "cookie": "ig_nrcb=1"
    }

    LETTERS = 'qwertyuiopasdfghjklzxcvbnm._1234567890'

    def __init__(
        self,
        username: str,
        account_name: str,
        use_proxy: bool = False,
        proxy_protocol: Optional[str] = None,
        proxy_file: Optional[str] = None,
        timeout: int = 5
    ):
        self.username = username
        self.account_name = account_name
        self.use_proxy = use_proxy
        self.proxy_protocol = proxy_protocol
        self.proxy_file = proxy_file
        self.timeout = timeout
        self.report_count = 0
        self.proxy_list = []
        
        if self.use_proxy and self.proxy_file:
            self._load_proxies()

    def _load_proxies(self):
        """Load proxy list from file."""
        try:
            with open(self.proxy_file, 'r') as f:
                self.proxy_list = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(self.proxy_list)} proxies from {self.proxy_file}")
        except FileNotFoundError:
            logger.warning(f"Proxy file {self.proxy_file} not found. Running without proxies.")
            self.use_proxy = False
        except Exception as e:
            logger.error(f"Error loading proxy file: {e}")
            self.use_proxy = False

    def _generate_email(self) -> str:
        """Generate a random email address."""
        boy = "".join(random.choice(self.LETTERS) for _ in range(10))
        return f"{boy}@gmail.com"

    def _build_payload(self) -> str:
        """Build the form data payload."""
        now = datetime.now()
        timestamp = str(int(datetime.timestamp(now)))
        email = self._generate_email()

        data = (
            f'jazoest=2931'
            f'&lsd=AVq5uabXj48'
            f'&Field258021274378282={self.username}'
            f'&Field735407019826414={self.account_name}'
            f'&Field506888789421014[year]=2014'
            f'&Field506888789421014[month]=11'
            f'&Field506888789421014[day]=11'
            f'&Field294540267362199=Parent'
            f'&inputEmail={email}'
            f'&support_form_id=723586364339719'
            f'&support_form_locale_id=en_US'
            f'&support_form_hidden_fields=%7B%7D'
            f'&support_form_fact_false_fields=[]'
            f'&__user=0&__a=1&__req=6'
            f'&__hs=19552.BP%3ADEFAULT.2.0..0.0'
            f'&dpr=1&__ccg=GOOD'
            f'&__rev=1007841948'
            f'&__s=s4c6vz%3Anapxo9%3An9ncx2'
            f'&__hsi=7255652935514227640'
            f'&__dyn=7xe6E5aQ1PyUbFuC1swgE98nwgU6C7UW8xi642-7E2vwXw5ux60Vo1upE4W0OE2WxO2O1Vwooa81VohwnU1e42C220qu1Tw40wdq0Ho2ewnE3fw6iw4vwbS1Lw4Cwcq'
            f'&__csr='
            f'&__spin_r=1007841948'
            f'&__spin_b=trunk'
            f'&__spin_t={timestamp}'
        )
        return data

    def _get_proxies(self) -> Optional[dict]:
        """Get proxy dict if proxy is enabled."""
        if not self.use_proxy or not self.proxy_list:
            return None
        
        proxy_addr = random.choice(self.proxy_list)
        return {self.proxy_protocol: proxy_addr}

    def send_report(self) -> Tuple[bool, int]:
        """
        Send a single report request.
        
        Returns:
            Tuple of (success: bool, status_code: int)
        """
        data = self._build_payload()
        proxies = self._get_proxies()
        
        try:
            resp = requests.post(
                self.HELP_URL,
                data=data,
                headers=self.HEADERS,
                proxies=proxies,
                timeout=self.timeout
            )
            
            if resp.status_code == 200:
                self.report_count += 1
                return True, resp.status_code
            else:
                return False, resp.status_code
                
        except requests.exceptions.Timeout:
            logger.warning("Request timed out")
            return False, 0
        except requests.exceptions.ProxyError as e:
            logger.warning(f"Proxy error: {e}")
            return False, 0
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return False, 0

    def report_once(self) -> Tuple[bool, str, int]:
        """Send a single report and return result."""
        success, status = self.send_report()
        
        if success:
            return True, f"Report sent successfully (HTTP {status})", 1
        elif status == 0:
            return False, f"Request failed (network/proxy error)", 0
        else:
            return False, f"Server returned HTTP {status}", 0

    def report_burst(self, count: int = 10) -> Tuple[bool, str, int]:
        """
        Send multiple reports in burst mode.
        
        Args:
            count: Number of reports to send (max 100 for safety)
            
        Returns:
            Tuple of (overall_success, message, total_sent)
        """
        count = min(count, 100)  # Safety cap
        success_count = 0
        fail_count = 0
        
        for i in range(count):
            success, status = self.send_report()
            
            if success:
                success_count += 1
            else:
                fail_count += 1
        
        message = (
            f"Burst complete: {success_count}/{count} reports sent successfully"
            + (f", {fail_count} failed" if fail_count > 0 else "")
        )
        
        return success_count > 0, message, success_count


# Module-level instance for potential direct usage
reporter: Optional[InstagramReporter] = None
