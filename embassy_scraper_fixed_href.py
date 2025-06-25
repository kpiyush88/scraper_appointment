#!/usr/bin/env python3
"""
Indian Embassy Appointment Scraper - FIXED href Detection
Scrapes appointment availability from June 2025 to Jan 2026
Fixed href="#d" detection by using correct approach from debug
"""

import asyncio
from playwright.async_api import async_playwright
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

async def scrape_embassy_appointments():
    """Main function to scrape appointment data"""
    
    # Base URL
    base_url = "https://www.indianembassynetherlands.gov.in/apt/appointment.php"
    
    # Define months to scrape (June 2025 to Jan 2026)
    months_to_scrape = [
        ("06", "2025"), ("07", "2025"), ("08", "2025"), 
        ("09", "2025"), ("10", "2025"), ("11", "2025"), 
        ("12", "2025"), ("01", "2026")
    ]
    
    results = {}
    
    async with async_playwright() as p:
        # Launch browser (headless for server deployment)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            for month, year in months_to_scrape:
                print(f"\nScraping {month}/{year}...")
                
                # Build URL for specific month/year
                url = f"{base_url}?month={month}&year={year}&apttype=Submission&locationid=2&serviceid=4#dw"
                
                # Navigate to the page
                await page.goto(url)
                
                # Wait for page to load
                await page.wait_for_timeout(3000)
                
                # Initialize counters for this month
                month_key = f"{month}/{year}"
                results[month_key] = {
                    "RED_no_service": 0,
                    "RED_CROSSED_already_booked": 0, 
                    "GREY_yet_to_open": 0,
                    "GREEN_available": 0,
                    "GREEN_dates": []  # Track specific GREEN appointment dates
                }
                
                print(f"Scanning dates for {month_key}...")
                
                # Find all list items that contain dates
                all_lis = await page.query_selector_all("li")
                
                found_dates = False
                for li in all_lis:
                    try:
                        text_content = await li.text_content()
                        if text_content and text_content.strip().isdigit():
                            text = text_content.strip()
                            if 1 <= int(text) <= 31:
                                found_dates = True
                                
                                # Get class attribute from the li element
                                li_class = await li.get_attribute("class") or ""
                                
                                # Use the same approach as debug to get href
                                href = ""
                                
                                # First check parent for href
                                parent_link = await li.query_selector("xpath=..")
                                if parent_link:
                                    try:
                                        parent_tag = await parent_link.evaluate("el => el.tagName.toLowerCase()")
                                        if parent_tag == "a":
                                            href = await parent_link.get_attribute("href") or ""
                                    except:
                                        pass
                                
                                # If no href found from parent, search all links for this date text
                                if not href:
                                    all_links = await page.query_selector_all("a")
                                    for link in all_links:
                                        try:
                                            link_text = await link.text_content()
                                            if link_text and link_text.strip() == text:
                                                href = await link.get_attribute("href") or ""
                                                break
                                        except:
                                            continue
                                
                                # Apply the CORRECTED categorization logic with proper priority order
                                if "a_disable" in li_class:
                                    # GREY (Yet to open): class="a_disable" - CHECK FIRST
                                    results[month_key]["GREY_yet_to_open"] += 1
                                    category = "GREY (Yet to open)"
                                elif "a_full" in li_class:
                                    # RED CROSSED (Already booked): class="a_full" - CHECK SECOND
                                    results[month_key]["RED_CROSSED_already_booked"] += 1
                                    category = "RED CROSSED (Already booked)"
                                elif href == "#d":
                                    # RED (No service): href="#d" - CHECK THIRD
                                    results[month_key]["RED_no_service"] += 1
                                    category = "RED (No service)"
                                else:
                                    # GREEN (Available): no special class and has appointment URL - DEFAULT
                                    results[month_key]["GREEN_available"] += 1
                                    results[month_key]["GREEN_dates"].append(int(text))  # Store the actual date
                                    category = "GREEN (Available)"
                                
                                print(f"  Date {text:2}: {category}")
                    
                    except Exception as e:
                        continue
                
                if not found_dates:
                    print(f"No date elements found for {month_key}")
                
                total_dates = sum(results[month_key].values())
                print(f"Completed {month_key}: {total_dates} dates processed")
                
                # Small delay between requests
                await page.wait_for_timeout(2000)
        
        except Exception as e:
            print(f"Error during scraping: {e}")
        
        finally:
            await browser.close()
    
    return results

def print_results(results):
    """Print formatted results"""
    print("\n" + "="*70)
    print("EMBASSY APPOINTMENT AVAILABILITY SUMMARY")
    print("="*70)
    
    # Track totals
    total_summary = {
        "RED_no_service": 0,
        "RED_CROSSED_already_booked": 0,
        "GREY_yet_to_open": 0,
        "GREEN_available": 0
    }
    
    # Print monthly results
    for month, data in results.items():
        print(f"\n{month}:")
        print(f"  RED (No service):          {data['RED_no_service']:2d} days")
        print(f"  RED CROSSED (Already booked): {data['RED_CROSSED_already_booked']:2d} days") 
        print(f"  GREY (Yet to open):        {data['GREY_yet_to_open']:2d} days")
        print(f"  GREEN (Available):         {data['GREEN_available']:2d} days")
        
        total = sum(data.values())
        print(f"  Total days:                {total:2d}")
        
        # Add to overall summary
        for key in total_summary:
            total_summary[key] += data[key]
    
    # Print overall summary
    print(f"\n" + "="*70)
    print("OVERALL SUMMARY (June 2025 - January 2026)")
    print("="*70)
    print(f"RED (No service):          {total_summary['RED_no_service']:3d} days")
    print(f"RED CROSSED (Already booked): {total_summary['RED_CROSSED_already_booked']:3d} days")
    print(f"GREY (Yet to open):        {total_summary['GREY_yet_to_open']:3d} days")
    print(f"GREEN (Available):         {total_summary['GREEN_available']:3d} days")
    print(f"TOTAL DAYS PROCESSED:      {sum(total_summary.values()):3d}")
    print("="*70)

