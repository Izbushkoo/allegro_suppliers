import io
import re
import time

import httpx
import requests
import hashlib
import os
import aiofiles
import aiohttp
import asyncio

import xml.etree.ElementTree as ET

from app.loggers import ToLog

urls = {
    "pgn": "https://b2b.pgn.com.pl/xml?id=26",
    "unimet": "https://img.unimet.pl/cennik.xml",
    "hurtprem": "https://www.hurtowniaprzemyslowa.pl/xml/baselinker.xml",
    "rekman": "https://api.rekman.com.pl/cennik.php?email=aradzevich&password=GeVIOj&TylkoNaStanie=TRUE",
    "growbox": "https://goodlink.pl/pl/xmlapi/1/3/utf8/39f5f529-deb6-4d82-87bf-5ccf0807a24d"
}


async def download_xml(supplier):
    url = urls[supplier]
    # file_dest = os.path.join(os.getcwd(), "xml", f"{supplier}.xml")

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response_text = await response.text()

            # with open(file_dest, 'w', encoding='utf-8') as file:
            #     file.write(response_text)
            ToLog.write_basic(f"Content downloaded for {url}")
            return response_text


async def download_file(url):

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()  # Проверка на ошибки HTTP

            # async with aiofiles.open(destination_path, 'wb') as file:
            #     async for chunk in response.aiter_bytes():
            #         if chunk:  # Фильтрация пустых блоков
            #             await file.write(chunk)

    ToLog.write_basic(f"Content downloaded for {url}")
    return response.text


async def validate_xml_file(content):
    try:
        tree = ET.parse(io.StringIO(content))
        return True
    except ET.ParseError as e:
        ToLog.write_error(f"XML file validation failed: {e}")
        return False


async def download_with_retry(supplier, retries=10, delay=5):
    url = urls[supplier]
    # destination_path = os.path.join(os.getcwd(), "xml", f"{supplier}.xml")

    for attempt in range(retries):
        try:
            content = await download_file(url)
            if await validate_xml_file(content):
                ToLog.write_basic("File downloaded and verified successfully")
                return content
            else:
                raise ValueError("File validation failed")
        except Exception as e:
            ToLog.write_basic(f"Attempt {attempt + 1} failed: {e}")
            if attempt + 1 < retries:
                ToLog.write_basic(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                raise
    raise RuntimeError("Failed to download file after multiple attempts")


def download_xml_sync(supplier):
    url = urls[supplier]
    file_dest = os.path.join(os.getcwd(), "xml", f"{supplier}.xml")

    result = requests.get(url)
    response_text = result.text

    with open(file_dest, 'w', encoding='utf-8') as file:
        file.write(response_text)

    ToLog.write_basic(f"File downloaded to {file_dest}")


def download_content_sync(supplier):
    url = urls[supplier]
    response = requests.get(url)
    response.raise_for_status()
    ToLog.write_basic(f"Content downloaded from {url}")
    content = response.content  # Получение содержимого в байтах

    # Удаление BOM (если присутствует)
    boms = [b'\xef\xbb\xbf', b'\xff\xfe', b'\xfe\xff']
    for bom in boms:
        if content.startswith(bom):
            content = content[len(bom):]

    content = content.decode('utf-8')  # Декодирование содержимого обратно в текст

    # Удаление неиспользуемых управляющих символов
    content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
    ToLog.write_basic(f"first 40 symbols: {content[:40]}")
    return content


def validate_content_sync(content):
    try:
        tree = ET.fromstring(content)
        return True
    except ET.ParseError as e:
        ToLog.write_error(f"XML file validation failed: {e}")
        return False


def download_with_retry_sync(supplier, retries=10, delay=5):
    url = urls[supplier]

    for attempt in range(retries):
        try:
            content = download_content_sync(supplier)
            if validate_content_sync(content):
                ToLog.write_basic(f"Content from {url} verified successfully")
                return content
            else:
                raise ValueError("File validation failed")
        except Exception as e:
            ToLog.write_basic(f"Attempt {attempt + 1} failed: {e}")
            if attempt + 1 < retries:
                ToLog.write_basic(f"Retrying in {delay} seconds...")
                time.sleep(5)
            else:
                raise
    raise RuntimeError("Failed to download file after multiple attempts")

