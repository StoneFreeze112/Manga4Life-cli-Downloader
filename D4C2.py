import re
import aiohttp
import asyncio
import aiofiles
import logging
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from colorama import init, Fore, Style

# Initialize Colorama
init(autoreset=True)

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]"
)

class MangaDownloader:
    def __init__(self, manga_name: str, uppercase: bool = False, edit: bool = False):
        if edit:
            self.manga_name = manga_name
        else:
            self.manga_name = manga_name.upper() if uppercase else manga_name.title()

        self.formatted_manga_name = re.sub(r'\s+', '-', self.manga_name)
        self.main_folder = Path("Mangas")
        self.manga_folder = self.main_folder / self.formatted_manga_name
        self.history_file = Path("download_history.txt")
        self.manga_folder.mkdir(parents=True, exist_ok=True)

    def format_chapter_number(self, chapter_number: str) -> str:
        if '.' in chapter_number:
            integer_part, decimal_part = chapter_number.split('.')
            formatted_chapter_number = f"{int(integer_part):04d}.{decimal_part}"
        else:
            formatted_chapter_number = f"{int(chapter_number):04d}"
        return formatted_chapter_number

    async def generate_image_url(self, chapter_number: str, png_number: int, manga_address: str) -> str:
        base_url = f"https://{manga_address}/manga/{{}}/{{}}-{{:03d}}.png"
        url = base_url.format(self.formatted_manga_name, chapter_number, png_number)
        return url

    async def download_image(self, session: aiohttp.ClientSession, url: str) -> bytes:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logging.warning(f"Failed to download {url}: {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logging.error(f"Error downloading {url}: {e}")
            return None

    def extract_text_from_html(self, html_content: str) -> str:
        pattern = re.compile(r'vm\.CurPathName\s*=\s*"([^"]+)"')
        matches = pattern.findall(html_content)
        return matches[0] if matches else None

    async def extract_text_from_url(self, session: aiohttp.ClientSession, chapter_number: str) -> str:
        formatted_chapter_number = self.format_chapter_number(chapter_number)
        url = f"https://manga4life.com/read-online/{self.formatted_manga_name}-chapter-{formatted_chapter_number}.html"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    html_content = await response.text()
                    manga_address = self.extract_text_from_html(html_content)
                    if not manga_address:
                        alt_url = f"https://manga4life.com/read-online/{self.formatted_manga_name}-chapter-{formatted_chapter_number}-index-2.html"
                        async with session.get(alt_url) as alt_response:
                            if alt_response.status == 200:
                                html_content = await alt_response.text()
                                manga_address = self.extract_text_from_html(html_content)
                    return manga_address
                else:
                    return None
        except aiohttp.ClientError:
            return None

    async def count_pages_in_chapter(self, session: aiohttp.ClientSession, chapter_number: str) -> int:
        formatted_chapter_number = self.format_chapter_number(chapter_number)
        manga_address = await self.extract_text_from_url(session, formatted_chapter_number)
        if manga_address:
            async def check_page_exists(png_number):
                url = await self.generate_image_url(formatted_chapter_number, png_number, manga_address)
                try:
                    async with session.get(url) as response:
                        return response.status == 200
                except aiohttp.ClientError:
                    return False

            tasks = [check_page_exists(png_number) for png_number in range(1, 101)]
            results = await asyncio.gather(*tasks)
            return sum(results)
        return 0

    async def colorful_progress_bar(self, current: int, total: int):
        current = min(current, total)
        percent = (current / total) * 100
        bar_length = 50
        filled_length = int(bar_length * current // total)

        bar = '█' * filled_length + '-' * (bar_length - filled_length)

        if percent < 50:
            color = Fore.RED
        elif percent < 80:
            color = Fore.YELLOW
        else:
            color = Fore.GREEN

        sys.stdout.write(f'\r{color}[{bar}] {percent:.2f}%{Style.RESET_ALL}')
        sys.stdout.flush()

    async def download_chapter_images(self, session: aiohttp.ClientSession, chapter_number: str, total_pages: int, chapter_index: int) -> list:
        formatted_chapter_number = self.format_chapter_number(chapter_number)
        manga_address = await self.extract_text_from_url(session, formatted_chapter_number)
        image_data = []

        if manga_address:
            png_number = 1
            for _ in range(total_pages):  
                url = await self.generate_image_url(formatted_chapter_number, png_number, manga_address)
                image_bytes = await self.download_image(session, url)
                if image_bytes:
                    image_data.append(image_bytes)
                    overall_progress = (chapter_index * total_pages) + png_number
                    await self.colorful_progress_bar(overall_progress, total_chapters_pages)
                png_number += 1

            return image_data
        else:
            return []

    async def save_chapter_to_pdf(self, chapter_number: str, image_data: list):
        pdf_filename = self.manga_folder / f"Chapter-{self.format_chapter_number(chapter_number)}.pdf"
        c = canvas.Canvas(str(pdf_filename), pagesize=letter)

        for image_bytes in image_data:
            with NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                temp_file.write(image_bytes)
                temp_file_path = temp_file.name
                width, height = letter
                c.drawImage(temp_file_path, 0, 0, width=width, height=height, preserveAspectRatio=True, anchor='c')
                c.showPage()  # Create a new page

        c.save()

    async def download_chapters(self, chapters_to_download: list):
        chapter_count = len(chapters_to_download)
        logging.info(f"There are {chapter_count} chapter(s) to download.")

        global total_chapters_pages
        async with aiohttp.ClientSession() as session:
            # Gather counts of pages in all chapters
            page_counts = await asyncio.gather(*(self.count_pages_in_chapter(session, chapter_number) for chapter_number in chapters_to_download))
            total_chapters_pages = sum(page_counts)

        user_input = input("Do you want to proceed with the download? (Y/N): ").strip().upper()
        if user_input != 'Y':
            logging.info("Download canceled by user.")
            return

        conn = aiohttp.TCPConnector(limit=10)
        async with aiohttp.ClientSession(connector=conn) as session:
            for chapter_index, chapter_number in enumerate(chapters_to_download):
                total_pages = page_counts[chapter_index]
                image_data = await self.download_chapter_images(session, chapter_number, total_pages, chapter_index)
                if image_data:
                    await self.save_chapter_to_pdf(chapter_number, image_data)

        await self.save_history(self.manga_name)
        logging.info(f"Saved {self.manga_name} to history.")

    async def save_history(self, manga_name: str):
        if not self.history_file.exists():
            self.history_file.touch()
        async with aiofiles.open(self.history_file, 'a+') as file:
            await file.seek(0)
            history = await file.read()
            if manga_name not in history:
                await file.write(manga_name + "\n")
                logging.info(f"Saved {manga_name} to history.")

    async def load_history(self):
        if self.history_file.exists():
            async with aiofiles.open(self.history_file, 'r') as file:
                history = await file.read()
                logging.info("Download History:")
                for manga in history.splitlines():
                    logging.info(manga)
        else:
            logging.info("No download history found.")

def parse_chapters(chapters_str):
    chapters = []
    for part in chapters_str.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            chapters.extend(range(start, end + 1))
        else:
            chapters.append(int(part))
    return [str(chapter) for chapter in chapters]

async def main():
    manga_name = input("Please type Manga Name: ").strip()
    chapters_str = input("Please input Manga Chapter Number(s) (e.g., 1,2-5): ").strip()
    uppercase = input("Would you like the manga name to be uppercase? (y/n): ").strip().lower() == 'y'
    edit = input("Would you like to edit the manga name? (y/n): ").strip().lower() == 'y'

    downloader = MangaDownloader(manga_name, uppercase=uppercase, edit=edit)
    chapters_to_download = parse_chapters(chapters_str)
    
    await downloader.download_chapters(chapters_to_download)

if __name__ == "__main__":
    asyncio.run(main())
