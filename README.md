# Embassy Appointment Scraper

Automatically checks Indian Embassy Netherlands appointment availability every 10 minutes.

## Features
- ✅ Only sends email when GREEN appointments found
- ✅ Highlights specific available dates in BOLD CAPITALS
- ✅ Runs automatically via GitHub Actions
- ✅ FREE deployment

## Setup Instructions

1. **Fork this repository**

2. **Set up GitHub Secrets** (Repository Settings → Secrets and variables → Actions):
   - `SENDER_EMAIL`: Your Gmail address (k.piyush.88@gmail.com)
   - `SENDER_PASSWORD`: Your Gmail App Password (get from Google Account settings)

3. **Enable GitHub Actions**:
   - Go to Actions tab in your repository
   - Enable workflows if prompted

4. **Manual run (optional)**:
   - Actions → Embassy Appointment Scraper → Run workflow

## How it works
- Runs every 10 minutes automatically
- Scrapes June 2025 - January 2026
- Only sends email when GREEN appointments available
- Email highlights specific dates: **DAY 15** - AVAILABLE FOR BOOKING

## Gmail App Password Setup
1. Enable 2-factor authentication on Gmail
2. Google Account Settings → Security → App Passwords
3. Generate password for "Mail"
4. Use the 16-character password as `SENDER_PASSWORD`