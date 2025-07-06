from PIL import Image
import os

def create_ico(input_file, output_file, sizes=None):
    if sizes is None:
        sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]
    
    img = Image.open(input_file)
    img.save(output_file, format='ICO', sizes=sizes)
    print(f"Icon converted successfully to {output_file}!")

# Convert PNG to ICO if PNG exists, otherwise try to use SVG directly
if os.path.exists('icon.png'):
    create_ico('icon.png', 'icon.ico')
elif os.path.exists('icon.svg'):
    try:
        img = Image.open('icon.svg')
        img.save('icon.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
        print("Icon converted successfully from SVG!")
    except Exception as e:
        print(f"Error converting SVG: {e}")
        print("Please convert your SVG to PNG first using an external tool.") 