import asyncio
import logging
import websockets
import names
import aiohttp
import json
from datetime import datetime, timedelta
from websockets import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosedOK
from aiofile import AIOFile, Writer
from aiopath import AsyncPath
import sys

logging.basicConfig(level=logging.INFO)


# Клієнт для отримання курсів валют через API ПриватБанку
class PrivatbankAPIClient:
    BASE_URL = 'https://api.privatbank.ua/p24api/exchange_rates?json&date='

    def __init__(self, days, currencies):
        self.days = days
        self.currencies = currencies

    async def fetch_rate_for_date(self, date):
        url = f'{self.BASE_URL}{date.strftime("%d.%m.%Y")}'
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Error: {response.status}")
                    data = await response.json()
                    return self.extract_rates(data)
        except Exception as e:
            print(f"Failed to fetch data for {date}: {e}")
            return None

    def extract_rates(self, data):
        date = data['date']
        rates = {}
        for rate in data['exchangeRate']:
            if rate['currency'] in self.currencies:
                rates[rate['currency']] = {
                    'sale': rate.get('saleRate', 'N/A'),
                    'purchase': rate.get('purchaseRate', 'N/A')
                }
        return {date: rates}

    async def fetch_rates(self):
        tasks = []
        for i in range(self.days):
            date = datetime.now() - timedelta(days=i)
            tasks.append(self.fetch_rate_for_date(date))
        return await asyncio.gather(*tasks)


# Сервіс для роботи з обмінними курсами та обробки команд exchange
class ExchangeRateService:
    def __init__(self, client):
        self.client = client

    async def get_rates(self):
        return await self.client.fetch_rates()

    async def log_exchange(self, command):
        path = AsyncPath('exchange_log.txt')
        async with AIOFile(path, 'a') as afp:
            writer = Writer(afp)
            await writer(f"{datetime.now()}: {command}\n")

    async def handle_exchange_command(self, params):
        days = int(params[0]) if params else 1
        self.client.days = days
        rates = await self.get_rates()
        await self.log_exchange(f"exchange {days}")
        return rates


    async def handle_chat(self, websocket, path):
        async for message in websocket:
            if message.startswith("exchange"):
                params = message.split()[1:]
                rates = await self.handle_exchange_command(params)
                await websocket.send(json.dumps([rate for rate in rates if rate], indent=2))


# Сервер WebSocket
class Server:
    clients = set()

    async def register(self, ws: WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            await asyncio.gather(*[client.send(message) for client in self.clients])

    async def ws_handler(self, ws: WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distrubute(ws)
        except ConnectionClosedOK:
            pass
        finally:
            await self.unregister(ws)

    async def distrubute(self, ws: WebSocketServerProtocol):
        async for message in ws:
            await self.send_to_clients(f"{ws.name}: {message}")


async def run_chat_server(service):
    async with websockets.serve(service.handle_chat, 'localhost', 8765):
        print("WebSocket server started on ws://localhost:8765")
        await asyncio.Future()


async def main():
    # Парсинг аргументів командного рядка
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    if days > 10:
        print("Cannot fetch rates for more than 10 days")
        return

    # Додаткові валюти
    currencies = sys.argv[2:] if len(sys.argv) > 2 else ['EUR', 'USD', 'PLN']

    # Ініціалізація клієнта та сервісу
    client = PrivatbankAPIClient(days, currencies)
    service = ExchangeRateService(client)

    # Запуск WebSocket сервера
    await run_chat_server(service)


if __name__ == '__main__':
    asyncio.run(main())
