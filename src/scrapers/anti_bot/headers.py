"""Sistema de rotación de headers y user agents."""
import random
from typing import Dict
from fake_useragent import UserAgent


class HeaderRotator:
    """Rotador de headers para evitar detección."""
    
    def __init__(self):
        self.ua = UserAgent()
        
        # Headers base realistas
        self.base_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
        
        # Pool de referers comunes en Perú
        self.referers = [
            "https://www.google.com.pe/",
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://www.facebook.com/",
            "",  # Sin referer a veces
        ]
    
    def get_headers(self) -> Dict[str, str]:
        """Generar headers aleatorios pero realistas."""
        headers = self.base_headers.copy()
        
        # Rotar User-Agent
        headers["User-Agent"] = self.ua.random
        
        # Agregar referer aleatorio (80% de probabilidad)
        if random.random() < 0.8:
            headers["Referer"] = random.choice(self.referers)
        
        # Simular diferentes navegadores ocasionalmente
        if random.random() < 0.3:
            headers["Sec-CH-UA"] = self._get_random_sec_ch_ua()
        
        return headers
    
    def _get_random_sec_ch_ua(self) -> str:
        """Generar Sec-CH-UA aleatorio."""
        browsers = [
            '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            '"Microsoft Edge";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            '"Brave";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        ]
        return random.choice(browsers)
    
    def get_mobile_headers(self) -> Dict[str, str]:
        """Headers para simular dispositivo móvil."""
        headers = self.base_headers.copy()
        
        mobile_uas = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
        ]
        
        headers["User-Agent"] = random.choice(mobile_uas)
        headers["Sec-CH-UA-Mobile"] = "?1"
        
        return headers


class RateLimiter:
    """Control de velocidad de requests."""
    
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.min_delay = 60.0 / requests_per_minute
        self.last_request_time = 0
    
    def wait_if_needed(self):
        """Esperar si es necesario para respetar rate limit."""
        import time
        
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            # Agregar jitter aleatorio (±20%)
            jitter = sleep_time * random.uniform(-0.2, 0.2)
            time.sleep(sleep_time + jitter)
        
        self.last_request_time = time.time()
