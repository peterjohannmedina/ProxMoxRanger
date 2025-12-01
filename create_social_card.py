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
OUTPUT_FILE_V2 = "assets/ProxMoxRanger-Social-v2.png"
OUTPUT_FILE_V3 = "assets/ProxMoxRanger-Social-v3.png"

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

def create_social_card_v2():
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

    # Add GitHub logo with lettering in upper right corner with black transparent background
    try:
        github_logo = Image.open("assets/github-logo-white.png")

        # Resize GitHub logo to fit nicely
        github_width = 200
        github_height = int(github_logo.height * (github_width / github_logo.width))
        github_logo = github_logo.resize((github_width, github_height), Image.Resampling.LANCZOS)

        # Create a semi-transparent black background for the logo
        logo_bg_padding = 20
        logo_bg_x = WIDTH - github_width - 40 - logo_bg_padding
        logo_bg_y = 40 - logo_bg_padding
        logo_bg_width = github_width + (logo_bg_padding * 2)
        logo_bg_height = github_height + (logo_bg_padding * 2)

        # Draw rounded rectangle with black transparent background
        # Create a new RGBA layer for the transparent background
        overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        overlay_draw.rounded_rectangle(
            [logo_bg_x, logo_bg_y, logo_bg_x + logo_bg_width, logo_bg_y + logo_bg_height],
            radius=12,
            fill=(0, 0, 0, 180)  # Black with transparency
        )

        # Composite the overlay onto the main image
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)

        # Position GitHub logo in upper right corner
        github_x = WIDTH - github_width - 40 - logo_bg_padding + logo_bg_padding
        github_y = 40

        # Paste GitHub logo with alpha channel
        if github_logo.mode == 'RGBA':
            img.paste(github_logo, (github_x, github_y), github_logo)
        else:
            # Convert to RGBA for transparency
            img_rgba = img.convert('RGBA')
            img_rgba.paste(github_logo, (github_x, github_y))
            img = img_rgba.convert('RGB')
    except Exception as e:
        print(f"Could not load GitHub logo: {e}")

    # Save the image
    img.save(OUTPUT_FILE_V2, quality=95)
    print(f"Social media card v2 created: {OUTPUT_FILE_V2}")
    print(f"Dimensions: {WIDTH}x{HEIGHT}px")
    print(f"Perfect for GitHub social preview and sharing!")

def create_social_card_v3():
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

    # Add GitHub mark and lettering in upper right corner with black transparent background
    try:
        github_mark = Image.open("assets/github-mark-white.png")
        github_lettering = Image.open("assets/github-logo-white.png")

        # Resize GitHub mark to match lettering height
        mark_height = 60
        mark_width = int(github_mark.width * (mark_height / github_mark.height))
        github_mark = github_mark.resize((mark_width, mark_height), Image.Resampling.LANCZOS)

        # Resize GitHub lettering
        lettering_height = 60
        lettering_width = int(github_lettering.width * (lettering_height / github_lettering.height))
        github_lettering = github_lettering.resize((lettering_width, lettering_height), Image.Resampling.LANCZOS)

        # Calculate combined width with spacing
        mark_lettering_spacing = 15
        combined_width = mark_width + mark_lettering_spacing + lettering_width
        combined_height = max(mark_height, lettering_height)

        # Create a semi-transparent black background for the logos
        logo_bg_padding = 20
        logo_bg_x = WIDTH - combined_width - 40 - logo_bg_padding
        logo_bg_y = 40 - logo_bg_padding
        logo_bg_width = combined_width + (logo_bg_padding * 2)
        logo_bg_height = combined_height + (logo_bg_padding * 2)

        # Draw rounded rectangle with black transparent background
        overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        overlay_draw.rounded_rectangle(
            [logo_bg_x, logo_bg_y, logo_bg_x + logo_bg_width, logo_bg_y + logo_bg_height],
            radius=12,
            fill=(0, 0, 0, 180)  # Black with transparency
        )

        # Composite the overlay onto the main image
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')

        # Position GitHub mark and lettering in upper right corner
        mark_x = WIDTH - combined_width - 40 - logo_bg_padding + logo_bg_padding
        mark_y = 40 + (combined_height - mark_height) // 2

        lettering_x = mark_x + mark_width + mark_lettering_spacing
        lettering_y = 40 + (combined_height - lettering_height) // 2

        # Convert back to RGBA to paste logos
        img = img.convert('RGBA')

        # Paste GitHub mark
        if github_mark.mode == 'RGBA':
            img.paste(github_mark, (mark_x, mark_y), github_mark)
        else:
            img.paste(github_mark, (mark_x, mark_y))

        # Paste GitHub lettering
        if github_lettering.mode == 'RGBA':
            img.paste(github_lettering, (lettering_x, lettering_y), github_lettering)
        else:
            img.paste(github_lettering, (lettering_x, lettering_y))

        # Convert back to RGB
        img = img.convert('RGB')

    except Exception as e:
        print(f"Could not load GitHub logos: {e}")

    # Save the image
    img.save(OUTPUT_FILE_V3, quality=95)
    print(f"Social media card v3 created: {OUTPUT_FILE_V3}")
    print(f"Dimensions: {WIDTH}x{HEIGHT}px")
    print(f"Perfect for GitHub social preview and sharing!")

if __name__ == "__main__":
    create_social_card()
    print()
    create_social_card_v2()
    print()
    create_social_card_v3()
