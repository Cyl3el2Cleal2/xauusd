import json
import asyncio
import time
from typing import AsyncGenerator, Dict, Optional, Any
import logging
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebDriverPool:
    """Manages WebDriver instances with connection pooling and caching"""

    def __init__(self):
        self.drivers: Dict[str, webdriver.Chrome] = {}
        self.element_cache: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    async def get_driver(self, client_id: str) -> webdriver.Chrome:
        """Get or create a WebDriver instance for a client"""
        async with self.lock:
            if client_id not in self.drivers:
                options = Options()
                options.add_argument("--headless")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-plugins")
                options.add_argument("--disable-images")
                options.add_argument("--disable-javascript")
                options.add_argument("--blink-settings=imagesEnabled=false")
                options.add_argument("--disable-web-security")
                options.add_argument("--allow-running-insecure-content")

                driver = webdriver.Chrome(options=options)
                driver.set_page_load_timeout(15)
                driver.set_script_timeout(10)

                self.drivers[client_id] = driver
                self.element_cache[client_id] = {}
                logger.info(f"Created new WebDriver for client: {client_id}")

            return self.drivers[client_id]

    async def cleanup_driver(self, client_id: str):
        """Clean up driver resources for a client"""
        async with self.lock:
            if client_id in self.drivers:
                try:
                    self.drivers[client_id].quit()
                    logger.info(f"Cleaned up WebDriver for client: {client_id}")
                except Exception as e:
                    logger.error(f"Error quitting driver for {client_id}: {e}")
                finally:
                    del self.drivers[client_id]

            if client_id in self.element_cache:
                del self.element_cache[client_id]

    async def safe_find_element(
        self,
        client_id: str,
        by: By,
        value: str,
        timeout: int = 5,
        cache_key: str = None
    ) -> Optional[Any]:
        """Safely find element with caching and error handling"""
        driver = await self.get_driver(client_id)

        # Check cache first
        if cache_key and cache_key in self.element_cache.get(client_id, {}):
            try:
                element = self.element_cache[client_id][cache_key]
                if element.is_displayed() and element.is_enabled():
                    return element
            except:
                # Element is stale, remove from cache
                del self.element_cache[client_id][cache_key]

        try:
            wait = WebDriverWait(driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, value)))

            # Cache the element
            if cache_key:
                if client_id not in self.element_cache:
                    self.element_cache[client_id] = {}
                self.element_cache[client_id][cache_key] = element

            return element
        except (TimeoutException, NoSuchElementException) as e:
            logger.warning(f"Element not found {by}={value} for client {client_id}: {e}")
            return None

    def get_active_count(self) -> int:
        """Get count of active drivers"""
        return len(self.drivers)

# Global driver pool
driver_pool = WebDriverPool()

def current_time_ms() -> int:
    """Get current timestamp in milliseconds"""
    return int(time.time() * 1000)

async def create_sse_data(data: dict) -> str:
    """Create properly formatted SSE data"""
    return f"data: {json.dumps(data)}\n\n"

class BasePriceStreamer:
    """Base class for price streaming with common functionality"""

    def __init__(self, symbol: str, url: str):
        self.symbol = symbol
        self.url = url
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self.base_poll_interval = 2.0

    async def initialize_page(self, client_id: str):
        """Initialize the page for scraping"""
        driver = await driver_pool.get_driver(client_id)
        driver.get(self.url)
        await asyncio.sleep(3)  # Initial page load

    def get_adaptive_poll_interval(self) -> float:
        """Get adaptive polling interval based on time"""
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:  # Market hours
            return self.base_poll_interval * 0.75  # Faster during market hours
        else:
            return self.base_poll_interval * 1.5  # Slower during off hours

    async def handle_error(self, client_id: str, error: Exception):
        """Handle errors with smart recovery"""
        self.consecutive_errors += 1
        logger.warning(f"Error in {self.symbol} stream (attempt {self.consecutive_errors}): {error}")

        if self.consecutive_errors >= self.max_consecutive_errors:
            try:
                driver = await driver_pool.get_driver(client_id)
                driver.refresh()
                await asyncio.sleep(3)

                # Clear element cache after refresh
                if client_id in driver_pool.element_cache:
                    driver_pool.element_cache[client_id].clear()

                logger.info(f"Refreshed page for {self.symbol} stream")
                self.consecutive_errors = 0
            except Exception as refresh_error:
                logger.error(f"Failed to refresh page: {refresh_error}")
                raise Exception("Failed to recover from streaming errors")

        await asyncio.sleep(2)  # Brief pause before retry

    def reset_error_count(self):
        """Reset consecutive error count"""
        self.consecutive_errors = 0

