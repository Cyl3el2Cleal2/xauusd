import json
import asyncio
import time
from typing import AsyncGenerator, Dict, Optional, Any
import logging
from datetime import datetime

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Database imports
from src.db import get_async_session
from src.schemas import GoldPriceCreate, Gold96PriceCreate
from src.services.price_service import PriceService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple stealth implementation to avoid dependency issues
async def apply_stealth(page: Page):
    """Apply basic stealth techniques to avoid detection"""
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        window.chrome = {
            runtime: {},
        };
    """)

class PlaywrightPool:
    """Manages Playwright browser instances with connection pooling"""

    def __init__(self):
        self.browsers: Dict[str, Browser] = {}
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}
        self.lock = asyncio.Lock()
        self.max_browsers = 3  # Limit to 3 browser instances

    async def get_page(self, client_id: str) -> Page:
        """Get or create a Playwright page for a client"""
        async with self.lock:
            if client_id not in self.browsers:
                # Create new browser
                playwright = await async_playwright().start()

                browser = await playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-extensions',
                        '--disable-plugins',
                        '--disable-images',
                        '--disable-web-security',
                        '--allow-running-insecure-content',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                    ]
                )

                self.browsers[client_id] = browser

                # Create context with stealth
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True
                )
                self.contexts[client_id] = context

                # Create page
                page = await context.new_page()
                await apply_stealth(page)  # Apply stealth to avoid detection
                self.pages[client_id] = page

                # Set timeouts
                page.set_default_timeout(30000)  # 30 seconds
                page.set_default_navigation_timeout(45000)  # 45 seconds

                logger.info(f"Created new Playwright page for client: {client_id}")

            return self.pages[client_id]

    async def cleanup_page(self, client_id: str):
        """Clean up page resources for a client"""
        async with self.lock:
            try:
                if client_id in self.pages:
                    await self.pages[client_id].close()

                if client_id in self.contexts:
                    await self.contexts[client_id].close()

                if client_id in self.browsers:
                    await self.browsers[client_id].close()

                # Remove from all dictionaries
                self.pages.pop(client_id, None)
                self.contexts.pop(client_id, None)
                self.browsers.pop(client_id, None)

                logger.info(f"Cleaned up Playwright resources for client: {client_id}")

            except Exception as e:
                logger.error(f"Error cleaning up Playwright for {client_id}: {e}")

    def get_active_count(self) -> int:
        """Get count of active pages"""
        return len(self.pages)

# Global page pool
page_pool = PlaywrightPool()

def current_time_ms() -> int:
    """Get current timestamp in milliseconds"""
    return int(time.time() * 1000)

def convertOunceToThaiBaht(spot):
    """Convert gold spot price from USD/ounce to Thai Baht"""
    try:
        # Handle comma as thousands separator
        if isinstance(spot, str):
            spot = spot.replace(',', '')

        # Fix 1usd = 31.07baht, gold is 0.473 ounces per baht weight
        price = (float(spot)+2)*31.07*0.473
        return round(price, 2)
    except (ValueError, TypeError):
        return None

async def save_gold_price_to_db(price_data: dict):
    """Save gold price data to database"""
    try:
        from src.db import async_session_maker
        async with async_session_maker() as session:
            # Extract USD price before conversion if available
            usd_price = price_data.get('usd_price')
            baht_price = price_data.get('price')

            create_data = GoldPriceCreate(
                symbol=price_data['symbol'],
                price=baht_price,
                usd_price=usd_price,
                timestamp=datetime.utcnow(),
                source="investing.com"
            )

            await PriceService.save_gold_price(session, create_data)
            logger.debug(f"Saved gold price to database: {baht_price}")

    except Exception as e:
        logger.error(f"Failed to save gold price to database: {e}")

async def save_gold96_price_to_db(price_data: dict):
    """Save gold 96 price data to database"""
    try:
        from src.db import async_session_maker
        async with async_session_maker() as session:
            create_data = Gold96PriceCreate(
                symbol=price_data['symbol'],
                buy_price=float(price_data['buy_price'].replace(',', '')),
                sell_price=float(price_data['sell_price'].replace(',', '')),
                timestamp=datetime.utcnow(),
                source="goldtraders.or.th"
            )

            await PriceService.save_gold96_price(session, create_data)
            logger.debug(f"Saved gold 96 price to database: Buy={price_data['buy_price']}, Sell={price_data['sell_price']}")

    except Exception as e:
        logger.error(f"Failed to save gold 96 price to database: {e}")

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
        self.base_poll_interval = 10.0  # Longer intervals for Playwright
        self.last_error_time = 0

    async def initialize_page(self, client_id: str):
        """Initialize the page for scraping"""
        page = await page_pool.get_page(client_id)

        try:
            # Navigate to URL with anti-detection measures
            await page.goto(self.url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3000)  # Wait for page to fully load

            # Random mouse movement to appear more human-like
            await page.mouse.move(100, 100)
            await page.wait_for_timeout(500)
            await page.mouse.move(200, 200)
            await page.wait_for_timeout(500)

        except Exception as e:
            logger.warning(f"Error during page initialization for {self.symbol}: {e}")
            raise

    def get_adaptive_poll_interval(self) -> float:
        """Get adaptive polling interval based on time and error rate"""
        current_hour = datetime.now().hour

        # Increase polling time if we had recent errors
        if time.time() - self.last_error_time < 300:  # 5 minutes
            return self.base_poll_interval * 2
        elif 9 <= current_hour <= 17:  # Market hours
            return self.base_poll_interval  # 10 seconds during market hours
        else:
            return self.base_poll_interval * 1.5  # 15 seconds during off hours

    async def handle_error(self, client_id: str, error: Exception):
        """Handle errors with smart recovery"""
        self.consecutive_errors += 1
        self.last_error_time = time.time()
        logger.warning(f"Error in {self.symbol} stream (attempt {self.consecutive_errors}): {error}")

        if self.consecutive_errors >= self.max_consecutive_errors:
            try:
                page = await page_pool.get_page(client_id)

                # Try to refresh the page
                await page.reload(wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(3000)

                logger.info(f"Refreshed page for {self.symbol} stream")
                self.consecutive_errors = 0

            except Exception as refresh_error:
                logger.error(f"Failed to refresh page: {refresh_error}")
                # Try to recreate the page
                await page_pool.cleanup_page(client_id)
                await self.initialize_page(client_id)
                self.consecutive_errors = 0
        else:
            # Exponential backoff
            backoff_time = min(60, 5 * (2 ** (self.consecutive_errors - 1)))
            await asyncio.sleep(backoff_time)

    def reset_error_count(self):
        """Reset consecutive error count"""
        self.consecutive_errors = 0
        self.last_error_time = 0

class GoldSpotStreamer(BasePriceStreamer):
    """Gold spot price streamer using Playwright"""

    def __init__(self):
        super().__init__("spot", "https://th.investing.com/commodities/gold")
        self.last_price = 0

    async def stream_prices(self, client_id: str) -> AsyncGenerator[str, None]:
        """Stream gold spot prices using Playwright"""
        await self.initialize_page(client_id)

        try:
            logger.info(f"Starting gold spot price stream for client {client_id}")

            while True:
                try:
                    page = await page_pool.get_page(client_id)

                    # Wait for price element with timeout
                    selector = '[data-test="instrument-price-last"]'

                    try:
                        await page.wait_for_selector(selector, timeout=15000)
                        price_element = await page.query_selector(selector)
                    except:
                        # Try alternative selectors
                        alternative_selectors = [
                            '.instrument-price_last',
                            '[data-symbol="XAU"]',
                            'span[class*="price"]',
                            'div[class*="price"]',
                        ]

                        for alt_selector in alternative_selectors:
                            try:
                                price_element = await page.query_selector(alt_selector)
                                if price_element:
                                    break
                            except:
                                price_element = None
                                continue
                        else:
                            raise Exception("Price element not found with any selector")

                    if not price_element:
                        await self.handle_error(client_id, Exception("Price element not found"))
                        continue

                    # Get price text
                    current_price = await price_element.inner_text()
                    current_price = current_price.strip()

                    usd_price = current_price
                    baht_price = convertOunceToThaiBaht(current_price)

                    # Only send data if price changed
                    if baht_price and self.last_price != baht_price:
                        self.last_price = baht_price
                        self.reset_error_count()

                        data = {
                            "symbol": self.symbol,
                            "price": baht_price,
                            "usd_price": usd_price,
                            "time": current_time_ms(),
                            "type": "price_update"
                        }

                        logger.debug(f"Gold spot price update: {baht_price}")
                        yield await create_sse_data(data)

                        # Save to database asynchronously
                        asyncio.create_task(save_gold_price_to_db(data))

                    # Adaptive polling
                    poll_interval = self.get_adaptive_poll_interval()
                    await asyncio.sleep(poll_interval)

                except Exception as e:
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
    """Gold 96 price streamer using Playwright"""

    def __init__(self):
        super().__init__("gold96", "https://www.goldtraders.or.th/")
        self.last_buy_price = ""
        self.last_sell_price = ""

    async def stream_prices(self, client_id: str) -> AsyncGenerator[str, None]:
        """Stream gold 96 prices using Playwright"""
        await self.initialize_page(client_id)

        try:
            logger.info(f"Starting gold 96 price stream for client {client_id}")

            while True:
                try:
                    page = await page_pool.get_page(client_id)

                    # Wait for page to be ready
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(2000)

                    # Find buy price element
                    buy_element = None
                    buy_selectors = [
                        "#DetailPlace_uc_goldprices1_lblBLBuy",
                        '[id*="lblBLBuy"]',
                        'span:has-text("รับซื้อ")',
                        'div:has-text("รับซื้อ")',
                    ]

                    for selector in buy_selectors:
                        try:
                            buy_element = await page.query_selector(selector)
                            if buy_element:
                                break
                        except:
                            continue

                    # Find sell price element
                    sell_element = None
                    sell_selectors = [
                        "#DetailPlace_uc_goldprices1_lblBLSell",
                        '[id*="lblBLSell"]',
                        'span:has-text("ขาย")',
                        'div:has-text("ขาย")',
                    ]

                    for selector in sell_selectors:
                        try:
                            sell_element = await page.query_selector(selector)
                            if sell_element:
                                break
                        except:
                            continue

                    if not buy_element or not sell_element:
                        await self.handle_error(client_id, Exception("Price elements not found"))
                        continue

                    current_buy_price = await buy_element.inner_text()
                    current_sell_price = await sell_element.inner_text()

                    current_buy_price = current_buy_price.strip()
                    current_sell_price = current_sell_price.strip()

                    # Clean up comma separators for float conversion
                    current_buy_price = current_buy_price.replace(',', '')
                    current_sell_price = current_sell_price.replace(',', '')

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

                        # Save to database asynchronously
                        asyncio.create_task(save_gold96_price_to_db(data))

                    # Adaptive polling
                    poll_interval = self.get_adaptive_poll_interval()
                    await asyncio.sleep(poll_interval)

                except Exception as e:
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
    base_delay = 10  # Longer base delay for Playwright

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

            # Exponential backoff with longer delays
            delay = base_delay * (2 ** (retry_count - 1))
            await asyncio.sleep(delay)

            # Cleanup and restart
            await page_pool.cleanup_page(client_id)

# Lifecycle management functions for FastAPI
async def initialize_ticker():
    """Initialize the ticker system"""
    logger.info("Ticker system initialized with Playwright")
    # No specific initialization needed for Playwright

async def shutdown_ticker():
    """Shutdown the ticker system"""
    logger.info("Shutting down ticker system...")

    # Clean up all Playwright resources
    for client_id in list(page_pool.pages.keys()):
        await page_pool.cleanup_page(client_id)

    logger.info("Ticker system shutdown complete")
