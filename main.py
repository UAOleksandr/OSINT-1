import parsers
import apiS4F as S4f
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, Chat, Bot
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)
import random
from parsers import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ocr import ocr
import os
from mega import Mega
import json


FILENAME = "settings.json"

# list of necessary variables
authorized_users = []
settings = {}

# Database necessary variables
session = None
engine = None


db_record = []
solution = ""  # variable for photo_search

# for authentication checkIn
photo_search_flag = False
user_iDs = []
active_user = []  # list of users, that are operating in bot

# regular expressions for handlers
choise_regex = 'Ввід інформації|Пошук інформації|Інструкція'
command_regex = ['Вручну', 'У вигляді файлу']
output_regex = "ПІБ|Адреса|Телефон|Місце роботи/служби|Посада/Звання|ІНПН|Пошук особи за фотографією|Вихід"
error_msg = "Сталась помилка під час використання бота. Радимо натиснути /cancel та почати роботу заново. Просимо вибачення за помилку"
bot_log = "bot.log"
parameter = ""
full_name = None
birthday = None
address = None
works_name = None
military_position = None
telephone_number = None
email_post = None
social_network = None
pasport_info = None
seria_pasport = None
personal_id = None


# Handler constants
ADMIN_PANEL, ADMIN_CHOISE, AUTHORIZATION, MAIN_MENU, IO_CHOISE, INSERTION_MODE, FILE_INSERTION,  GET_PARAMETER, \
    GET_INFO, USER_ADDING, USER_DELETING, INSTRUCTION, TELEPHONE, UPLOAD_TO_MEGA, \
    CONTINUE, PHOTO_INSERTION, INFO_CONFIRMATION, INFO_CORRECTION, LINK_INSERTION, LOG_CHOICE = range(20)


# bot functions
def print_info():
    global full_name, birthday, address, works_name, military_position, telephone_number, email_post, social_network
    global pasport_info, seria_pasport, personal_id
    output_str = ""
    if full_name is not None:
        output_str += parsers.csv_header[0] + ': ' + full_name + '\n'
    if birthday is not None:
        output_str += parsers.csv_header[1] + ': ' + birthday + '\n'
    if address is not None:
        output_str += parsers.csv_header[2] + ': ' + address + '\n'
    if works_name is not None:
        output_str += parsers.csv_header[3] + ': ' + works_name + '\n'
    if military_position is not None:
        output_str += parsers.csv_header[4] + ': ' + military_position + '\n'
    if telephone_number is not None:
        output_str += parsers.csv_header[5] + ': ' + telephone_number + '\n'
    if email_post is not None:
        output_str += parsers.csv_header[6] + ': ' + email_post + '\n'
    if social_network is not None:
        output_str += parsers.csv_header[7] + ': ' + social_network + '\n'
    if pasport_info is not None:
        output_str += parsers.csv_header[8] + ': ' + pasport_info + '\n'
    if seria_pasport is not None:
        output_str += parsers.csv_header[9] + ': ' + seria_pasport + '\n'
    if personal_id is not None:
        output_str += parsers.csv_header[10] + ': ' + personal_id + '\n'
    return output_str


def parse_file(file: str):
    msg = ""
    filetype = file[len(file) - 5:len(file)]
    print(filetype)
    # checking if filetype can be processed
    filetype_flag = True
    photo_flag = False
    for form in parsers.AVAILABLE_FORMATS:
        if form in filetype or filetype  in form:
            filetype_flag = False
            break

    for photo in parsers.PHOTO_FORMATS:
        if photo in filetype:
            photo_flag = True
            break

    if photo_flag:
        return "Для обробки фотографії спробуйте іншу опцію та надішліть фотографію \
у нестисненому виглді"


    elif filetype_flag:
        return "На жаль, даний тип файлів ще не реалізовано"

    else:
        flag = False
        if file:
            flag = parsers.parser(session, file, engine)
    if file:
        os.system(f"DEL {file}")
    if flag:
        return "Дані занесено до БД."
    if not flag:
        return "Дані не було занесено до БД"


