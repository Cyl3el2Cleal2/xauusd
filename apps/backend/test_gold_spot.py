#!/usr/bin/env python3
"""
Focused test for gold spot price streaming to debug issues
"""
import asyncio
import time
from playwright.async_api import async_playwright

async def test_gold_spot_detailed():
    """Detailed test for gold spot price extraction"""
    print("🧪 Testing Gold Spot Price Extraction...")

    async with async_playwright() as p:
        print("✅ Playwright started")

        # Launch browser
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-web-security',
                '--allow-running-insecure-content',
            ]
        )
        print("✅ Browser launched")

        # Create context
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        print("✅ Context created")

        # Create page
        page = await context.new_page()
        print("✅ Page created")

        try:
            # Navigate to gold price page
            print("📍 Navigating to investing.com...")
            await page.goto("https://th.investing.com/commodities/gold",
                          wait_until="domcontentloaded",
                          timeout=45000)
            print("✅ Page loaded")

            # Wait for page to stabilize
            await page.wait_for_timeout(3000)
            print("⏱️ Waited for page stabilization")

            # Try multiple selectors for price element
            selectors = [
                '[data-test="instrument-price-last"]',
                '.instrument-price_last',
                '[data-symbol="XAU"]',
                'span[class*="price"]',
                'div[class*="price"]',
                '.text-2xl',
            ]

            price_element = None
            price_text = None

            for i, selector in enumerate(selectors):
                try:
                    print(f"🔍 Trying selector {i+1}: {selector}")
                    await page.wait_for_selector(selector, timeout=10000)
                    price_element = await page.query_selector(selector)

                    if price_element:
                        price_text = await price_element.inner_text()
                        print(f"✅ Found price with selector {i+1}: {price_text}")
                        break
                    else:
                        print(f"❌ No element found with selector {i+1}")

                except Exception as e:
                    print(f"❌ Selector {i+1} failed: {e}")
                    continue

            if not price_text:
                # Try to extract price from page text as fallback
                print("🔍 Trying to extract price from page text...")
                page_text = await page.inner_text('body')

                # Look for price patterns
                import re
                patterns = [
                    r'[\d,]+\.\d+',  # Basic price pattern
                    r'XAU/USD\s*([\d,]+\.\d+)',  # XAU/USD pattern
                    r'Gold\s*([\d,]+\.\d+)',  # Gold price pattern
                ]

                for pattern in patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        price_text = match.group(1) if match.groups() else match.group(0)
                        print(f"✅ Found price with regex: {price_text}")
                        break
                else:
                    print("❌ No price found in page text")

            if price_text:
                # Test conversion function
                def convertOunceToThaiBaht(spot):
                    try:
                        price = (float(spot)+2)*31.07*0.473
                        return round(price, 2)
                    except (ValueError, TypeError):
                        return None

                usd_price = price_text.strip().replace(',', '')
                baht_price = convertOunceToThaiBaht(usd_price)

                print(f"💰 USD Price: {usd_price}")
                print(f"💰 THB Price: {baht_price}")

                # Test if conversion works
                if baht_price:
                    print("✅ Price conversion successful")
                else:
                    print("❌ Price conversion failed")
            else:
                print("❌ Could not extract price")

        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Cleanup
            await page.close()
            await context.close()
            await browser.close()
            print("🧹 Cleanup completed")

async def test_continuous_streaming():
    """Test continuous price streaming like the real application"""
    print("\n🔄 Testing Continuous Streaming...")

    conversion_function = lambda spot: round((float(spot)+2)*31.07*0.473, 2)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto("https://th.investing.com/commodities/gold",
                          wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3000)

            last_price = None
            attempt = 0
            max_attempts = 5

            while attempt < max_attempts:
                try:
                    attempt += 1
                    print(f"\n--- Attempt {attempt} ---")

                    # Try to find price element
                    selector = '[data-test="instrument-price-last"]'
                    await page.wait_for_selector(selector, timeout=10000)
                    price_element = await page.query_selector(selector)

                    if price_element:
                        current_price_text = await price_element.inner_text()
                        current_price = conversion_function(current_price_text)

                        if current_price and current_price != last_price:
                            print(f"✅ Price updated: {current_price} THB")
                            last_price = current_price
                        else:
                            print(f"ℹ️ Price unchanged: {current_price} THB")
                    else:
                        print("❌ Price element not found")

                    # Wait before next attempt (simulating polling)
                    if attempt < max_attempts:
                        await page.wait_for_timeout(5000)  # 5 seconds

                except Exception as e:
                    print(f"❌ Attempt {attempt} failed: {e}")
                    if attempt < max_attempts:
                        await page.wait_for_timeout(10000)  # Wait longer on error

        except Exception as e:
            print(f"❌ Streaming test failed: {e}")

        finally:
            await page.close()
            await context.close()
            await browser.close()

if __name__ == "__main__":
    print("🚀 Starting Gold Spot Price Tests...")
    print("=" * 60)

    # Run detailed test
    asyncio.run(test_gold_spot_detailed())

    print("\n" + "=" * 60)

    # Run continuous test
    asyncio.run(test_continuous_streaming())

    print("\n🎉 Tests completed!")
