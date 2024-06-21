import asyncio
import json
import os
import signal
import logging
import httpx

logging.basicConfig(level=logging.INFO)


# Функция для отправки уведомления
async def send_error_report(url, resource_id, message):
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, json=json.dumps({"status": "Critical Error", "message": message,
                                                    "resource_id": resource_id}))
        except Exception as e:
            logging.error(f"Failed to send error report: {e}")


def handle_segfault(signum, frame):
    callback_url = os.getenv("CALLBACK_URL")
    resource_id = os.getenv("RESOURCE_ID")
    if callback_url and resource_id:
        message = "Произошла критическая ошибка сегментации. Пожалуйста повторите операцию."
        # Отправка уведомления асинхронно
        asyncio.run(send_error_report(callback_url, resource_id, message))


# Регистрация обработчика сигнала
signal.signal(signal.SIGSEGV, handle_segfault)


def on_exit(server):
    server.log.info("Server is exiting")


def when_ready(server):
    server.log.info("Server is ready. Spawning workers")


# Добавление хуков Gunicorn
on_exit = on_exit
when_ready = when_ready
