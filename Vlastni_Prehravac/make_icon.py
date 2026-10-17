from PIL import Image
img = Image.open('assets/icon.png').resize((256, 256))
img.save('assets/icon.ico', format='ICO', sizes=[(256,256),(48,48),(32,32),(16,16)])
print('icon.ico saved')
