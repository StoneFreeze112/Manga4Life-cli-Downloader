import re
import requests
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

def generate_image_url(manga_name, chapter_number, png_number, manga_address):
    base_url = f"https://{manga_address}/manga/{{}}/{{}}-{{:03d}}.png"
    formatted_manga_name = manga_name.replace(" ", "-")
    url = base_url.format(formatted_manga_name, str(chapter_number).zfill(4), png_number)
    return url

def download_image(url, path):
    try:
        with requests.get(url, stream=True) as response:
            if response.status_code == 200:
                with open(path, 'wb') as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
                print(f"Downloaded: {url}")
                return True
            else:
                print(f"Failed to download {url}: Status code {response.status_code}")
                return False
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def extract_text_from_html(html_content):
    pattern = re.compile(r'vm\.CurPathName\s*=\s*"([^"]+)"')
    matches = pattern.findall(html_content)
    if matches:
        for match in matches:
            if 'us' in match:
                return match
    print("No line containing 'us' found.")
    return None

def extract_text_from_url(manga_name, manga_chapter):
    manga_name = manga_name.replace(" ", "-")
    url = f"https://manga4life.com/read-online/{manga_name}-chapter-{manga_chapter}.html"
    try:
        with requests.get(url) as response:
            if response.status_code == 200:
                html_content = response.text
                return extract_text_from_html(html_content)
            else:
                print(f"Error: {response.status_code}")
                return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

def download_chapter_images(args):
    manga_name, chapter_number, manga_address, chapter_folder = args
    png_number = 1
    while True:
        url = generate_image_url(manga_name, chapter_number, png_number, manga_address)
        image_filename = "{:03d}.png".format(png_number)
        image_path = chapter_folder / image_filename
        if not download_image(url, image_path):
            print(f"Download of Chapter {chapter_number} Complete")
            break
        png_number += 1

def main():
    manga_name = input("Enter the manga name: ").title()
    input_chapters = input("Enter the chapter number(s) separated by commas: ")
    chapters_to_download = [int(chapter.strip()) for chapter in input_chapters.split(",")]

    formatted_manga_name = manga_name.replace(" ", "-")
    manga_folder = Path(formatted_manga_name)
    manga_folder.mkdir(exist_ok=True)

    with requests.Session() as session, ThreadPoolExecutor() as executor:
        for chapter_number in chapters_to_download:
            chapter_folder_name = f"Chapter: {str(chapter_number).zfill(4)}"
            chapter_folder = manga_folder / chapter_folder_name
            chapter_folder.mkdir(exist_ok=True)

            manga_address = extract_text_from_url(manga_name, chapter_number)
            if manga_address:
                executor.map(download_chapter_images, [(manga_name, chapter_number, manga_address, chapter_folder)])

if __name__ == "__main__":
    main()
