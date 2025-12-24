#!/usr/bin/env python3
"""
Test script to debug SSE streaming issues.
This script will test both the Selenium ticker and SSE endpoint.
"""

import requests
import asyncio
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime

def test_selenium_ticker():
    """Test the Selenium ticker functionality directly."""
    print("=" * 50)
    print("TESTING SELENIUM TICKER DIRECTLY")
    print("=" * 50)

    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=chrome_options)
        print("✓ ChromeDriver started successfully")

        driver.get("https://th.investing.com/commodities/gold")
        print("✓ Page loaded successfully")

        # Wait for page to load
        import time
        time.sleep(3)

        # Try to find the price element
        price_element = driver.find_element(By.CSS_SELECTOR, '[data-test="instrument-price-last"]')
        price_text = price_element.text
        print(f"✓ Price element found: {price_text}")

        # Test multiple reads
        for i in range(3):
            time.sleep(2)
            price_element = driver.find_element(By.CSS_SELECTOR, '[data-test="instrument-price-last"]')
            current_price = price_element.text
            print(f"📊 Read {i+1}: {current_price} at {datetime.now()}")

        driver.quit()
        print("✓ Test completed successfully")

    except Exception as e:
        print(f"✗ Selenium test failed: {e}")
        return False

    return True

def test_sse_endpoint():
    """Test the SSE endpoint directly."""
    print("\n" + "=" * 50)
    print("TESTING SSE ENDPOINT")
    print("=" * 50)

    try:
        url = "http://localhost:8000/stream/price"
        headers = {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache'
        }

        print(f"📡 Connecting to {url}")

        response = requests.get(url, headers=headers, stream=True, timeout=10)
        print(f"✓ Response status: {response.status_code}")

        if response.status_code == 200:
            print("✓ SSE connection established")
            print("📨 Receiving data for 10 seconds...")

            # Read first few chunks
            chunk_count = 0
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if chunk:
                    chunk_count += 1
                    print(f"Chunk {chunk_count}: {chunk.strip()}")
                    if chunk_count >= 5:  # Read first 5 chunks
                        break

            response.close()
            print(f"✓ Received {chunk_count} chunks")
        else:
            print(f"✗ Failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("✗ Request timed out - server might not be running")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Connection error - server might not be running on localhost:8000")
        return False
    except Exception as e:
        print(f"✗ SSE test failed: {e}")
        return False

    return True

def test_simple_endpoint():
    """Test the simple price endpoint."""
    print("\n" + "=" * 50)
    print("TESTING SIMPLE ENDPOINT")
    print("=" * 50)

    try:
        url = "http://localhost:8000/test/price"

        print(f"📡 Connecting to {url}")

        response = requests.get(url, timeout=5)
        print(f"✓ Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✓ Simple endpoint working")
            print(f"📊 Response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"✗ Failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Simple endpoint test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting SSE Debug Tests")
    print(f"📅 Time: {datetime.now()}")

    # Test 1: Selenium directly
    selenium_ok = test_selenium_ticker()

    # Test 2: Simple endpoint
    simple_ok = test_simple_endpoint()

    # Test 3: SSE endpoint
    sse_ok = test_sse_endpoint()

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Selenium Test: {'✓ PASS' if selenium_ok else '✗ FAIL'}")
    print(f"Simple Endpoint: {'✓ PASS' if simple_ok else '✗ FAIL'}")
    print(f"SSE Endpoint: {'✓ PASS' if sse_ok else '✗ FAIL'}")

    if not selenium_ok:
        print("\n🔧 Selenium Issues:")
        print("- Check ChromeDriver installation")
        print("- Verify Chrome/ChromeDriver version match")
        print("- Check internet connection")
        print("- Website might be blocking scrapers")

    if not simple_ok:
        print("\n🔧 Server Issues:")
        print("- Make sure FastAPI server is running")
        print("- Check if server is on localhost:8000")
        print("- Check server logs for errors")

    if not sse_ok and simple_ok:
        print("\n🔧 SSE Specific Issues:")
        print("- Check FastAPI version compatibility")
        print("- Try different headers in Postman")
        print("- Check for proxy/firewall blocking")
        print("- Verify URL endpoint path")

if __name__ == "__main__":
    main()
```

## Summary of Changes and Testing

I've fixed several critical issues in your SSE implementation:

### **Main Problems Fixed:**

1. **Blocking Operations**: Your original `async gold_price()` function used blocking Selenium calls, which can prevent proper streaming.
2. **Missing Sleep**: Infinite loop without delay can overwhelm the CPU.
3. **Error Handling**: Poor error handling could cause silent failures.

### **Key Changes:**

1. **Created synchronous version**: `gold_price_sync()` that works better with StreamingResponse
2. **Added proper SSE headers**: Cache-Control, Connection, etc.
3. **Added sleep intervals**: 2-second delays between price checks
4. **Improved error handling**: Better exception handling and recovery
5. **Added test endpoint**: `/test/price` for easy debugging

### **To Test in Postman:**

1. **Method**: GET
2. **URL**: `http://localhost:8000/stream/price`
3. **Headers**:
   - `Accept`: `text/event-stream`
   - `Cache-Control`: `no-cache`

### **Debug Steps:**

1. **Run the test script**: `python backend/test_sse.py`
2. **Check the simple endpoint first**: `GET /test/price`
3. **Verify Selenium is working**: The test script will test this directly
4. **Start the server**: Make sure it's running on localhost:8000

### **Common Issues:**

- **ChromeDriver**: Ensure it's installed and matches your Chrome version
- **Website blocking**: The site might detect and block automated scraping
- **Network issues**: Firewalls or proxies can block SSE connections
- **Server not running**: Make sure your FastAPI server is started

The test script I created will help you identify exactly where the issue is occurring. Run it and let me know what the output shows!