# Function to check for admin
def admin(telegram_id):
    global authorized_users
    return telegram_id in [user.telegram_id for user in authorized_users if user.admin]


# User authorization
def start(update: Update, context: CallbackContext) -> int:
    sender = update.message.from_user

    global authorized_users
    authorized_users = parsers.parse_users()
    global user_iDs
    user_iDs = [user.telegram_id for user in authorized_users]

    # sending the user in the direction of russian battleship if the user is not in authorized_users
    if sender.id not in user_iDs:
        update.message.reply_text("Вам користуватись ботом не дозволено, ідіть нахуй")
        # Chat.ban_member(user_id=sender.id)
    else:
        update.message.reply_text("Введіть ПІН для входу в систему")
        return AUTHORIZATION


def cancel(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    global authorized_users
    update.message.reply_text("Робота із ботом завершена", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def authorization(update: Update, context: CallbackContext) -> int:
    sender = update.message.from_user
    global active_user
    PIN = update.message.text.strip()
    if len(PIN) == 0:
        update.message.reply_text("Ви не ввели пароль. Повторіть спробу")
        return AUTHORIZATION

    global authorized_users
    for user in authorized_users:
        if sender.id == user.telegram_id and int(PIN) == user.PIN:

            # check if user is admin
            if user.admin:
                update.message.reply_text(
                    "Вітаю в системі. Ваша роль: адміністратор."
                )
                reply_keyboard = [['Адміністрування', 'Введення/Пошук інформації'], ['Інструкція', 'Вихід']]
                update.message.reply_text(
                    'Отож, ваші подальші дії',
                    reply_markup=ReplyKeyboardMarkup(
                        reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
                    ),
                )
                active_user.append(sender.id)
                return ADMIN_CHOISE
            else:
                reply_keyboard = \
                    [
                        ['Ввід інформації', 'Пошук інформації'], ['Інструкція', 'Вихід']
                    ]

                # Поштаріца check
                if sender.id == 740945761:
                    with open("Poshtaritsa.png", "rb") as photo:
                        update.message.reply_photo(photo)
                else:
                    update.message.reply_text("Ваша роль: користувач")
                update.message.reply_text(
                    'Виберіть опцію із наявного переліку',
                    reply_markup=ReplyKeyboardMarkup(
                        reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
                    ),
                )
                # parsers.refresh_logs()
                parsers.log_event(f"Користувач {user.first_name} ({user.telegram_id}) здійснив вхід до системи;")
                active_user.append(sender.id)
                return IO_CHOISE
    update.message.reply_text("Автентифікація провалена. Спробуйте ще раз")
    return AUTHORIZATION


# Admin panel
def admin_choise(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    user = update.message.from_user
    if text == 'Адміністрування':
        reply_keyboard = reply_keyboard = [
            ['Додавання користувача', 'Видалення користувача'],
            ['Вивантаження БД', 'Вивантаження логів'],
            ['Назад до адмін-меню', 'Вихід']
        ]
        update.message.reply_text(
            'Отож, ваші подальші дії',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return ADMIN_PANEL

    elif text == "Інструкція":
        update.message.reply_text("Інструкція із використання бота")
        filename = "instructions/Iнструкцiя iз використання телеграм бота для адміністратора.pdf"
        with open(filename, "rb") as document:
            update.message.reply_document(document)
        reply_keyboard = [['Продовжити роботу'], ['Вихід']]
        update.message.reply_text(
            'Виберіть одну із опцій',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return CONTINUE

    elif text == "Введення/Пошук інформації":
        reply_keyboard = \
            [
                ['Ввід інформації', 'Пошук інформації'], ['Назад до адмін-меню', 'Вихід']
            ]
        update.message.reply_text(
            'Виберіть опцію із наявного переліку',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return IO_CHOISE

    else:
        if "/start" not in text and 'Вихід' not in text and '/cancel' not in text:
            update.message.reply_text("Щось ліве. Давай заново")
            reply_keyboard = [['Адміністрування', 'Введення/Пошук інформації', 'Вихід']]
            update.message.reply_text(
                'Отож, ваші подальші дії',
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, input_field_placeholder='Здійсніть вибір...'
                ),
            )
            return ADMIN_CHOISE


def admin_panel(update: Update, context: CallbackContext) -> int:
    global authorized_users
    text = update.message.text

    if "Додавання користувача" in text:
        reply_keyboard = [["Назад до адмін-панелі"]]
        update.message.reply_text("Надішліть контакт користувача Телеграм прямо сюди",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                    resize_keyboard=True, one_time_keyboard=True,
                                                    input_field_placeholder="Надішліть контакт або поверніться назад")
        )
        return USER_ADDING

    elif "Видалення користувача" in text:
        reply_text = ""
        reply_keyboard = [["Назад до адмін-панелі"]]
        for index in range(len(authorized_users)):
            reply_text += f"{index+1}.{authorized_users[index].username}:{authorized_users[index].PIN}"
            if index != len(authorized_users) - 1:
                reply_text += '\n'
        update.message.reply_text("Список наявних користувачів"+'\n'+ reply_text)
        update.message.reply_text("Введіть PIN користувача для його видалення", reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                    resize_keyboard=True, one_time_keyboard=True,
                                                    input_field_placeholder="Надішліть контакт або поверніться назад"))
        return USER_DELETING

    elif text == "Вивантаження логів":
        # parsers.refresh_logs()

        # Вибір завантажуваних логів
        reply_keyboard = [["Лог дій користувачів", "Лог бота"]]
        update.message.reply_text("Виберіть тип логу, який необхідно вивантажити",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return LOG_CHOICE
        logfile = "bot.log"
        with open(logfile, "rb") as document:
            update.message.reply_document(document)
        reply_keyboard = [['Продовжити роботу'], ['Вихід']]
        update.message.reply_text(
            'Виберіть одну із опцій',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                input_field_placeholder='Здійсніть вибір...'
            ),
        )

    elif "Вивантаження БД" in text:
        global settings
        mega = Mega()
        m = mega.login(settings["MEGA_LOGIN"], settings["MEGA_PASSWD"])
        file = m.upload("osint_database.db")
        update.message.reply_text(f"Посилання на БД: {m.get_upload_link(file)}")
        reply_keyboard = [['Адміністрування', 'Введення/Пошук інформації', 'Вихід']]
        update.message.reply_text("Виберіть подальшу дію",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                        resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return ADMIN_CHOISE


def user_adding(update: Update, context: CallbackContext) -> int:
    user = update.message.contact
    print(user)
    global authorized_users

    pin_list = [usr.PIN for usr in authorized_users]

    # PIN generation
    while True:
        PIN = random.randint(1001, 9999)
        if PIN not in pin_list:
            break

    # appending user to the list
    authorized_users.append(User(user.first_name, PIN, user.user_id, False))
    parsers.users_write(authorized_users)
    reply_keyboard = [['Додавання користувача', 'Видалення користувача'], ['Вивантаження БД'], ['Назад до адмін-меню', 'Вихід']]
    update.message.reply_text(f" Користувача {user.first_name} із телеграм ІД  " +
                              f"{user.user_id} було додано до списку користувачів. Його PIN: {PIN}",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
        ),
    )
    return ADMIN_CHOISE


def user_deleting(update: Update, context: CallbackContext) -> int:
    global authorized_users
    msg = update.message.text
    PIN = int(msg)
    for user in authorized_users:
        if PIN == user.PIN:
            update.message.reply_text(f"Користувача {user.username}({user.telegram_id}) із PIN {user.PIN} було видалено.")
            authorized_users.pop(authorized_users.index(user))
            parsers.users_write(authorized_users)
    reply_keyboard = [['Додавання користувача', 'Видалення користувача'], ['Вивантаження БД'], ['Назад до адмін-меню', 'Вихід']]
    update.message.reply_text("Ваші подальші дії",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
        ),
    )
    return ADMIN_CHOISE


def log_choice(update: Update, context: CallbackContext) -> int:

    msg = update.message.text
    filename = ""

    if msg in "Лог дій користувачів":
        filename = "userlog.txt"

    elif msg in "Лог бота":
        filename = "bot.log"


    # Sending log to administrator
    with open(filename, "rb") as document:
        update.message.reply_document(document)

    # Flushing bot.log if bot logging was chosen
    if filename == "bot.log":
        with open(filename, "w", encoding="utf-8") as file:
            file.write("")

    reply_keyboard = [['Продовжити роботу'], ['Вихід']]
    update.message.reply_text(
        'Виберіть одну із опцій',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
            input_field_placeholder='Здійсніть вибір...'
        ),
    )
    return CONTINUE


# common user functionality
def main_menu(update: Update, context: CallbackContext):
    user = update.message.from_user
    reply_keyboard = \
    [
        ['Ввід інформації', 'Пошук інформації'],
        ['Вихід']
    ]
    if user.id in [usr.telegram_id for usr in authorized_users if usr.admin]:
        reply_keyboard.insert(2, ["Назад до адмін-меню"])
    update.message.reply_text(
        'Виберіть опцію із наявного переліку',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Здійсніть вибір...'
        ),
    )
    return IO_CHOISE


