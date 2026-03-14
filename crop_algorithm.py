import os
from PIL import Image


def crop_image(image, crop_region):
    x = crop_region['x']
    y = crop_region['y']
    width = crop_region['width']
    height = crop_region['height']

    cropped = image.crop((
        x,
        y,
        x + width,
        y + height
    ))

    return cropped


def save_cropped_image(cropped_image, output_path, original_format=None):
    save_format = original_format if original_format else 'PNG'

    if save_format.upper() == 'JPEG':
        if cropped_image.mode in ('RGBA', 'LA', 'P'):
            cropped_image = cropped_image.convert('RGB')
        save_format = 'JPEG'

    try:
        if save_format.upper() == 'PNG' and not output_path.lower().endswith('.png'):
            output_path += '.png'
        elif save_format.upper() == 'JPEG':
            if not output_path.lower().endswith(('.jpg', '.jpeg')):
                output_path = os.path.splitext(output_path)[0] + '.jpg'

        cropped_image.save(output_path, format=save_format)
        return True, output_path
    except Exception as e:
        return False, str(e)


def crop_and_save(image, crop_region, output_path):
    cropped = crop_image(image, crop_region)

    original_format = image.format

    success, result = save_cropped_image(cropped, output_path, original_format)

    return success, result


def get_image_format(filepath):
    try:
        with Image.open(filepath) as img:
            return img.format
    except:
        return None
