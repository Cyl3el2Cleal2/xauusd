import json
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime

# Configure headless mode (no window pops up)
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=chrome_options)

last_gold_spot_price = 0
last_gold_96_buy_price = 0
last_gold_96_sell_price = 0

async def gold_spot_price():
    try:
        global last_gold_spot_price
        print("Starting gold spot price streaming...")
        driver.get("https://th.investing.com/commodities/gold")

        # Wait a bit for the page to load initially
        await asyncio.sleep(3)

        while True:
            try:
                # Locate the price element
                price_element = driver.find_element(By.CSS_SELECTOR, '[data-test="instrument-price-last"]')
                current_price = price_element.text

                if last_gold_spot_price != current_price:
                    last_gold_spot_price = current_price
                    timestamp = datetime.now().isoformat()
                    data = {
                        "price": last_gold_spot_price,
                        "time": timestamp
                    }
                    print(f"Real-time Gold Spot Price: {timestamp} {current_price}")

                    # Yield in proper SSE format
                    yield f"data: {json.dumps(data)}\n\n"

                # Add sleep to prevent overwhelming CPU and allow other requests
                await asyncio.sleep(2)

            except Exception as e:
                print(f"[ERROR]: Error getting price element: {e}")
                # Wait before retrying
                await asyncio.sleep(5)
                # Try to refresh the page
                driver.refresh()
                await asyncio.sleep(3)

    except Exception as e:
        print(f"[ERROR]: Gold price streaming error: {e}")
        error_data = {
            "error": str(e),
            "time": datetime.now().isoformat()
        }
        yield f"data: {json.dumps(error_data)}\n\n"
    finally:
        print("Closing webdriver...")
        driver.quit()

async def gold_96_price():
    try:
        global last_gold_96_buy_price
        global last_gold_96_sell_price
        print("Starting gold traders price streaming...")
        driver.get("https://www.goldtraders.or.th/")

        # Wait a bit for the page to load initially
        await asyncio.sleep(3)

        while True:
            try:
                # Locate the price element
                sell_price_element = driver.find_element(By.ID, "DetailPlace_uc_goldprices1_lblBLSell")
                buy_price_element = driver.find_element(By.ID, "DetailPlace_uc_goldprices1_lblBLBuy")
                current_sell_price = sell_price_element.text
                current_buy_price = buy_price_element.text

                if last_gold_96_buy_price != current_buy_price or last_gold_96_sell_price != current_sell_price:
                    timestamp = datetime.now().isoformat()
                    data = {
                        "buy_price": current_buy_price,
                        "sell_price": current_sell_price,
                        "time": timestamp
                    }
                    print(f"Real-time Gold Buy Price: {timestamp} {current_buy_price}")
                    print(f"Real-time Gold Sell Price: {timestamp} {current_sell_price}")
                    last_gold_96_buy_price = current_buy_price
                    last_gold_96_sell_price = current_sell_price

                    # Yield in proper SSE format
                    yield f"data: {json.dumps(data)}\n\n"

                # Add sleep to prevent overwhelming CPU and allow other requests
                await asyncio.sleep(2)

            except Exception as e:
                print(f"[ERROR]: Error getting gold_96 price element: {e}")
                # Wait before retrying
                await asyncio.sleep(5)
                # Try to refresh the page
                driver.refresh()
                await asyncio.sleep(3)

    except Exception as e:
        print(f"[ERROR]: gold_96 price streaming error: {e}")
        error_data = {
            "error": str(e),
            "time": datetime.now().isoformat()
        }
        yield f"data: {json.dumps(error_data)}\n\n"
    finally:
        print("Closing webdriver...")
        driver.quit()
