import asyncio
import time
from typing import Dict, Optional, Any
import logging
from datetime import datetime

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Database imports
from src.db import async_session_maker
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

# Global background task
background_task: Optional[asyncio.Task] = None

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
        async with async_session_maker() as session:
            # Extract and clean USD price
            usd_price = price_data.get('usd_price')
            baht_price = price_data.get('price')

            # Convert string prices to floats for database validation
            if isinstance(usd_price, str):
                usd_price = usd_price.replace(',', '')
                try:
                    usd_price = float(usd_price)
                except ValueError:
                    usd_price = None

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
        async with async_session_maker() as session:
            # Extract and clean prices
            buy_price = price_data.get('buy_price')
            sell_price = price_data.get('sell_price')

            # Convert strings to floats for database validation
            if isinstance(buy_price, str):
                buy_price = buy_price.replace(',', '')
            if isinstance(sell_price, str):
                sell_price = sell_price.replace(',', '')

            try:
                buy_price = float(buy_price)
                sell_price = float(sell_price)
            except ValueError:
                logger.error(f"Could not convert prices to float: Buy={buy_price}, Sell={sell_price}")
                return

            create_data = Gold96PriceCreate(
                symbol=price_data['symbol'],
                buy_price=buy_price,
                sell_price=sell_price,
                timestamp=datetime.utcnow(),
                source="goldtraders.or.th"
            )

            await PriceService.save_gold96_price(session, create_data)
            logger.debug(f"Saved gold 96 price to database: Buy={buy_price}, Sell={sell_price}")

    except Exception as e:
        logger.error(f"Failed to save gold 96 price to database: {e}")

# Lifecycle management functions for FastAPI
async def initialize_ticker():
    """Initialize the ticker system"""
    logger.info("Ticker system initialized with background scraping")

    # Start background scraping task
    global background_task
    background_task = asyncio.create_task(background_price_scraper())
    logger.info("Background price scraper started")

async def background_price_scraper():
    """Background task to periodically scrape and save gold prices"""
    logger.info("Background price scraper task started")

    # Create a dedicated browser instance for background scraping
    browser = None
    context = None
    page = None

    try:
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
            ]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )

        page = await context.new_page()
        await apply_stealth(page)

        # Set timeouts
        page.set_default_timeout(30000)
        page.set_default_navigation_timeout(45000)

        gold_spot_last_time = 0
        gold96_last_time = 0
        gold_spot_interval = 60  # 1 minute
        gold96_interval = 300    # 5 minutes

        while True:
            try:
                current_time = time.time()

                # Scrape gold spot price
                if current_time - gold_spot_last_time >= gold_spot_interval:
                    try:
                        await page.goto("https://th.investing.com/commodities/gold",
                                      wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(2000)

                        # Try to find price element
                        selector = '[data-test="instrument-price-last"]'
                        price_element = None

                        try:
                            await page.wait_for_selector(selector, timeout=10000)
                            price_element = await page.query_selector(selector)
                        except:
                            # Try alternative selectors
                            for alt_selector in ['.instrument-price_last', '[data-symbol="XAU"]', 'span[class*="price"]']:
                                try:
                                    price_element = await page.query_selector(alt_selector)
                                    if price_element:
                                        break
                                except:
                                    continue

                        if price_element:
                            current_price = await price_element.inner_text()
                            current_price = current_price.strip()
                            baht_price = convertOunceToThaiBaht(current_price)

                            if baht_price:
                                data = {
                                    "symbol": "spot",
                                    "price": baht_price,
                                    "usd_price": current_price,
                                    "timestamp": datetime.utcnow(),
                                    "source": "investing.com"
                                }
                                await save_gold_price_to_db(data)
                                logger.debug(f"Background scraper saved gold spot price: {baht_price}")
                                gold_spot_last_time = current_time

                    except Exception as e:
                        logger.error(f"Background scraper gold spot error: {e}")

                # Scrape gold 96 price
                if current_time - gold96_last_time >= gold96_interval:
                    try:
                        await page.goto("https://www.goldtraders.or.th/",
                                      wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(2000)

                        # Find buy and sell price elements
                        buy_element = None
                        sell_element = None

                        for selector in ["#DetailPlace_uc_goldprices1_lblBLBuy", '[id*="lblBLBuy"]']:
                            try:
                                buy_element = await page.query_selector(selector)
                                if buy_element:
                                    break
                            except:
                                continue

                        for selector in ["#DetailPlace_uc_goldprices1_lblBLSell", '[id*="lblBLSell"]']:
                            try:
                                sell_element = await page.query_selector(selector)
                                if sell_element:
                                    break
                            except:
                                continue

                        if buy_element and sell_element:
                            current_buy_price = await buy_element.inner_text()
                            current_sell_price = await sell_element.inner_text()

                            data = {
                                "symbol": "gold96",
                                "buy_price": current_buy_price.strip().replace(',', ''),
                                "sell_price": current_sell_price.strip().replace(',', ''),
                                "timestamp": datetime.utcnow(),
                                "source": "goldtraders.or.th"
                            }
                            await save_gold96_price_to_db(data)
                            logger.debug(f"Background scraper saved gold 96 price: Buy={current_buy_price}, Sell={current_sell_price}")
                            gold96_last_time = current_time

                    except Exception as e:
                        logger.error(f"Background scraper gold 96 error: {e}")

                # Sleep before next iteration
                await asyncio.sleep(10)

            except asyncio.CancelledError:
                logger.info("Background price scraper task cancelled")
                break
            except Exception as e:
                logger.error(f"Background scraper error: {e}")
                await asyncio.sleep(30)  # Wait before retrying

    except Exception as e:
        logger.error(f"Fatal error in background price scraper: {e}")
    finally:
        # Clean up browser resources
        try:
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
        except Exception as e:
            logger.error(f"Error cleaning up background scraper: {e}")

        logger.info("Background price scraper task ended")

async def shutdown_ticker():
    """Shutdown the ticker system"""
    logger.info("Shutting down ticker system...")

    # Stop background task if running
    if background_task and not background_task.done():
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass

    logger.info("Ticker system shutdown complete")