def io_choise(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user


    if update.message.text == "Інструкція":
        update.message.reply_text("Інструкція із використання бота")
        filename = "instructions/Iнструкцiя iз використання телеграм бота.pdf"
        with open(filename, "rb") as document:
            update.message.reply_document(document)
        reply_keyboard = [['Продовжити роботу'], ['Вихід']]
        update.message.reply_text(
            'Виберіть одну із опцій',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return CONTINUE
    elif update.message.text in 'Ввід інформації':

        reply_keyboard = [['Вручну', 'У вигляді файлу'], ['У вигляді зображення', 'У вигляді посилання'], ["Назад до вибору режиму"], ["Вихід"]]
        update.message.reply_text(
            'Виберіть режим введення даних',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return INSERTION_MODE

    else:
        reply_keyboard = [
            ['ПІБ', 'Адреса', 'Телефон'],
            ['Місце роботи/служби', 'Посада/Звання', 'ІНПН'],
            ['Пошук особи за фотографією'],
            ['Назад до вибору режиму'], ["Вихід"]
        ]
        update.message.reply_text(
            'Оберіть необхідний критерій',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return GET_PARAMETER


def insertion_mode(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user


    if 'посилання' in update.message.text:
        reply_keyboard = [["Назад до вводу"]]
        update.message.reply_text("Надішліть посилання на файл, що зберігається на файлообміннику MEGA",
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return LINK_INSERTION

    if 'Вручну' in update.message.text:
        user_data = print_info()

        # data_erase before entering info

        full_name = None
        birthday = None
        address = None
        works_name = None
        military_position = None
        telephone_number = None
        email_post = None
        social_network = None
        pasport_info = None
        seria_pasport = None
        personal_id = None

        if len(user_data) < 1:
            update.message.reply_text("Здійсніть введення даних")
        else:
            update.message.reply_text(f"Наступні дані будуть занесені до БД:\n{user_data}")

        reply_keyboard = [['1', '2', '3', '4'], ['5', '6', '7', '8'], ['9', '10', '11', '0'], ["Назад до вводу"]]

        # text for choosing
        choise_msg = "0. Занести дані до БД\n"
        for i in range(1, len(parsers.csv_header) + 1):
            choise_msg += f"{str(i)}. {parsers.csv_header[i - 1]}"
            if i != len(parsers.csv_header):
                choise_msg += "\n"

        update.message.reply_text(
            'Оберіть необхідний критерій:\n' + choise_msg,
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return INFO_CONFIRMATION

    elif 'У вигляді файлу' in update.message.text:
        update.message.reply_text(
f"""
Активовано режим надсилання файлів.
Наразі доступна обробка наступних типів:
{parsers.available_formats()}
            """,
            reply_markup=ReplyKeyboardRemove()
    )
        update.message.reply_text(
f'''
Перед надсиланням файлів просимо перевірити наявність заголовків.
Перелік припустимих заголовків:
{parsers.available_headers()}
'''
    )
        reply_keyboard=[["Назад до вводу"]]
        update.message.reply_text("Надішліть файл",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                   resize_keyboard=True)
                                  )
        return FILE_INSERTION

    elif 'зображення' in update.message.text:
        reply_keyboard = [["Назад до вводу"]]
        update.message.reply_text("Надішліть фотографію у нестисненому виді",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                   resize_keyboard=True)
                                  )
        return PHOTO_INSERTION


def file_insertion(update: Update, context: CallbackContext) -> int:
    try:
        flag = False

        # using database engine
        global session

        user = update.message.from_user
        file = context.bot.get_file(update.message.document).download()
        msg = parse_file(file)
        update.message.reply_text(msg)
        reply_keyboard = [['Продовжити роботу'], ['Вихід']]
        update.message.reply_text(
                'Виберіть одну із опцій',
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                    input_field_placeholder='Здійсніть вибір...'),
        )
        return CONTINUE
    except Exception as e:
        update.message.reply_text(error_msg)
        parsers.log_event(e, bot_log)

# functions for getting info from the database
def get_parameter(update: Update, context: CallbackContext) -> int:
    global parameter
    parameter = update.message.text
    if "фотографією" in parameter:
        update.message.reply_text("Надішліть сюди стиснену фотографію")
        global photo_search_flag
        photo_search_flag = True
        return PHOTO_INSERTION
    else:
        update.message.reply_text("Введіть необхідне значення")
    return GET_INFO


def get_info(update: Update, context: CallbackContext) -> int:
    global session
    global parameter
    value = update.message.text
    user = update.message.from_user

    # getting data from database
    data = parsers.get_info_by_parameter(parameter, value, session)

    if type(data) == str:
        update.message.reply_text(data)

    elif type(data) == list:
        global settings
        bot = Bot(settings["TOKEN"])
        filename = "Результати пошуку.xlsx"
        parsers.write_xlsx(filename, data)
        update.message.reply_text("Знайдена інформація поміщена в документ через велику кількість даних.")
        with open(filename, "rb") as document:
            update.message.reply_document(document)

    reply_keyboard = [['Продовжити роботу'], ['Вихід']]
    update.message.reply_text(
            'Виберіть одну із опцій',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
        ),
    )
    return CONTINUE


# OCR
def photo_insertion(update: Update, context: CallbackContext) -> int:
    try:
        file = update.message.photo[-1].file_id
        obj = context.bot.get_file(file)
        imgname = obj.file_path.split('/')[len(obj.file_path.split('/')) - 1]
        obj.download()

        global photo_search_flag


        if photo_search_flag:
            solution = S4f.photo_search(imgname)
            os.system(f"del {imgname}")
            update.message.reply_text(solution)
            solution = ""
            reply_keyboard = [['Продовжити роботу'], ['Вихід']]
            update.message.reply_text(
                'Виберіть одну із опцій',
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                    input_field_placeholder='Здійсніть вибір...'
                ),
            )
            photo_search_flag = False
            return CONTINUE

        else:
            imgname = obj.file_path.split('/')[len(obj.file_path.split('/')) - 1]

            update.message.reply_text("Зображення отримане, зачейкайте...")

            ocr.file_name(imgname)
            data = ocr.full_info
            os.system(f"del {imgname}")
            print(f"<{data}>")
            global full_name
            global birthday
            global address
            global pasport_info
            surname = str(data['Surname']).capitalize() if 'Surname' in data.keys() else ""
            name = str(data['Name']).capitalize() if 'Name' in data.keys() else ""
            patronymic = str(data['Patronymic']).capitalize() if 'Patronymic' in data.keys() else ""
            full_name = f"{surname} {name} {patronymic}"
            birthday = data['Born'] if 'Born' in data.keys() else None
            address = data['Place'] if 'Place' in data.keys() else None
            pasport_info = data['Passport'] if 'Passport' in data.keys() else None
            update.message.reply_text(f"Наступні дані будуть занесені до БД:\n{print_info()}")
            reply_keyboard = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ['10', '11', '0']]

            # text for choosing
            choise_msg = "0. Занести дані до БД\n"
            for i in range(1, len(parsers.csv_header)+1):
                choise_msg += f"{str(i)}. {parsers.csv_header[i-1]}"
                if i != len(parsers.csv_header):
                    choise_msg += "\n"

            update.message.reply_text(
                'Оберіть необхідний критерій:\n' + choise_msg,
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, input_field_placeholder='Здійсніть вибір...'
                ),
            )
            return INFO_CONFIRMATION
    except Exception as e:
        parsers.log_event(e, bot_log)
        update.message.reply_text(error_msg)