def send_email(results):
    """Send results via email ONLY when GREEN appointments are found"""
    
    # Check if any GREEN appointments exist
    total_green = 0
    green_appointments = {}
    
    for month, data in results.items():
        if data['GREEN_available'] > 0:
            total_green += data['GREEN_available']
            green_appointments[month] = data['GREEN_dates']
    
    # Only send email if GREEN appointments found
    if total_green == 0:
        print("\n📧 No GREEN appointments found - Email NOT sent")
        return
    
    # Email configuration
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    import os
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    
    if not sender_email or not sender_password:
        print("❌ ERROR: Email credentials not found in environment variables")
        print("Please set SENDER_EMAIL and SENDER_PASSWORD as GitHub Secrets")
        return
    recipient_email = "k.piyush.88@gmail.com"
    
    # Create email content
    subject = f"🟢 GREEN APPOINTMENTS FOUND! - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    # Format results for email - Focus on GREEN appointments
    email_body = "🟢🟢🟢 GREEN APPOINTMENTS FOUND! 🟢🟢🟢\n"
    email_body += "="*70 + "\n\n"
    
    email_body += f"TOTAL GREEN APPOINTMENTS: {total_green}\n\n"
    
    # Highlight GREEN appointments in BOLD CAPITALS
    email_body += "AVAILABLE APPOINTMENT DATES:\n"
    email_body += "="*30 + "\n"
    
    for month, dates in green_appointments.items():
        email_body += f"\n**{month.upper()}**:\n"
        sorted_dates = sorted(dates)
        for date in sorted_dates:
            email_body += f"  📅 **DAY {date}** - AVAILABLE FOR BOOKING\n"
    
    email_body += "\n" + "="*70 + "\n"
    email_body += "FULL MONTHLY BREAKDOWN:\n"
    email_body += "="*70 + "\n\n"
    
    # Track totals for full summary
    total_summary = {
        "RED_no_service": 0,
        "RED_CROSSED_already_booked": 0,
        "GREY_yet_to_open": 0,
        "GREEN_available": 0
    }
    
    # Add monthly results
    for month, data in results.items():
        email_body += f"{month}:\n"
        email_body += f"  RED (No service):             {data['RED_no_service']:2d} days\n"
        email_body += f"  RED CROSSED (Already booked): {data['RED_CROSSED_already_booked']:2d} days\n"
        email_body += f"  GREY (Yet to open):           {data['GREY_yet_to_open']:2d} days\n"
        
        # Highlight GREEN counts in caps
        if data['GREEN_available'] > 0:
            email_body += f"  **GREEN (AVAILABLE):          {data['GREEN_available']:2d} DAYS** ⭐\n"
        else:
            email_body += f"  GREEN (Available):            {data['GREEN_available']:2d} days\n"
        
        total = sum([data['RED_no_service'], data['RED_CROSSED_already_booked'], 
                    data['GREY_yet_to_open'], data['GREEN_available']])
        email_body += f"  Total days:                   {total:2d}\n\n"
        
        # Add to overall summary
        for key in total_summary:
            if key in data:
                total_summary[key] += data[key]
    
    # Add overall summary
    email_body += "="*70 + "\n"
    email_body += "OVERALL SUMMARY (June 2025 - January 2026)\n"
    email_body += "="*70 + "\n"
    email_body += f"RED (No service):             {total_summary['RED_no_service']:3d} days\n"
    email_body += f"RED CROSSED (Already booked): {total_summary['RED_CROSSED_already_booked']:3d} days\n"
    email_body += f"GREY (Yet to open):           {total_summary['GREY_yet_to_open']:3d} days\n"
    email_body += f"GREEN (Available):            {total_summary['GREEN_available']:3d} days\n"
    email_body += f"TOTAL DAYS PROCESSED:         {sum(total_summary.values()):3d}\n"
    email_body += "="*70 + "\n\n"
    
    # Final emphasis on GREEN appointments
    email_body += f"\n🎯 ACTION REQUIRED: {total_green} GREEN APPOINTMENT SLOTS AVAILABLE!\n"
    email_body += "🚨 BOOK IMMEDIATELY - THESE SLOTS MAY BE TAKEN QUICKLY!\n\n"
    
    email_body += "Visit: https://www.indianembassynetherlands.gov.in/apt/appointment.php\n"
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(email_body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        print(f"\n✅ 🟢 GREEN APPOINTMENT ALERT EMAIL sent to {recipient_email}")
        print(f"📧 {total_green} available appointment slots reported!")
        
    except Exception as e:
        print(f"\n❌ Failed to send GREEN appointment alert email: {e}")
        print("Please check your email configuration and credentials.")

async def main():
    """Main execution function"""
    print("Indian Embassy Appointment Scraper - FIXED href Detection")
    print("="*60)
    print("Target: June 2025 - January 2026")
    print("FIXED Logic:")
    print("  RED (No service):          href='#d' (PROPERLY DETECTED)")
    print("  RED CROSSED (Already booked): class='a_full'")
    print("  GREY (Yet to open):        class='a_disable'")
    print("  GREEN (Available):         no special class + appointment URL")
    print("="*60)
    
    # Run the scraper
    results = await scrape_embassy_appointments()
    
    # Print results
    print_results(results)
    
    # Send email with results
    send_email(results)
    
    # Save results to JSON file
    output_file = "embassy_results_fixed_href.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
