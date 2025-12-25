#!/usr/bin/env python3
"""
Simple test for Playwright functionality
"""
import asyncio
import time
from playwright.async_api import async_playwright

async def test_playwright():
    """Test basic Playwright functionality"""
    print("🧪 Testing Playwright...")

    try:
        # Start Playwright
        async with async_playwright() as p:
            print("✅ Playwright started successfully")

            # Launch browser
            browser = await p.chromium.launch(headless=True)
            print("✅ Browser launched successfully")

            # Create context
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            print("✅ Context created successfully")

            # Create page
            page = await context.new_page()
            print("✅ Page created successfully")

            # Navigate to test page
            await page.goto("https://th.investing.com/commodities/gold", timeout=45000)
            print("✅ Page loaded successfully")

            # Wait for page to stabilize
            await page.wait_for_timeout(3000)

            # Try to find price element
            selector = '[data-test="instrument-price-last"]'
            try:
                await page.wait_for_selector(selector, timeout=15000)
                price_element = await page.query_selector(selector)

                if price_element:
                    price_text = await price_element.inner_text()
                    print(f"✅ Found gold price: {price_text}")
                else:
                    print("❌ Price element not found")

            except Exception as e:
                print(f"❌ Error finding price element: {e}")

            # Test goldtraders site
            await page.goto("https://www.goldtraders.or.th/", timeout=45000)
            print("✅ Goldtraders page loaded successfully")

            await page.wait_for_timeout(3000)

            # Try to find buy/sell elements
            buy_selectors = [
                "#DetailPlace_uc_goldprices1_lblBLBuy",
                '[id*="lblBLBuy"]'
            ]

            sell_selectors = [
                "#DetailPlace_uc_goldprices1_lblBLSell",
                '[id*="lblBLSell"]'
            ]

            buy_element = None
            for selector in buy_selectors:
                try:
                    buy_element = await page.query_selector(selector)
                    if buy_element:
                        break
                except:
                    continue

            sell_element = None
            for selector in sell_selectors:
                try:
                    sell_element = await page.query_selector(selector)
                    if sell_element:
                        break
                except:
                    continue

            if buy_element and sell_element:
                buy_text = await buy_element.inner_text()
                sell_text = await sell_element.inner_text()
                print(f"✅ Found gold 96 prices - Buy: {buy_text}, Sell: {sell_text}")
            else:
                print("❌ Gold 96 price elements not found")

            # Clean up
            await page.close()
            await context.close()
            await browser.close()
            print("✅ All resources cleaned up successfully")

    except Exception as e:
        print(f"❌ Playwright test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_playwright())
