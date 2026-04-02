from PIL import Image
from collections import Counter

def get_dominant_color(image_path):
    try:
        img = Image.open(image_path)
        img = img.convert("RGBA")
        
        # Resize to speed up processing
        img = img.resize((50, 50))
        
        pixels = list(img.getdata())
        
        # Filter out transparent pixels
        valid_pixels = [p for p in pixels if p[3] > 0]
        
        if not valid_pixels:
            return "#FFFFFF" # Default if empty/transparent
            
        # Count colors
        counts = Counter(valid_pixels)
        most_common = counts.most_common(1)[0][0]
        
        return f"#{most_common[0]:02x}{most_common[1]:02x}{most_common[2]:02x}"
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    color = get_dominant_color("frontend/public/Logo.png")
    if color:
        print(color)
    else:
        print("Failed")