def info_confirmation(update: Update, callback: CallbackContext) -> int:
    try:
        text = update.message.text
        user = update.message.from_user
        if text == '0':
            send_db()
            update.message.reply_text("Дані були занесені до БД.")
            global db_record
            # parsers.refresh_logs()
            parsers.log_event(f"Користувач {user.first_name} ({user.id}) заніс до БД наступні дані: {db_record};")
            db_record = []
            reply_keyboard = [['Продовжити роботу'], ['Вихід']]
            update.message.reply_text(
                'Виберіть одну із опцій',
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
                ),
            )
            return CONTINUE
        else:
            global param
            param = text
            update.message.reply_text("Введіть значення параметру")
            return INFO_CORRECTION
    except Exception as e:
        update.message.reply_text(error_msg)
        parsers.log_event(e, bot_log)


def info_correction(update: Update, callback: CallbackContext) -> int:
    text = update.message.text
    global param
    correction_parameter_choose(param, text)
    update.message.reply_text(f"Наступні дані будуть занесені до БД:\n{print_info()}")
    reply_keyboard = [['1', '2', '3'], ['4', '5', '6'], ['7', '8', '9'], ['10', '11', '0']]

    # text for choosing
    choise_msg = "0. Занести дані до БД\n"
    for i in range(1, len(parsers.csv_header) + 1):
        choise_msg += f"{str(i)}. {parsers.csv_header[i - 1]}"
        if i != len(parsers.csv_header):
            choise_msg += "\n"

    update.message.reply_text(
        'Оберіть необхідний критерій:\n' + choise_msg,
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Здійсніть вибір...'
        ),
    )
    return INFO_CONFIRMATION


