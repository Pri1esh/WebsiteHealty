import threading
import time
import requests
import pandas as pd
import os
from flask import Flask, render_template, jsonify, request
from datetime import datetime
import urllib3

urllib3.disable_warnings()
app = Flask(__name__)

CHECK_INTERVAL = 15 * 60  # 15 minutes

monitoring_results = {
    'total': 0,
    'checked': 0,
    'failed': [],
    'last_check': None,
    'is_running': False,
    'retry_in_progress': False
}

results_lock = threading.Lock()


def load_websites_from_excel():
    """Load websites from Excel"""
    try:
        possible_paths = [
            os.path.join(os.path.dirname(__file__), 'Adani-BUWise-Websites.xlsx'),
            'Adani-BUWise-Websites.xlsx',
            'upload/Adani-BUWise-Websites.xlsx',
            '/mnt/kimi/upload/Adani-BUWise-Websites.xlsx'
        ]

        path = None
        for p in possible_paths:
            if os.path.exists(p):
                path = p
                print(f"✓ Found Excel at: {p}")
                break

        if not path:
            print("✗ Excel not found, using demo data")
            return get_demo_websites()

        df = pd.read_excel(path)
        websites = []

        for _, row in df.iterrows():
            bu = str(row.get('BU', '')).strip()
            cell = str(row.get('Websites', '')).strip()

            if not cell or cell.lower() in ['nan', 'none']:
                continue

            cell = cell.replace('\r\n', '\n').replace('\r', '\n')
            raw_urls = []

            for part in cell.split('\n'):
                raw_urls.extend([u.strip() for u in part.split(',') if u.strip()])

            for url in raw_urls:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                url = url.replace(' ', '').rstrip('/')

                websites.append({
                    'bu': bu,
                    'url': url,
                    'name': url.replace('https://', '').replace('http://', '').replace('www.', '')
                })

        print(f"✓ Loaded {len(websites)} websites")
        return websites

    except Exception as e:
        print(f"✗ Error loading Excel: {e}")
        import traceback
        traceback.print_exc()
        return get_demo_websites()


def check_website(site_info):
    """Check website using requests only"""
    url = site_info['url']

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        success = 200 <= response.status_code < 400

        return {
            'success': success,
            'status_code': response.status_code,
            'url': url,
            'bu': site_info['bu'],
            'name': site_info['name'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'error': None if success else f'HTTP {response.status_code}'
        }

    except Exception as e:
        return {
            'success': False,
            'status_code': 0,
            'url': url,
            'bu': site_info['bu'],
            'name': site_info['name'],
            'error': str(e)[:50],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


def get_demo_websites():
    return [
        {'bu': 'Demo', 'url': 'https://www.google.com', 'name': 'google.com'},
        {'bu': 'Demo', 'url': 'https://www.github.com', 'name': 'github.com'}
    ]


def monitor_websites():
    """Main monitoring loop"""
    global monitoring_results
    monitoring_results['is_running'] = True

    while monitoring_results['is_running']:
        websites = load_websites_from_excel()

        with results_lock:
            monitoring_results['total'] = len(websites)
            monitoring_results['checked'] = 0
            monitoring_results['failed'] = []

        print(f"\n{'=' * 60}")
        print(f"🔍 CYCLE STARTED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Checking {len(websites)} websites...")
        print(f"{'=' * 60}")

        for i, site in enumerate(websites, start=1):
            if not monitoring_results['is_running']:
                break

            print(f"[{i}/{len(websites)}] Checking {site['name'][:40]}...", end=' ')

            result = check_website(site)

            with results_lock:
                monitoring_results['checked'] = i
                if not result['success']:
                    result['retry_count'] = 0
                    monitoring_results['failed'].append(result)
                    print(f"❌ FAILED ({result['error'] or result['status_code']})")
                else:
                    monitoring_results['failed'] = [f for f in monitoring_results['failed'] if
                                                    f['url'] != result['url']]
                    print(f"✅ OK ({result['status_code']})")

            time.sleep(0.5)

        with results_lock:
            monitoring_results['last_check'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        print(f"\n✅ CYCLE COMPLETE")
        print(f"   Failed: {len(monitoring_results['failed'])} sites")
        print(f"   Next check in 15 minutes...")
        print(f"{'=' * 60}\n")

        # Sleep for 15 minutes (check every second if should stop)
        for _ in range(CHECK_INTERVAL):
            if not monitoring_results['is_running']:
                break
            time.sleep(1)

    print("🛑 Monitoring stopped")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/start', methods=['POST'])
def start_monitoring():
    if not monitoring_results['is_running']:
        t = threading.Thread(target=monitor_websites, daemon=True)
        t.start()
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already_running'})


@app.route('/api/stop', methods=['POST'])
def stop_monitoring():
    monitoring_results['is_running'] = False
    return jsonify({'status': 'stopped'})


@app.route('/api/status')
def status():
    with results_lock:
        return jsonify({
            'total': monitoring_results['total'],
            'checked': monitoring_results['checked'],
            'failed': [f.copy() for f in monitoring_results['failed']],
            'last_check': monitoring_results['last_check'],
            'is_running': monitoring_results['is_running']
        })


@app.route('/api/retry', methods=['POST'])
def retry_website():
    global monitoring_results

    data = request.get_json()
    if not data or not data.get('url'):
        return jsonify({'success': False, 'error': 'No URL'}), 400

    url = data['url']

    with results_lock:
        site_index = None
        site_info = None

        for i, site in enumerate(monitoring_results['failed']):
            if site['url'] == url:
                site_index = i
                site_info = site
                break

        if site_index is None:
            return jsonify({'success': False, 'error': 'Site not in failed list'}), 404

        retry_count = site_info.get('retry_count', 0)
        if retry_count >= 3:
            return jsonify({'success': False, 'error': 'Max retries reached', 'retry_count': retry_count}), 429

    result = check_website(site_info)

    with results_lock:
        if result['success']:
            monitoring_results['failed'].pop(site_index)
            return jsonify({
                'success': True,
                'message': 'Website is now accessible',
                'failed_count': len(monitoring_results['failed'])
            })
        else:
            site_info['retry_count'] = retry_count + 1
            site_info['last_retry'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return jsonify({
                'success': False,
                'error': result.get('error', 'Check failed'),
                'retry_count': site_info['retry_count']
            })


# For PythonAnywhere WSGI
application = app

if __name__ == '__main__':
    print("=" * 60)
    print("Adani Website Health Monitor")
    print("=" * 60)
    print("Open browser: http://localhost:5000")
    print("Press CTRL+C to stop")
    print("=" * 60 + "\n")

    # Start monitoring automatically
    if not monitoring_results['is_running']:
        t = threading.Thread(target=monitor_websites, daemon=True)
        t.start()
        print("🚀 Auto-started monitoring\n")

    # Keep main thread alive with Flask server
    # This prevents "Process finished with exit code 0"
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,  # Set to True for debug mode
            threaded=True,  # Enable threading
            use_reloader=False  # Prevent double startup
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        monitoring_results['is_running'] = False
        time.sleep(1)
        print("Goodbye!")