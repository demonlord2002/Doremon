import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch
from config import YOUTUBE_IMG_URL
from AviaxMusic.core.dir import CACHE_DIR

# === Premium Layout & Style Settings === #
CANVAS_SIZE = (1280, 720)
PANEL_W, PANEL_H = 1000, 320  # Slightly taller for premium look
PANEL_X = (CANVAS_SIZE[0] - PANEL_W) // 2
PANEL_Y = (CANVAS_SIZE[1] - PANEL_H) // 2

THUMB_W, THUMB_H = 280, 280  # Larger thumbnail
THUMB_X = PANEL_X + 40
THUMB_Y = PANEL_Y + (PANEL_H - THUMB_H) // 2

TEXT_X = THUMB_X + THUMB_W + 40
TITLE_Y = THUMB_Y + 25
ARTIST_Y = TITLE_Y + 70
DURATION_Y = ARTIST_Y + 45
BAR_Y = DURATION_Y + 40

# Play Icons Settings
ICONS_W, ICONS_H = 280, 60
ICONS_X = TEXT_X
ICONS_Y = BAR_Y + 35

TRANSPARENCY = 90  # More transparent for premium look
CORNER_RADIUS = 40  # More rounded corners

MAX_TITLE_WIDTH = 580
MAX_ARTIST_WIDTH = 580

# Premium color scheme
PREMIUM_COLORS = {
    'text_primary': (255, 255, 255),
    'text_secondary': (200, 200, 200),
    'text_tertiary': (150, 150, 150),
    'accent_glow': (255, 105, 180, 180),  # Pink accent for icons
}

