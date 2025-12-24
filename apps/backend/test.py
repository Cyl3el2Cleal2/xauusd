from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime

# Configure headless mode (no window pops up)
chrome_options = Options()
chrome_options.add_argument("--headless")

driver = webdriver.Chrome(options=chrome_options)
last_price = 0

try:
    driver.get("https://th.investing.com/commodities/gold")
    while True:
        # Locate the price element
        price_element = driver.find_element(By.CSS_SELECTOR, '[data-test="instrument-price-last"]')
        if last_price != price_element.text:
          last_price = price_element.text
          print(f"Real-time Gold Price:{datetime.now()} {price_element.text}")
          
except KeyboardInterrupt:
    print("Stopped by user")
finally:
    driver.quit()