class GoldSpotStreamer(BasePriceStreamer):
    """Gold spot price streamer"""

    def __init__(self):
        super().__init__("spot", "https://th.investing.com/commodities/gold")
        self.last_price = ""

    async def stream_prices(self, client_id: str) -> AsyncGenerator[str, None]:
        """Stream gold spot prices"""
        await self.initialize_page(client_id)

        try:
            logger.info(f"Starting gold spot price stream for client {client_id}")

            while True:
                try:
                    price_element = await driver_pool.safe_find_element(
                        client_id,
                        By.CSS_SELECTOR,
                        '[data-test="instrument-price-last"]',
                        timeout=3,
                        cache_key="instrument_price_last"
                    )

                    if not price_element:
                        await self.handle_error(client_id, Exception("Price element not found"))
                        continue

                    current_price = price_element.text.strip()

                    # Only send data if price changed
                    if current_price and self.last_price != current_price:
                        self.last_price = current_price
                        self.reset_error_count()

                        data = {
                            "symbol": self.symbol,
                            "price": current_price,
                            "time": current_time_ms(),
                            "type": "price_update"
                        }

                        logger.debug(f"Gold spot price update: {current_price}")
                        yield await create_sse_data(data)

                    # Adaptive polling
                    await asyncio.sleep(self.get_adaptive_poll_interval())

                except WebDriverException as e:
                    await self.handle_error(client_id, e)

        except Exception as e:
            logger.error(f"Gold spot price stream error: {e}")
            error_data = {
                "error": str(e),
                "symbol": self.symbol,
                "time": current_time_ms(),
                "type": "error"
            }
            yield await create_sse_data(error_data)
            raise

class Gold96Streamer(BasePriceStreamer):
    """Gold 96 price streamer"""

    def __init__(self):
        super().__init__("gold96", "https://www.goldtraders.or.th/")
        self.last_buy_price = ""
        self.last_sell_price = ""

    async def stream_prices(self, client_id: str) -> AsyncGenerator[str, None]:
        """Stream gold 96 prices"""
        await self.initialize_page(client_id)

        try:
            logger.info(f"Starting gold 96 price stream for client {client_id}")

            while True:
                try:
                    # Find both elements
                    buy_element = await driver_pool.safe_find_element(
                        client_id,
                        By.ID,
                        "DetailPlace_uc_goldprices1_lblBLBuy",
                        timeout=3,
                        cache_key="gold96_buy_price"
                    )

                    sell_element = await driver_pool.safe_find_element(
                        client_id,
                        By.ID,
                        "DetailPlace_uc_goldprices1_lblBLSell",
                        timeout=3,
                        cache_key="gold96_sell_price"
                    )

                    if not buy_element or not sell_element:
                        await self.handle_error(client_id, Exception("Price elements not found"))
                        continue

                    current_buy_price = buy_element.text.strip()
                    current_sell_price = sell_element.text.strip()

                    # Only send data if prices changed
                    if (current_buy_price and current_sell_price and
                        (self.last_buy_price != current_buy_price or
                         self.last_sell_price != current_sell_price)):

                        self.last_buy_price = current_buy_price
                        self.last_sell_price = current_sell_price
                        self.reset_error_count()

                        data = {
                            "symbol": self.symbol,
                            "buy_price": current_buy_price,
                            "sell_price": current_sell_price,
                            "time": current_time_ms(),
                            "type": "price_update"
                        }

                        logger.debug(f"Gold 96 price update - Buy: {current_buy_price}, Sell: {current_sell_price}")
                        yield await create_sse_data(data)

                    # Adaptive polling
                    await asyncio.sleep(self.get_adaptive_poll_interval())

                except WebDriverException as e:
                    await self.handle_error(client_id, e)

        except Exception as e:
            logger.error(f"Gold 96 price stream error: {e}")
            error_data = {
                "error": str(e),
                "symbol": self.symbol,
                "time": current_time_ms(),
                "type": "error"
            }
            yield await create_sse_data(error_data)
            raise

# Streamer instances
gold_spot_streamer = GoldSpotStreamer()
gold_96_streamer = Gold96Streamer()

async def gold_spot_price_stream(client_id: str) -> AsyncGenerator[str, None]:
    """Stream gold spot prices"""
    async for data in gold_spot_streamer.stream_prices(client_id):
        yield data

async def gold_96_price_stream(client_id: str) -> AsyncGenerator[str, None]:
    """Stream gold 96 prices"""
    async for data in gold_96_streamer.stream_prices(client_id):
        yield data

async def stream_with_retry(stream_func, symbol: str, client_id: str, max_retries: int = 3) -> AsyncGenerator[str, None]:
    """Stream with automatic retry and error handling"""
    retry_count = 0
    base_delay = 1

    while retry_count < max_retries:
        try:
            async for data in stream_func(client_id):
                retry_count = 0  # Reset retry count on success
                yield data

        except Exception as e:
            retry_count += 1
            logger.error(f"Stream error for {symbol} (attempt {retry_count}): {e}")

            if retry_count >= max_retries:
                error_data = {
                    "error": f"Stream failed after {max_retries} attempts: {str(e)}",
                    "symbol": symbol,
                    "time": current_time_ms(),
                    "type": "fatal_error"
                }
                yield await create_sse_data(error_data)
                break

            # Exponential backoff
            delay = base_delay * (2 ** (retry_count - 1))
            await asyncio.sleep(delay)

            # Cleanup and restart
            await driver_pool.cleanup_driver(client_id)