def trim_to_width(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    ellipsis = "…"
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if font.getlength(text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis
    return ellipsis

def get_dominant_color(image):
    """Extract dominant color from image with premium color adjustment"""
    # Resize for processing
    small = image.resize((50, 50))
    
    if small.mode != 'RGB':
        small = small.convert('RGB')
    
    # Get colors with better sampling
    colors = small.getcolors(2500)
    
    if not colors:
        return (80, 120, 200)  # Premium blue fallback
    
    # Sort by frequency and get the most vibrant color
    colors.sort(key=lambda x: x[0], reverse=True)
    
    # Take top 5 colors and pick the most vibrant one
    top_colors = [color[1] for color in colors[:5]]
    
    def color_vibrancy(rgb):
        r, g, b = rgb
        return abs(r - g) + abs(g - b) + abs(b - r)
    
    vibrant_color = max(top_colors, key=color_vibrancy)
    
    # Enhance color for premium look
    r, g, b = vibrant_color
    enhanced = (
        min(255, int(r * 1.1)),
        min(255, int(g * 1.1)),
        min(255, int(b * 1.1))
    )
    
    return enhanced

def create_premium_glass_effect(size, blur_radius=15, transparency=120):
    """Create premium glass morphism effect"""
    width, height = size
    
    # Create base glass panel
    glass = Image.new('RGBA', size, (255, 255, 255, transparency))
    
    # Apply blur for glass effect
    glass = glass.filter(ImageFilter.GaussianBlur(blur_radius))
    
    return glass

def add_corner_glow(draw, position, size, color, corner_radius, intensity=25):
    """Add glow specifically to corners for premium effect"""
    x, y = position
    w, h = size
    
    # Create glow layer
    glow_size = (w + intensity*2, h + intensity*2)
    glow = Image.new('RGBA', glow_size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    
    # Draw rounded rectangle glow
    glow_draw.rounded_rectangle(
        [0, 0, glow_size[0], glow_size[1]],
        radius=corner_radius + 10,
        fill=color
    )
    
    # Blur the glow
    glow = glow.filter(ImageFilter.GaussianBlur(15))
    
    return glow

async def gen_thumb(videoid: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_premium.png")
    if os.path.exists(cache_path):
        return cache_path

    # --- YouTube Data ---
    results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
    try:
        data = (await results.next())["result"][0]
        title = re.sub(r"\W+", " ", data.get("title", "Untitled")).title()
        thumbnail = data.get("thumbnails", [{}])[0].get("url", YOUTUBE_IMG_URL)
        artist = data.get("channel", {}).get("name", "Unknown Artist")
        duration = data.get("duration")
    except Exception:
        title, thumbnail, artist, duration = "Unknown Title", YOUTUBE_IMG_URL, "Unknown Artist", "Live"

    is_live = not duration or str(duration).lower() in {"", "live", "live now"}
    duration_text = "LIVE 🔴" if is_live else f"{duration}"

    # --- Download thumbnail ---
    thumb_path = os.path.join(CACHE_DIR, f"thumb_{videoid}.png")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await resp.read())
    except Exception:
        return YOUTUBE_IMG_URL

    # --- Premium Background with Gradient Overlay ---
    base = Image.open(thumb_path).convert("RGBA").resize(CANVAS_SIZE)
    
    # Enhanced blur with premium settings
    bg_blur = base.filter(ImageFilter.GaussianBlur(30))
    bg_blur = ImageEnhance.Brightness(bg_blur).enhance(0.5)
    bg_blur = ImageEnhance.Contrast(bg_blur).enhance(1.3)

    # --- Extract and enhance dominant color ---
    dominant_color = get_dominant_color(base)
    glow_rgb = dominant_color
    glow_color_alpha = (*glow_rgb, 120)

    # Create dark background for premium look
    dark_bg = Image.new('RGBA', CANVAS_SIZE, (20, 20, 30, 255))
    dark_bg = Image.alpha_composite(dark_bg, bg_blur)

    # --- Premium Glass Panel ---
    glass_panel = create_premium_glass_effect((PANEL_W, PANEL_H), 20, TRANSPARENCY)
    
    # Add subtle border to glass panel
    border = Image.new('RGBA', (PANEL_W, PANEL_H), (255, 255, 255, 30))
    glass_panel = Image.alpha_composite(glass_panel, border)
    
    # Create mask for rounded corners
    panel_mask = Image.new('L', (PANEL_W, PANEL_H), 0)
    panel_draw = ImageDraw.Draw(panel_mask)
    panel_draw.rounded_rectangle((0, 0, PANEL_W, PANEL_H), CORNER_RADIUS, fill=255)
    
    # Apply glass panel to background
    dark_bg.paste(glass_panel, (PANEL_X, PANEL_Y), panel_mask)

    # --- Corner Glow Effect ---
    corner_glow = add_corner_glow(None, (PANEL_X, PANEL_Y), (PANEL_W, PANEL_H), 
                                glow_color_alpha, CORNER_RADIUS, 30)
    dark_bg.paste(corner_glow, (PANEL_X - 25, PANEL_Y - 25), corner_glow)

    draw = ImageDraw.Draw(dark_bg)

    # --- Premium Fonts ---
    try:
        # Try to use premium fonts
        title_font = ImageFont.truetype("AviaxMusic/assets/font2.ttf", 52)
        artist_font = ImageFont.truetype("AviaxMusic/assets/font.ttf", 32)
        duration_font = ImageFont.truetype("AviaxMusic/assets/font.ttf", 26)
        small_font = ImageFont.truetype("AviaxMusic/assets/font.ttf", 22)
    except OSError:
        # Fallback to default fonts
        title_font = ImageFont.load_default()
        artist_font = ImageFont.load_default()
        duration_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # --- Premium Thumbnail with Enhanced Glow ---
    thumb_img = Image.open(thumb_path).convert("RGBA").resize((THUMB_W, THUMB_H), Image.LANCZOS)
    
    # Thumbnail shadow/glow
    thumb_shadow = Image.new('RGBA', (THUMB_W + 40, THUMB_H + 40), (*glow_rgb, 100))
    thumb_shadow = thumb_shadow.filter(ImageFilter.GaussianBlur(20))
    dark_bg.paste(thumb_shadow, (THUMB_X - 20, THUMB_Y - 20), thumb_shadow)
    
    # Thumbnail with rounded corners
    thumb_mask = Image.new('L', (THUMB_W, THUMB_H), 0)
    ImageDraw.Draw(thumb_mask).rounded_rectangle((0, 0, THUMB_W, THUMB_H), 30, fill=255)
    dark_bg.paste(thumb_img, (THUMB_X, THUMB_Y), thumb_mask)

    # --- Premium Text Styling ---
    trimmed_title = trim_to_width(title, title_font, MAX_TITLE_WIDTH)
    trimmed_artist = trim_to_width(artist, artist_font, MAX_ARTIST_WIDTH)
    
    # Title with subtle shadow
    title_shadow_offset = 3
    draw.text((TEXT_X + title_shadow_offset, TITLE_Y + title_shadow_offset), 
              trimmed_title, font=title_font, fill=(0, 0, 0, 80))
    draw.text((TEXT_X, TITLE_Y), trimmed_title, font=title_font, 
              fill=PREMIUM_COLORS['text_primary'])
    
    # Artist name
    draw.text((TEXT_X, ARTIST_Y), trimmed_artist, font=artist_font, 
              fill=PREMIUM_COLORS['text_secondary'])
    
    # Duration text
    draw.text((TEXT_X, DURATION_Y), f"Duration: {duration_text}", font=duration_font, 
              fill=PREMIUM_COLORS['text_tertiary'])

    # --- Premium Progress Bar ---
    bar_len = 500
    bar_height = 6
    bar_x = TEXT_X
    bar_y = BAR_Y
    
    # Bar background
    draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_len, bar_y + bar_height), 
                          3, fill=(60, 60, 70, 255))
    
    # Progress with glow
    progress_width = 200
    progress_glow = Image.new('RGBA', (progress_width + 20, bar_height + 20), (*glow_rgb, 80))
    progress_glow = progress_glow.filter(ImageFilter.GaussianBlur(10))
    dark_bg.paste(progress_glow, (bar_x - 10, bar_y - 10), progress_glow)
    
    draw.rounded_rectangle((bar_x, bar_y, bar_x + progress_width, bar_y + bar_height), 
                          3, fill=glow_rgb)

    # Time indicators
    draw.text((bar_x, bar_y + 12), "0:00", font=small_font, 
              fill=PREMIUM_COLORS['text_tertiary'])
    draw.text((bar_x + bar_len - 60, bar_y + 12), duration_text, font=small_font, 
              fill=PREMIUM_COLORS['text_tertiary'])

    # --- Premium Play Icons ---
    icons_path = "AviaxMusic/assets/play_icons.png"
    if os.path.isfile(icons_path):
        try:
            ic = Image.open(icons_path).convert("RGBA")
            ic = ic.resize((ICONS_W, ICONS_H), resample=Image.LANCZOS)

            # Extract alpha channel
            r, g, b, a = ic.split()

            # Create colored glow based on alpha mask
            color_img = Image.new("RGBA", ic.size, PREMIUM_COLORS['accent_glow'])
            color_img.putalpha(a)
            color_glow = color_img.filter(ImageFilter.GaussianBlur(10))
            dark_bg.paste(color_glow, (ICONS_X - 8, ICONS_Y - 8), color_glow)

            # White silhouette for crispness
            white_layer = Image.new("RGBA", ic.size, (255, 255, 255, 255))
            white_layer.putalpha(a)
            dark_bg.paste(white_layer, (ICONS_X, ICONS_Y), white_layer)

            # Paste original icon on top with slight reduced alpha to keep texture
            ic_top = ic.copy()
            # Reduce alpha a bit to blend nicely
            try:
                top_a = ic_top.split()[3].point(lambda p: int(p * 0.9))
                ic_top.putalpha(top_a)
            except Exception:
                pass
            dark_bg.paste(ic_top, (ICONS_X, ICONS_Y), ic_top)
        except Exception as e:
            print(f"Icons error: {e}")
            # Fallback: draw simple play button
            draw.rounded_rectangle((ICONS_X, ICONS_Y, ICONS_X + 200, ICONS_Y + 50), 
                                 10, fill=(255, 105, 180, 200))
            draw.text((ICONS_X + 70, ICONS_Y + 10), "▶ PLAY", font=small_font, fill="white")

    # --- Premium Signature ---
    signature_bg = Image.new('RGBA', (220, 35), (0, 0, 0, 120))
    signature_bg = signature_bg.filter(ImageFilter.GaussianBlur(5))
    dark_bg.paste(signature_bg, (35, CANVAS_SIZE[1] - 50), signature_bg)
    
    draw.text((50, CANVAS_SIZE[1] - 45), "Dev: @SunsetOfMe", font=small_font, 
              fill=PREMIUM_COLORS['text_primary'])

    # --- Final Premium Touches ---
    # Add subtle gradient overlay
    gradient = Image.new('RGBA', CANVAS_SIZE, (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(gradient)
    for i in range(CANVAS_SIZE[1]):
        alpha = int(30 * (i / CANVAS_SIZE[1]))
        gradient_draw.line([(0, i), (CANVAS_SIZE[0], i)], fill=(0, 0, 0, alpha))
    
    dark_bg = Image.alpha_composite(dark_bg, gradient)

    # --- Cleanup ---
    try:
        os.remove(thumb_path)
    except OSError:
        pass

    # Save with premium quality
    dark_bg.save(cache_path, quality=100, optimize=True)
    return cache_path
