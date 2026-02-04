def test_adani_curl():
    """Test Adani Mangaluru Airport with curl_cffi"""
    from curl_cffi import requests
    from datetime import datetime

    url = 'https://www.adani.com/mangaluru-airport'

    print(f"Testing: {url}")
    print("Using curl_cffi with Chrome 120 impersonation")
    print("-" * 50)

    try:
        # impersonate="chrome120" mimics real browser TLS + headers exactly
        resp = requests.get(
            url,
            impersonate="chrome120",
            timeout=20,
            verify=False
        )

        print(f"Status Code: {resp.status_code}")
        print(f"Response Length: {len(resp.text)} characters")
        print(f"Content-Type: {resp.headers.get('content-type', 'N/A')}")

        if resp.status_code == 200 and len(resp.text) > 5000:
            print("\n✅ SUCCESS - Will work on Render")
            print("First 200 chars:", resp.text[:200].replace('\n', ' '))
            return True
        else:
            print(f"\n⚠️  Unexpected response (Status: {resp.status_code})")
            return False

    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        return False


# Run test
if __name__ == "__main__":
    test_adani_curl()