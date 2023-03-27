import random
import logging
import datetime
import sqlite3
import string
import hashlib
from jinja2 import Template
from config import *
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO)

bot = Bot(API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

conn = sqlite3.connect('dictionary.db')
cursor = conn.cursor()


@dp.inline_handler()
async def inline_handler(query: types.InlineQuery):
    x = query.query or 'echo'
    if x != 'echo':
        c = cursor.execute('''SELECT eng, ru, jap FROM dictionary ORDER BY time DESC''').fetchmany(int(x))
        ms = '''{% for c in cur -%}
             {% for i in c -%}   {{ i }}
{% endfor %}
{% endfor %}'''
        tm = Template(ms)
        msg = tm.render(cur=c)
        result_id: str = hashlib.md5(x.encode()).hexdigest()
        articles = [types.InlineQueryResultArticle(id=result_id, title=f'Показать последние {x}',
                                                   input_message_content=types.InputTextMessageContent(
                                                       message_text=msg))]
        await query.answer(articles, cache_time=1, is_personal=True)


@dp.message_handler(commands=['Показать_последние_5'])
async def show_last_5(message: types.Message):
    c = cursor.execute('''SELECT eng, ru, jap FROM dictionary ORDER BY time DESC''').fetchmany(5)
    ms = '''{% for c in cur -%}
    {% for i in c -%}   {{ i }}
{% endfor %}
{% endfor %}'''
    tm = Template(ms)
    msg = tm.render(cur=c)
    await message.answer(msg)


@dp.message_handler(commands=['Показать_последние_?'])
async def show_last_random(message: types.Message):
    c = cursor.execute('''SELECT eng, ru, jap FROM dictionary ORDER BY time DESC''').fetchall()
    ms = '''{% for c in cur -%}
{{ c }}
{% endfor %}'''
    tm = Template(ms)
    msg = tm.render(cur=random.choice(c))
    await message.answer(msg)


btn = KeyboardButton('/Показать_последние_5')
btn2 = KeyboardButton('/Показать_последние_?')
btn_client = ReplyKeyboardMarkup(resize_keyboard=True)
btn_client.add(btn, btn2)


class FSMAdmin(StatesGroup):
    eng = State()
    ru = State()
    jap = State()


@dp.message_handler(state=None)
async def load_eng(message: types.Message, state: FSMContext):
    if all(_ in string.ascii_letters for _ in message.text):
        if not cursor.execute(f"SELECT * FROM dictionary WHERE eng=?", (message.text.lower(),)).fetchone():
            await FSMAdmin.eng.set()
            async with state.proxy() as data:
                data['eng'] = message.text.lower()
            await FSMAdmin.next()
            await message.reply("Теперь на русском:")
        else:
            await message.answer(
                cursor.execute("SELECT ru, jap FROM dictionary WHERE eng=?", (message.text.lower(),)).fetchone())
            await state.finish()

    else:
        try:
            await message.answer(
                cursor.execute("SELECT eng, jap FROM dictionary WHERE ru=?", (message.text.lower(),)).fetchone())

        except Exception as e:
            await message.answer('Ещё не в словаре.', reply_markup=btn_client)

        await state.finish()


@dp.message_handler(state=FSMAdmin.ru)
async def load_ru(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['ru'] = message.text.lower()
    await FSMAdmin.next()
    await message.reply("Теперь японский:")


@dp.message_handler(state=FSMAdmin.jap)
async def load_jap(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['jap'] = message.text.lower()
    try:
        async with state.proxy() as data:
            cursor.execute("INSERT INTO dictionary VALUES (?, ?, ?, ?)",
                           (data['eng'], data['ru'], data['jap'], datetime.date.today()))
            conn.commit()
            await message.answer('Добавил.')
    except Exception as er:
        await message.answer(er)
    finally:
        await state.finish()


async def on_startup(_):
    print('Погнали')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False, on_startup=on_startup)
