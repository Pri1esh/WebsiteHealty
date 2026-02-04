#!/usr/bin/env bash
# render-build.sh

# Install Chrome for Selenium
apt-get update
apt-get install -y wget gnupg2 apt-transport-https ca-certificates

# Add Google Chrome repository
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list

# Install Chrome
apt-get update
apt-get install -y google-chrome-stable

# Verify installation
google-chrome --version

# Install Python dependencies
pip install -r requirements.txt