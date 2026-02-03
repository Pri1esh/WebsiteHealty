from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
import time


def test_selenium_stealth(url):
    """Use Selenium with stealth mode to bypass detection"""
    try:
        options = Options()

        # Stealth options
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')

        # Hide automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)

        print("Starting Chrome with Stealth...")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # Apply stealth
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )

        print(f"Navigating to {url}...")
        start_time = time.time()
        driver.get(url)
        load_time = time.time() - start_time

        print(f"\n{'=' * 50}")
        print(f"✅ SUCCESS!")
        print(f"Page Title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        print(f"Load Time: {load_time:.2f}s")
        print(f"{'=' * 50}")

        driver.quit()
        return True

    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


# Test
test_selenium_stealth("https://csmia-mumbai.adaniairports.com/")