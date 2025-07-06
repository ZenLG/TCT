from PIL import Image, ImageDraw

def create_default_icon():
    # Create a 256x256 image with a white background
    img = Image.new('RGB', (256, 256), 'white')
    draw = ImageDraw.Draw(img)
    
    # Draw a simple design (blue rectangle with TCT text)
    draw.rectangle([32, 32, 224, 224], fill='#2196F3')
    
    # Save as ICO with multiple sizes
    img.save('icon.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
    print("Default icon created successfully!")

if __name__ == '__main__':
    create_default_icon() 