def correction_parameter_choose(param: str, value: str):
    global full_name, birthday, address, works_name, military_position, telephone_number, email_post, social_network
    global pasport_info, seria_pasport, personal_id
    if param == "1":  # "ПІБ"
        full_name = value
    elif param == "2":  # "ДН"
        birthday = value
    elif param == "3":  # "АДРЕСА"
        address = value
    elif param == "4":  # "МІСЦЕ РОБОТИ/СЛУЖБИ"
        works_name = value
    elif param == "5":  # "ПОСАДА/ЗВАННЯ"
        military_position = value
    elif param == "6":  # "ТЕЛ"
        telephone_number = value
    elif param == "7":  # "ЕЛ.ПОШТА"
        email_post = value
    elif param == "8":  # "СОЦМЕРЕЖІ"
        social_network = value
    elif param == "9":  # "ПАСПОРТ"
        pasport_info = value
    elif param == "10":  # "СЕРІЯ"
        seria_pasport = value
    elif param == "11":  # "ІД"
        personal_id = value



# downloading file from cloud storages
def download_file(update: Update, context: CallbackContext) -> int:

    try:
        url = update.message.text

        mega = Mega()
        m = mega.login()
        m.download_url(url, dest_path="downloads")
        files_list = os.listdir('downloads')
        file = "downloads/" + files_list[len(files_list)-1]
        msg = parse_file(file)
        os.system(f"DEL {file}")
        update.message.reply_text(msg)
        reply_keyboard = [['Продовжити роботу'], ['Вихід']]
        update.message.reply_text(
            'Виберіть одну із опцій',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return CONTINUE
    except Exception as e:
        parsers.log_event(e, bot_log)
        update.message.reply_text(error_msg)


def send_db():
    global session
    data = [[
        full_name,
        parsers.try_parsing_date(birthday),
        address,
        works_name,
        military_position,
        telephone_number,
        email_post,
        social_network,
        pasport_info,
        seria_pasport,
        personal_id
    ]]
    global db_record
    db_record = data[0]
    for element in data:
        print(f"<{element}>")
    flag = parsers.to_database(data, session)
    return flag



def continue_operating(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    if admin(user.id):
        reply_keyboard = [['Адміністрування', 'Введення/Пошук інформації', 'Вихід']]
        update.message.reply_text(
            'Отож, ваші подальші дії',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return ADMIN_CHOISE
    else:
        reply_keyboard = \
            [
                ['Ввід інформації', 'Пошук інформації', 'Вихід']
            ]
        update.message.reply_text(
            'Виберіть опцію із наявного переліку',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return IO_CHOISE


# fallback_functions
def return_to_input_choiсe(update: Update, context: CallbackContext) -> int:
    sender = update.message.from_user
    if sender.id not in user_iDs:
        update.message.reply_text("тобі юзати бота нізя, піздуй нахуй")
    elif sender.id not in active_user:
        update.message.reply_text("Ви не авторизовані в системі. Почніть авторизацію із командою /start")

    else:
        reply_keyboard = [
            ['Вручну', 'У вигляді файлу'],
            ['У вигляді зображення', 'У вигляді посилання'],
            ['Назад до вибору вводу/виводу']
        ]
        update.message.reply_text(
            'Виберіть режим введення даних',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return INSERTION_MODE


def return_to_io_choice(update: Update, context: CallbackContext) -> int:
    sender = update.message.from_user
    if sender.id not in user_iDs:
        update.message.reply_text("тобі юзати бота нізя, піздуй нахуй")
    elif sender.id not in active_user:
        update.message.reply_text("Ви не авторизовані в системі. Почніть авторизацію із командою /start")
    else:
        reply_keyboard = \
            [
                ['Ввід інформації', 'Пошук інформації'], ['Вихід']
            ]
        update.message.reply_text(
            'Виберіть опцію із наявного переліку',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return IO_CHOISE


def return_to_admin_panel(update: Update, context: CallbackContext) -> int:
    sender = update.message.from_user
    if sender.id not in user_iDs:
        update.message.reply_text("тобі юзати бота нізя, піздуй нахуй")
    elif sender.id not in active_user:
        update.message.reply_text("Ви не авторизовані в системі. Почніть авторизацію із командою /start")
    elif sender.id not in [user.telegram_id for user in authorized_users if user.admin]:
        update.message.reply_text("Дана опція доступна лише адміністратору системи")
        reply_keyboard = \
            [
                ['Ввід інформації', 'Пошук інформації'], ['Вихід']
            ]
        update.message.reply_text(
            'Виберіть опцію із наявного переліку',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return IO_CHOISE
    else:
        reply_keyboard = reply_keyboard = [
            ['Додавання користувача', 'Видалення користувача'],
            ['Вивантаження БД', 'Вивантаження логів'],
            ['Назад до адмін-меню', 'Вихід']
        ]
        update.message.reply_text(
            'Отож, ваші подальші дії',
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                input_field_placeholder='Здійсніть вибір...'
            ),
        )
        active_user.append(sender.id)
        return ADMIN_PANEL


def return_to_admin_choice(update: Update, context: CallbackContext) -> int:
    try:
        sender = update.message.from_user
        if sender.id not in user_iDs:
            update.message.reply_text("тобі юзати бота нізя, піздуй нахуй")
        elif sender.id not in active_user:
            update.message.reply_text("Ви не авторизовані в системі. Почніть авторизацію із командою /start")
        elif sender.id not in [user.telegram_id for user in authorized_users if user.admin]:
            update.message.reply_text("Дана опція доступна лише адміністратору системи")
            reply_keyboard = \
                [
                    ['Ввід інформації', 'Пошук інформації'], ['Вихід']
                ]
            update.message.reply_text(
                'Виберіть опцію із наявного переліку',
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                    input_field_placeholder='Здійсніть вибір...'
                ),
            )
            return IO_CHOISE
        else:
            reply_keyboard = [['Адміністрування', 'Введення/Пошук інформації'], ['Вихід']]
            update.message.reply_text(
                'Отож, ваші подальші дії',
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                    input_field_placeholder='Здійсніть вибір...'
                ),
            )
            active_user.append(sender.id)
            return ADMIN_CHOISE
    except Exception as e:
        update.message.reply_text(error_msg)
        parsers.log_event(e, bot_log)

def main() -> None:

    # loading database
    global session
    global engine
    engine = create_engine('sqlite:///osint_database.db', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # reading settings.json
    global settings
    with open(FILENAME, "r", encoding="utf-8") as file:
        data = json.load(file)
        settings = data[0]

    # initialization of bot
    updater = Updater(settings["TOKEN"])
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            # authorization handler
            AUTHORIZATION: [MessageHandler(filters=Filters.regex("[0-9]{4}"), callback=authorization)],

            # Admin pannel
            ADMIN_CHOISE: [MessageHandler(filters=Filters.regex('Адміністрування|Введення/Пошук інформації|Інструкція'),
                                          callback=admin_choise)],
            ADMIN_PANEL: [MessageHandler(filters=Filters.regex(r'Додавання користувача|Видалення користувача|Вивантаження БД|Вивантаження логів'),
                                         callback=admin_panel)],
            USER_ADDING: [MessageHandler(filters=Filters.contact, callback=user_adding)],
            USER_DELETING: [MessageHandler(filters=Filters.regex("[0-9]{4}"), callback=user_deleting)],
            LOG_CHOICE: [MessageHandler(filters=Filters.regex("Лог дій користувачів|Лог бота"), callback=log_choice)],

            # User pannel
            MAIN_MENU: [MessageHandler(filters=Filters.regex('^(?!.*(Вихід|Продовжити роботу))'), callback=main_menu)],
            IO_CHOISE: [MessageHandler(filters=Filters.regex(choise_regex), callback=io_choise)],

            # Insertion of information
            INSERTION_MODE: [MessageHandler(filters=Filters.regex('Вручну|У вигляді файлу|У вигляді зображення|У вигляді посилання'),
                                            callback=insertion_mode)],

            # MEGA Link insertion
            LINK_INSERTION: [MessageHandler(filters=Filters.regex(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"),
                                            callback=download_file)],

            # File insertion
            FILE_INSERTION: [MessageHandler(Filters.document, callback=file_insertion)],

            # OCR
            PHOTO_INSERTION: [MessageHandler(Filters.photo, callback=photo_insertion)],
            INFO_CONFIRMATION: [MessageHandler(Filters.regex(r"[0-9]{1}|1[0-1]{1}"), callback=info_confirmation)],
            INFO_CORRECTION: [MessageHandler(Filters.regex(r""), callback=info_correction)],

            # Info search
            GET_PARAMETER: [MessageHandler(filters=Filters.regex(output_regex), callback=get_parameter)],
            GET_INFO: [MessageHandler(filters=Filters.regex('^(?!.*(Вихід|Продовжити роботу))'), callback=get_info)],


            CONTINUE: [MessageHandler(filters=Filters.regex('Продовжити роботу'), callback=continue_operating)],

        },
        fallbacks=[CommandHandler('cancel', cancel), MessageHandler(filters=Filters.regex('Вихід'), callback=cancel),
                   MessageHandler(Filters.regex("Назад до вводу"), callback=return_to_input_choiсe),
                   MessageHandler(Filters.regex("Назад до вибору режиму"), callback=return_to_io_choice),
                   MessageHandler(Filters.regex("Назад до адмін-меню"), callback=return_to_admin_choice),
                   MessageHandler(Filters.regex("Назад до адмін-панелі"), callback=return_to_admin_panel)]
    )

    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()