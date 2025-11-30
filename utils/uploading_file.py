import asyncio
import httpx


client = httpx.AsyncClient(base_url="https://0x0.st", timeout=120, headers={
    "User-Agent": "Userbot/0.9 Kurigram/2.2.12 (python, like pyrogram) Alekzum/1325079151"
})


async def upload_file(path: str) -> str:
    return (await client.post('', files={'file': open(path, 'rb')})).text

if __name__ == "__main__":
    async def _main():
        url = await upload_file(r'C:\Users\79967\PycharmProjects\UserBot\utils\music.py')
        print(url)
    asyncio.run(_main())
