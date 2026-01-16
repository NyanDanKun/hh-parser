"""Run HH.ru Parser Web Interface."""

import webbrowser
import time
from threading import Timer
from app import app

def open_browser():
    """Open browser after a short delay."""
    time.sleep(1.5)
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    # Open browser automatically
    Timer(1, open_browser).start()
    
    # Start Flask app
    print("=" * 60)
    print("🚀 HH.ru Parser - Web Interface")
    print("=" * 60)
    print("\n📊 Dashboard will open in your browser...")
    print("🌐 URL: http://localhost:5000")
    print("\n⌨️  Press Ctrl+C to stop the server")
    print("=" * 60)
    print()
    
    app.run(debug=False, host='0.0.0.0', port=5000)
