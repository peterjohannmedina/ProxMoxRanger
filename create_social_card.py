#!/usr/bin/env python3
"""
Generate a professional social media card for ProxMox Ranger
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Configuration
WIDTH = 1280
HEIGHT = 640
OUTPUT_FILE = "assets/ProxMoxRanger-Social.png"

# Colors - Dark theme matching the UI
BACKGROUND = "#1a1d24"  # Dark background
PRIMARY = "#6366f1"     # Purple/blue accent
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#9ca3af"
ACCENT = "#4f46e5"      # Darker purple

def create_social_card():
    # Create base image
    img = Image.new('RGB', (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(img)

    # Try to load and add logo
    try:
        logo = Image.open("assets/RangerMark.png")
        # Resize logo to fit nicely
        logo_width = 180
        logo_height = int(logo.height * (logo_width / logo.width))
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

        # Position logo on left side
        logo_x = 80
        logo_y = (HEIGHT - logo_height) // 2

        # Paste logo with alpha channel
        if logo.mode == 'RGBA':
            img.paste(logo, (logo_x, logo_y), logo)
        else:
            img.paste(logo, (logo_x, logo_y))
    except Exception as e:
        print(f"Could not load logo: {e}")
        logo_width = 0

    # Text positioning (right of logo)
    text_x = logo_x + logo_width + 60
    text_area_width = WIDTH - text_x - 80

    # Try to use a nice font, fallback to default
    try:
        title_font = ImageFont.truetype("segoeui.ttf", 72)
        subtitle_font = ImageFont.truetype("segoeui.ttf", 32)
        info_font = ImageFont.truetype("segoeui.ttf", 24)
    except:
        try:
            title_font = ImageFont.truetype("arial.ttf", 72)
            subtitle_font = ImageFont.truetype("arial.ttf", 32)
            info_font = ImageFont.truetype("arial.ttf", 24)
        except:
            # Fallback to default
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            info_font = ImageFont.load_default()

    # Draw title
    title = "ProxMox Ranger"
    title_y = 150
    draw.text((text_x, title_y), title, fill=TEXT_PRIMARY, font=title_font)

    # Draw subtitle
    subtitle = "Modern Hot-Swap Storage Manager"
    subtitle_y = title_y + 90
    draw.text((text_x, subtitle_y), subtitle, fill=TEXT_SECONDARY, font=subtitle_font)

    # Draw description
    description = "Secure web-based interface for Proxmox VE"
    desc_y = subtitle_y + 60
    draw.text((text_x, desc_y), description, fill=TEXT_SECONDARY, font=info_font)

    # Draw key features as badges/pills
    features = [
        "🔄 Hot-Swap Management",
        "🌐 SMB/CIFS Shares",
        "🔐 Secure Auth"
    ]

    badge_y = desc_y + 80
    badge_x = text_x
    badge_spacing = 15
    badge_padding_x = 20
    badge_padding_y = 10
    badge_height = 45

    for feature in features:
        # Calculate badge dimensions
        bbox = draw.textbbox((0, 0), feature, font=info_font)
        text_width = bbox[2] - bbox[0]
        badge_width = text_width + (badge_padding_x * 2)

        # Draw rounded rectangle background
        draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + badge_width, badge_y + badge_height],
            radius=8,
            fill=ACCENT,
            outline=PRIMARY,
            width=2
        )

        # Draw text centered in badge
        text_y = badge_y + badge_padding_y
        draw.text((badge_x + badge_padding_x, text_y), feature, fill=TEXT_PRIMARY, font=info_font)

        # Move to next badge position
        badge_x += badge_width + badge_spacing

        # Wrap to next line if needed
        if badge_x + 200 > WIDTH - 80:
            badge_x = text_x
            badge_y += badge_height + badge_spacing

    # Draw footer info
    footer_y = HEIGHT - 60
    footer_text = "github.com/peterjohannmedina/ProxMoxRanger"
    draw.text((text_x, footer_y), footer_text, fill=PRIMARY, font=info_font)

    # Add decorative accent line
    line_y = title_y - 30
    draw.line([(text_x, line_y), (text_x + 300, line_y)], fill=PRIMARY, width=4)

    # Add GitHub logo in upper right corner
    try:
        github_logo = Image.open("assets/github-mark-white.png")
        # Resize GitHub logo
        github_size = 80
        github_logo = github_logo.resize((github_size, github_size), Image.Resampling.LANCZOS)

        # Position in upper right corner with padding
        github_x = WIDTH - github_size - 60
        github_y = 60

        # Paste GitHub logo with alpha channel
        if github_logo.mode == 'RGBA':
            img.paste(github_logo, (github_x, github_y), github_logo)
        else:
            img.paste(github_logo, (github_x, github_y))
    except Exception as e:
        print(f"Could not load GitHub logo: {e}")

    # Save the image
    img.save(OUTPUT_FILE, quality=95)
    print(f"Social media card created: {OUTPUT_FILE}")
    print(f"Dimensions: {WIDTH}x{HEIGHT}px")
    print(f"Perfect for GitHub social preview and sharing!")

if __name__ == "__main__":
    create_social_card()
