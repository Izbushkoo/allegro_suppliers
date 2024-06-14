import os
import aiohttp
import asyncio
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
    file_dest = os.path.join(os.getcwd(), "xml", f"{supplier}.xml")

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response_text = await response.text()

            with open(file_dest, 'w', encoding='utf-8') as file:
                file.write(response_text)
                ToLog.write_basic(f"File downloaded to {file_dest}")

# Example usage:
# asyncio.run(download_xml('pgn'))
