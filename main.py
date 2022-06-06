import pandas as pd
import re
import parsers
import apiS4F as S4f
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    run_async
)
import random
from parsers import User
from ocr import ocr
import os
from mega import Mega
import json
from database_operations import db_ops


FILENAME = "settings.json"

# list of necessary variables
authorized_users = []
settings = {}
created_user = None
created_user_admin_flag = False
created_user_parameter = None

tablegroups_path = "database_operations/tablegroups.json"
table_groups = db_ops.read_tablegroups(tablegroups_path)

# Database necessary variables

db_record = []

# for authentication checkIn

user_iDs = []
active_user = []  # list of users, that are operating in bot

# regular expressions for handlers
choise_regex = 'Ввід інформації|Пошук інформації|Інструкція'
command_regex = ['Вручну', 'У вигляді файлу']
output_regex = "Пошук у базі бота|Пошук особи за фотографією|Вихід"
error_msg = "Сталась помилка під час використання бота. Радимо натиснути /cancel та почати роботу заново. Просимо вибачення за помилку"
bot_log = "bot.log"


# Handler constants
ADMIN_PANEL, ADMIN_CHOISE, AUTHORIZATION, MAIN_MENU, IO_CHOISE, INSERTION_MODE, FILE_INSERTION,  GET_PARAMETER, \
    GET_INFO, USER_ADDING, USER_DELETING, INSTRUCTION, TELEPHONE, UPLOAD_TO_MEGA, \
    CONTINUE, PHOTO_INSERTION, LINK_INSERTION, LOG_CHOICE, \
    USER_INFO_CONFIRMATION, USER_INFO_CORRECTION, S4F_TOKEN_INSERTION, TABLE_GROUP_SELECTION, \
    TABLE_GROUP_STRUCTURE, APPEND_CHOICE, PARAMETER_CONFIRMATION, PARAMETER_CORRECTION, TABLE_GROUP_INPUT_SELECTION = range(27)


# bot functions
def return_user(telegram_id) -> parsers.User:
    for user in authorized_users:
        if telegram_id == user.telegram_id:
            return user


@run_async
def parse_file(file: str, table_group_name: str, append_choise=True):
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
            parsers.parser(file, table_group_name, append_choice=append_choise)
            flag = True
    if file:
        os.system(f"rm {file}")
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
                if sender.id == 740945761 or "Поштаріца" in f"{sender.first_name} {sender.last_name}":
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
                parsers.log_event(f"Користувач {user.username} ({user.telegram_id}) здійснив вхід до системи;")
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
            ['Вивантаження БД', 'Вивантаження логів', 'Перевірка токена S4F'],
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
    global settings
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
        reply_keyboard = [['Адміністрування', 'Введення/Пошук інформації'], ['Вихід']]
        update.message.reply_text("Виберіть подальшу дію",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                        resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
            ),
        )
        return ADMIN_CHOISE

    elif "Перевірка токена S4F" in text:


        response = S4f.api_s4f_check(settings["apiUrl"], settings["apiKey"])
        err = "Токен не є дійсним"
        try:
            if int(response["remaining"]) <= 0:
                err = "Кількість можливих спроб є вичерпаною"
                raise Exception(err)

            reply_keyboard = [
                ['Додавання користувача', 'Видалення користувача'],
                ['Вивантаження БД', 'Вивантаження логів', 'Перевірка токена S4F'],
                ['Назад до адмін-меню', 'Вихід']
            ]
            update.message.reply_text(
                f"Кількість доступних пошуків: {response['remaining']}",
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                    input_field_placeholder='Здійсніть вибір...'
                ),
            )
            return ADMIN_PANEL
        except Exception as e:
            update.message.reply_text(f"{err}. Введіть його значення")
            return S4F_TOKEN_INSERTION


def user_adding(update: Update, context: CallbackContext) -> int:
    sended_contact = update.message.contact
    # print(created_user)
    global authorized_users

    pin_list = [usr.PIN for usr in authorized_users]

    # PIN generation
    while True:
        PIN = random.randint(1001, 9999)
        if PIN not in pin_list:
            break

    global created_user
    global created_user_admin_flag
    created_user = User(f"{sended_contact.first_name} {sended_contact.last_name}",
                        PIN, sended_contact.user_id, created_user_admin_flag)

    reply_keyboard = [
        ['Занести користувача до бази'],
        ["Ім'я користувача", "PIN", "Телеграм ID", "Роль"],
        ['Назад до адмін-меню', 'Вихід']]
    update.message.reply_text(f"""Із надісланого контакту вдалось отримати наступну інформацію:
1. Ім'я користувача: {created_user.username};
2. PIN користувача: {created_user.PIN};
3. Телеграм ID користувача: {created_user.telegram_id};
4. Роль користувача: {"Адміністратор" if created_user_admin_flag else "Користувач"}""",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
        ),
    )
    return USER_INFO_CONFIRMATION


def user_info_confirmation(update: Update, context: CallbackContext) -> int:

    # getting parameter
    global created_user
    choice = update.message.text

    if choice == 'Занести користувача до бази':
        error_flag = False
        if created_user is None:
            update.message.reply_text("Неможливо внести порожнього користувача")
        elif (not created_user.username) or (not created_user.telegram_id):
            error_flag = True
            update.message.reply_text(
                f"""Неможливо занести до бази користувача без наявного {"ПІБ" if created_user.telegram_id else "телеграм ID"}.
Здійсніть коригування даних або поверніться у попереднє меню""")


        if error_flag:
            reply_keyboard = [['1', '2', '3', '4'], ['Назад до адмін-меню', 'Вихід']]
            update.message.reply_text(f"""1. Ім'я користувача: {created_user.username};
2. PIN користувача: {created_user.PIN};
3. Телеграм ID користувача: {created_user.telegram_id};
4. Роль користувача: {"Адміністратор" if created_user_admin_flag else "Користувач"}""",
                                           reply_markup=ReplyKeyboardMarkup(
                                              reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                                               input_field_placeholder='Здійсніть вибір...'
                                         )
                                )

        else:
            authorized_users.append(created_user)
            parsers.config_write(authorized_users, "allowed_users.json")
            reply_keyboard = [
            ['Додавання користувача', 'Видалення користувача'],
            ['Вивантаження БД', 'Вивантаження логів', 'Перевірка токена S4F'],
            ['Назад до адмін-меню', 'Вихід']
        ]
            update.message.reply_text(f""" Користувача {created_user.username} із телеграм ІД \
{created_user.telegram_id} було додано до списку користувачів. Його PIN: {created_user.PIN}""",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
        ),
    )
            created_user = None
            return ADMIN_PANEL

    else:

        global created_user_parameter
        created_user_parameter = choice
        update.message.reply_text("Введіть значення параметру")
        if choice == "Роль":
            reply_keyboard = [["Адміністратор"], ["Користувач"]]
            update.message.reply_text("Виберіть значення параметра за допомогою клавіатури",
                                      reply_markup=ReplyKeyboardMarkup(
                                          reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                                          input_field_placeholder='Здійсніть вибір...'
                                      )
                                      )
        return USER_INFO_CORRECTION


def user_info_correction(update: Update, context: CallbackContext) -> int:

    parameter_value = update.message.text
    global created_user_parameter
    global created_user

    if created_user_parameter == "Ім'я користувача":
        created_user.username = parameter_value

    elif created_user_parameter == "PIN":

        if not (str(parameter_value).isdigit()):
            error_flag = True
            update.message.reply_text("PIN невірну форму(наявні нецифрові символи). Внесіть значення заново")
            return USER_INFO_CORRECTION
        else:
            created_user.PIN = int(parameter_value)

    elif created_user_parameter == "Телеграм ID":

        if not(str(parameter_value).isdigit()):
            error_flag = True
            update.message.reply_text("Телеграм ID має невірну форму(наявні нецифрові символи). Внесіть значення заново")
            return USER_INFO_CORRECTION

        else:
            created_user.telegram_id = int(parameter_value)

    elif created_user_parameter == "Роль":
        created_user.admin = True if parameter_value == "Адміністратор" else False

    reply_keyboard = [
        ['Занести користувача до бази'],
        ["Ім'я користувача", "PIN", "Телеграм ID", "Роль"],
        ['Назад до адмін-меню', 'Вихід']]
    update.message.reply_text(f"""Із надісланого контакту вдалось отримати наступну інформацію:
    1. Ім'я користувача: {created_user.username};
    2. PIN користувача: {created_user.PIN};
    3. Телеграм ID користувача: {created_user.telegram_id};
    4. Роль користувача: {"Адміністратор" if created_user.admin else "Користувач"}""",
                              reply_markup=ReplyKeyboardMarkup(
                                  reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                                  input_field_placeholder='Здійсніть вибір...'
                              ),
                              )
    return USER_INFO_CONFIRMATION


def user_deleting(update: Update, context: CallbackContext) -> int:
    global authorized_users
    msg = update.message.text
    PIN = msg
    if PIN.isdigit():
        for user in authorized_users:
            if int(PIN) == user.PIN:
                update.message.reply_text(f"Користувача {user.username}({user.telegram_id}) із PIN {user.PIN} було видалено.")
                authorized_users.pop(authorized_users.index(user))
                parsers.config_write(authorized_users, "allowed_users.json")
    reply_keyboard = [
            ['Додавання користувача', 'Видалення користувача'],
            ['Вивантаження БД', 'Вивантаження логів', 'Перевірка токена S4F'],
            ['Назад до адмін-меню', 'Вихід']
        ]
    update.message.reply_text("Ваші подальші дії",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder='Здійсніть вибір...'
        ),
    )
    return ADMIN_PANEL


def log_choice(update: Update, context: CallbackContext) -> int:

    msg = update.message.text
    filename = ""

    if msg in "Лог дій користувачів":
        filename = "userlog.txt"

    elif msg in "Лог бота":
        filename = "bot.log"


    # Sending log to administrator
    try:
        with open(filename, "rb") as document:
            update.message.reply_document(document)
        if filename == "bot.log":
            with open(filename, "w", encoding="utf-8") as file:
                file.write("")
    except Exception as e:
        update.message.reply_text("Обраний лог є порожнім, отож його завантаження є неможливим")

    # Flushing bot.log if bot logging was chosen


    reply_keyboard = [['Продовжити роботу'], ['Вихід']]
    update.message.reply_text(
        'Виберіть одну із опцій',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
            input_field_placeholder='Здійсніть вибір...'
        ),
    )
    return CONTINUE


def s4f_token_insertion(update: Update, context: CallbackContext) -> int:
    settings["apiKey"] = update.message.text
    parsers.config_write([settings], "settings.json")
    reply_keyboard = [['Продовжити роботу'], ['Вихід']]
    update.message.reply_text(
        'Токен успішно змінено. Виберіть одну із опцій',
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
            ['Пошук у базі бота'],
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
    global table_groups
    user = return_user(update.message.from_user.id)
    param = update.message.text

    if 'Вручну' in param:

        # print(table_groups)
        if table_groups:
            return_msg = ""
            if table_groups:
                for key, index in zip(table_groups.keys(), range(len(table_groups))):
                    return_msg += f"{index + 1}. {key};\n"
            reply_keyboard = [["Назад до вибору режиму"]]
            update.message.reply_text(f"""
На даний момент часу існують наступні групи:
{return_msg} Введіть цифру необхідної групи для додавання інформації.""",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True))

            return TABLE_GROUP_INPUT_SELECTION

    elif 'У вигляді файлу' == param or 'У вигляді посилання' == param:
        user.input_choice = param
        update.message.reply_text(
f"""
Наразі доступна обробка наступних типів:
{parsers.available_formats()}
            """,
            reply_markup=ReplyKeyboardRemove()
    )
        reply_keyboard = [["До нової групи"]]

        if table_groups:
            reply_keyboard.append(["До існуючої групи"])

        reply_keyboard.append(["Назад до вводу"])
        update.message.reply_text("Додати дані до",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                   resize_keyboard=True)
                                  )
        return TABLE_GROUP_SELECTION

    elif 'зображення' in param:
        reply_keyboard = [["Назад до вводу"]]
        update.message.reply_text("Надішліть фотографію у нестисненому виді",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                   resize_keyboard=True)
                                  )
        return PHOTO_INSERTION


def table_group_selection(update: Update, context: CallbackContext):
    msg = update.message.text
    global table_groups
    # print(table_groups)
    if table_groups and msg == "До існуючої групи":

        return_msg = ""

        for key, index in zip(table_groups.keys(), range(len(table_groups))):
            return_msg += f"{index+1}. {key};\n"

        reply_keyboard = [["Назад до вибору режиму"]]
        update.message.reply_text(
            f"""
На даний момент часу існують наступні групи:
{return_msg} Введіть цифру необхідної групи для надсилання файлу.""",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,resize_keyboard=True))

    elif msg == "До нової групи":
        reply_keyboard = [["Назад до вибору режиму"]]
        update.message.reply_text("Введіть назву групи", reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                   resize_keyboard=True))

    return TABLE_GROUP_STRUCTURE


def table_group_structure(update: Update, context: CallbackContext):


    global table_groups

    message = update.message.text
    user = return_user(update.message.from_user.id)
    tables_list = list(table_groups.keys())
    try:

        if not re.match(r"\w", message) and not re.match(r"[0-9]{1-50}", message):
            update.message.reply_text("Введено неприпустиму назву таблиці. Повторіть введення знову")
            return TABLE_GROUP_STRUCTURE

        elif message.isdigit():
            user.table_group_name = tables_list[int(message)-1]
        else:
            user.table_group_name = message

        fields = db_ops.get_fieldnames_for_tables(user.table_group_name, tablegroups_path)
        reply_keyboard = [["Додати як нову таблицю", "Додати лише дані"], ["Назад до вибору режиму"]]

        if fields is str and user.table_group_name not in tables_list:
            update.message.reply_text("Схоже, що таблиць в цій групі ще немає.")
            table_groups.update({table_group_name: []})
            db_ops.write_tablegroups(table_groups, tablegroups_path)


            update.message.reply_text("Виберіть одну із опцій",
                                          reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                           resize_keyboard=True))
            return APPEND_CHOICE

        else:
            user.pragma = parsers.return_pragma(fields)
            return_msg = parsers.beautify_dict_output(user.pragma)

            update.message.reply_text(f"Наступні заголовки є присутніми для даної групи таблиць:\n"
                                          f"{return_msg}")

        update.message.reply_text("Виберіть одну із опцій",
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                       resize_keyboard=True))
        return APPEND_CHOICE
    except Exception as e:
        update.message.reply_text(error_msg)
        parsers.log_event(e, bot_log)


def table_group_input_selection(update: Update, context: CallbackContext):

    user = return_user(update.message.from_user.id)

    global table_group_name
    message = update.message.text
    print(message)
    tables_list = list(table_groups.keys())
    if message.isdigit():
        table_group_name = tables_list[int(message)-1]
    else:
        table_group_name = message
    fields = db_ops.get_fieldnames_for_tables(table_group_name, tablegroups_path)
    if fields is str or table_group_name not in tables_list:
        update.message.reply_text("Схоже, що таблиць в цій групі ще немає. Зверніться до адміністратора із проханням створити групу")
        table_groups.update({table_group_name: []})
        reply_keyboard = [["Продовжити роботу", "Вихід"]]
        db_ops.write_tablegroups(table_groups, tablegroups_path)
        update.message.reply_text("Виберіть одну із опцій",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                   resize_keyboard=True))
        return CONTINUE

    else:
        user.pragma = parsers.return_pragma(fields)
        return_msg = parsers.beautify_dict_output(user.pragma)

        update.message.reply_text(f"""Наступні заголовки є присутніми для даної групи таблиць:\n{return_msg}
Введіть індекс параметра""")

        reply_keyboard = [["Занести дані до БД"], ["Назад до вибору режиму"]]
        update.message.reply_text("Виберіть параметр, ввівши його номер",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))

        return PARAMETER_CONFIRMATION


def append_choice(update: Update, context: CallbackContext):

    user = return_user(update.message.from_user.id)
    user.append_choice = update.message.text
    reply_keyboard = [["Назад до вибору режиму"]]

    if user.input_choice == "У вигляді файлу":
        update.message.reply_text("Надішліть файл",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                   resize_keyboard=True))
        return FILE_INSERTION
    elif user.input_choice == "У вигляді посилання":
        reply_keyboard = [["Назад до вводу"]]
        update.message.reply_text("Надішліть посилання на файл, що зберігається на файлообміннику MEGA",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                   resize_keyboard=True)
                                  )
        return LINK_INSERTION

@run_async
def file_insertion(update: Update, context: CallbackContext) -> int:
    try:
        flag = False
        user = return_user(update.message.from_user.id)
        append = False
        if user.append_choice == "Додати лише дані":
            append = False
        elif user.append_choice == "Додати як нову таблицю":
            append = True
        file = context.bot.get_file(update.message.document).download()
        msg = parse_file(file, user.table_group_name, append)
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

    user = return_user(update.message.from_user.id)
    user.parameter = update.message.text
    if "фотографією" in user.parameter:
        update.message.reply_text("Надішліть сюди стиснену фотографію")

        user.photo_search_flag = True
        return PHOTO_INSERTION

    else:
        return_msg = ""
        for key, index in zip(table_groups.keys(), range(len(table_groups))):
            return_msg += f"{index + 1}. {key};\n"
        reply_keyboard = [["Здійснити запит", "Назад до вибору режиму"]]
        update.message.reply_text(f"""Введіть цифру необхідної групи таблиць:
{return_msg}""", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
    return GET_INFO


def get_info(update: Update, context: CallbackContext) -> int:

    global table_groups
    user = return_user(update.message.from_user.id)
    tables_list = list(table_groups.keys())
    message = update.message.text

    if message.isdigit():
        user.table_group_name = tables_list[int(message) - 1]
        print(user.table_group_name)

    fields = db_ops.get_fieldnames_for_tables(user.table_group_name, tablegroups_path)
    print(type(fields))

    if fields is str or user.table_group_name not in tables_list:
        print(f"<{table_groups}>")
        update.message.reply_text("Схоже, що таблиць в цій групі ще немає.")
        table_groups.update({table_group_name: []})
        print(f"<{table_groups}>")
        db_ops.write_tablegroups(table_groups, tablegroups_path)
        reply_keyboard = [["Продовжити роботу"], ["Вихід"]]
        update.message.reply_text("Виберіть одну із опцій",
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
                                                                   resize_keyboard=True))
        return CONTINUE

    else:
        user.pragma = parsers.return_pragma(fields)
        return_msg = parsers.beautify_dict_output(user.pragma)
        update.message.reply_text(f"""Наступні заголовки є присутніми для даної групи таблиць:\n{return_msg}
Введіть індекс параметра""")

        return PARAMETER_CONFIRMATION

@run_async
def parameter_confirmation(update: Update, context: CallbackContext):

    user = return_user(update.message.from_user.id)
    global tablegroups_path
    text = update.message.text
    if text == "Здійснити запит":
        try:
            if user.param_dict:
                msg = get_data(tablegroups_path, user)
                if msg == "Результати пошуку.txt":
                    with open(msg, "rb") as document:
                        update.message.reply_document(document)

                else:
                    update.message.reply_text("Параметри не задано. Введіть номер параметру")
                    return PARAMETER_CONFIRMATION

        except Exception as e:
            parsers.log_event(e, bot_log)
            update.message.reply_text(error_msg)

        finally:
            reply_keyboard = [["Продовжити роботу", "Вихід"]]
            update.message.reply_text(
                'Виберіть одну із опцій',
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                    input_field_placeholder='Здійсніть вибір...'
                ),
            )
            return CONTINUE


    elif text == "Занести дані до БД":
        try:
            for key in user.param_dict.keys():
                user.param_dict[key] = [user.param_dict[key]]
            dataframe = pd.DataFrame(user.param_dict)
            print(dataframe)
            msg = db_ops.upload_data(df=dataframe, tablegroup=table_group_name, append_choise=True)
            update.message.reply_text(f"{msg}")
            user.param_dict = {}
        except Exception as e:
            update.message.reply_text(str(e))
        finally:
            reply_keyboard = [["Продовжити роботу", "Вихід"]]
            update.message.reply_text(
                'Виберіть одну із опцій',
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                    input_field_placeholder='Здійсніть вибір...'
                ),
            )
            return CONTINUE

    else:
        if text.isdigit():
            print(user.pragma)
            user.param = user.pragma[int(text)]
            update.message.reply_text("Введіть значення параметру")
            return PARAMETER_CORRECTION


def parameter_correction(update: Update, context: CallbackContext):

    user = return_user(update.message.from_user.id)
    text = update.message.text
    user.param_dict.update({user.param: text})

    update.message.reply_text(f"{parsers.beautify_dict_output(user.param_dict)}")
    update.message.reply_text("Введіть наступну цифру параметра або надішліть дані для пошуку")
    return PARAMETER_CONFIRMATION


# випиляти нахуй
def get_data(path: str, user: parsers.User):

    print(user.param_dict)
    if not user.param_dict:
        return "Список параметрів порожній"

    # getting the first parameter
    parameter = list(user.param_dict.keys())[0]
    value = user.param_dict[parameter]

    user.param_dict.pop(parameter)

    # getting data from database
    data, header = db_ops.get_data_from_db(parameter, value, user.table_group_name, path)
    if user.param_dict:
        for key in user.param_dict:
            for row in list(data):
                if user.param_dict[key] != row[header.index(key)]:
                    data.remove(row)

    # data rectification
    for key in list(header):
        if header.count(key):
            indexes = [n for n, x in enumerate(header) if x == key]
            for index in range(1, len(indexes), -1):
                header.pop(index)
                for row in data:
                    row.pop(index)

    print(f"Data after rectification: {data}")
    if data:
        with open("Результати пошуку.txt", "w", encoding="utf-8") as file:
            file.write("Результати пошуку:\n")
            for row in data:
                for key in header:
                    if row[header.index(key)] and key != 'id':
                        file.write(f"{key}: {row[header.index(key)]}\n")
                file.write("\n")

        return "Результати пошуку.txt"
    else:
        return "За даним запитом нічого не було знайдено"


# OCR
@run_async
def photo_insertion(update: Update, context: CallbackContext) -> int:
    user = return_user(update.message.from_user.id)
    try:
        file = update.message.photo[-1].file_id
        obj = context.bot.get_file(file)
        imgname = obj.file_path.split('/')[len(obj.file_path.split('/')) - 1]
        obj.download()
        global settings

        if user.photo_search_flag:
            print(settings["apiUrl"], settings["apiKey"])
            solution = S4f.photo_search(imgname, settings["apiUrl"], settings["apiKey"])
            os.system(f"rm {imgname}")
            update.message.reply_text(solution)
            reply_keyboard = [['Продовжити роботу'], ['Вихід']]
            update.message.reply_text(
                'Виберіть одну із опцій',
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard, one_time_keyboard=True, resize_keyboard=True,
                    input_field_placeholder='Здійсніть вибір...'
                ),
            )
            user.photo_search_flag = False
            return CONTINUE

        else:

            imgname = obj.file_path.split('/')[len(obj.file_path.split('/')) - 1]
            update.message.reply_text("Зображення отримане, зачейкайте...")

            ocr.file_name(imgname)
            data = ocr.full_info
            user.param_dict = ocr.results_to_parameters_dict(data)
            os.system(f"rm {imgname}")
            update.message.reply_text(f"За допомогою OCR було отримано наступні дані:\n"
                                      f"{parsers.beautify_dict_output(user.param_dict)}")

            fields = db_ops.get_fieldnames_for_tables("Інформація про користувачів", tablegroups_path)
            print(type(fields))
            user.pragma = parsers.return_pragma(fields)
            return_msg = parsers.beautify_dict_output(user.pragma)
            update.message.reply_text(f"Нижче перераховано поля, які є можливим змінити:\n"
                                      f"{return_msg}")

            reply_keyboard = [["Занести дані до БД", "Назад до вибору режиму"]]

            update.message.reply_text(f"Введіть індекс параметра",
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
            return PARAMETER_CONFIRMATION

    except Exception as e:
        parsers.log_event(e, bot_log)
        update.message.reply_text(error_msg)


# downloading file from cloud storages
@run_async
def download_file(update: Update, context: CallbackContext) -> int:

    try:
        url = update.message.text
        #
        mega = Mega()
        m = mega.login()
        m.download_url(url, dest_path="downloads")
        files_list = os.listdir('downloads')
        file = "downloads/" + files_list[len(files_list)-1]
        # msg = parse_file(file)
        os.system(f"rm {file}")
        flag = False
        user = return_user(update.message.from_user.id)
        append = False
        if user.append_choice == "Додати лише дані":
            append = False
        elif user.append_choice == "Додати як нову таблицю":
            append = True
        msg = parse_file(file, user.table_group_name, append)
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
        parsers.log_event(e, bot_log)
        update.message.reply_text(error_msg)


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
            ['Назад до вибору режиму']
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

    # прописати адміна сука

    if sender.id not in user_iDs:
        update.message.reply_text("тобі юзати бота нізя, піздуй нахуй")
    elif sender.id not in active_user:
        update.message.reply_text("Ви не авторизовані в системі. Почніть авторизацію із командою /start")
    else:
        reply_keyboard = \
            [
                ['Ввід інформації', 'Пошук інформації'], ['Вихід']
            ]
        if admin(sender.id):
            reply_keyboard.append(["Назад до адмін-меню"])

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
            ['Вивантаження БД', 'Вивантаження логів', 'Перевірка токена S4F'],
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

    # sending info to users
    global authorized_users
    authorized_users = parsers.parse_users()

    for user in authorized_users:
        os.system("")
    # reading settings.json
    global settings
    with open(FILENAME, "r", encoding="utf-8") as file:
        data = json.load(file)
        settings = data[0]

    # initialization of bot
    updater = Updater(settings["TOKEN"])
    dispatcher = updater.dispatcher
    for user in authorized_users:
        os.system(f'wget "https://api.telegram.org/bot{settings["TOKEN"]}/sendMessage?chat_id={user.telegram_id}&text=%D0%91%D0%BE%D1%82%D0%B0%20%D0%B7%D0%B0%D0%BF%D1%83%D1%89%D0%B5%D0%BD%D0%BE.%20%D0%9D%D0%B0%D1%82%D0%B8%D1%81%D0%BD%D1%96%D1%81%D1%82%D1%8C%20/start%20%D0%B4%D0%BB%D1%8F%20%D0%BF%D0%BE%D1%87%D0%B0%D1%82%D0%BA%D1%83%20%D1%80%D0%BE%D0%B1%D0%BE%D1%82%D0%B8"')
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
        # authorization handler
            AUTHORIZATION: [MessageHandler(filters=Filters.regex("[0-9]{4}"), callback=authorization)],

        # Admin panel
            ADMIN_CHOISE: [MessageHandler(filters=Filters.regex('Адміністрування|Введення/Пошук інформації|Інструкція'),
                                          callback=admin_choise)],
            ADMIN_PANEL: [MessageHandler(filters=Filters.regex(
                r'Додавання користувача|Видалення користувача|Вивантаження БД|Вивантаження логів|Перевірка токена S4F'),
                                         callback=admin_panel)],

            # user list manipulations
            USER_ADDING: [MessageHandler(filters=Filters.contact, callback=user_adding)],
            USER_INFO_CONFIRMATION: [MessageHandler(filters=Filters.regex(
                "Занести користувача до бази|Ім'я користувача|PIN|Телеграм ID|Роль"
            ), callback=user_info_confirmation)],
            USER_INFO_CORRECTION: [MessageHandler(filters=Filters.regex('^(?!.*(Вихід|Продовжити роботу))'),
                                                  callback=user_info_correction)],
            USER_DELETING: [MessageHandler(filters=Filters.regex("[0-9]{0,50}"), callback=user_deleting)],
            LOG_CHOICE: [MessageHandler(filters=Filters.regex("Лог дій користувачів|Лог бота"), callback=log_choice)],
            S4F_TOKEN_INSERTION: [MessageHandler(filters=Filters.regex('^(?!.*(Вихід|Продовжити роботу))'),
                                                 callback=s4f_token_insertion)],


        # User pannel
            MAIN_MENU: [MessageHandler(filters=Filters.regex('^(?!.*(Вихід|Продовжити роботу))'), callback=main_menu)],
            IO_CHOISE: [MessageHandler(filters=Filters.regex(choise_regex), callback=io_choise)],

            # Insertion of information
            INSERTION_MODE: [MessageHandler(filters=Filters.regex('Вручну|У вигляді файлу|У вигляді зображення|У вигляді посилання'),
                                            callback=insertion_mode)],
            TABLE_GROUP_SELECTION: [MessageHandler(filters=Filters.regex("До нової групи|До існуючої групи"),
                                            callback=table_group_selection)],
            TABLE_GROUP_STRUCTURE: [MessageHandler(filters=Filters.regex('^(?!.*(Вихід|Продовжити роботу|Назад до вибору режиму))'),
                                                   callback=table_group_structure)],
            APPEND_CHOICE: [MessageHandler(filters=Filters.regex('Додати як нову таблицю|Додати лише дані'),
                                            callback=append_choice)],

            # MEGA Link insertion
            LINK_INSERTION: [MessageHandler(filters=Filters.regex(r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"),
                                            callback=download_file)],

            # File insertion
            FILE_INSERTION: [MessageHandler(Filters.document, callback=file_insertion)],

            # OCR
            PHOTO_INSERTION: [MessageHandler(Filters.photo, callback=photo_insertion)],
            GET_PARAMETER: [MessageHandler(filters=Filters.regex(output_regex), callback=get_parameter)],
            TABLE_GROUP_INPUT_SELECTION: [MessageHandler(filters=Filters.regex("[0-9]{1,2}"),
                                            callback=table_group_input_selection)],

            GET_INFO: [MessageHandler(filters=Filters.regex('^(?!.*(Вихід|Продовжити роботу|Назад до вибору режиму))'), callback=get_info)],

            PARAMETER_CONFIRMATION: [MessageHandler(filters=Filters.regex('^(?!.*(Вихід|Продовжити роботу|Назад до вибору режиму))'),
                                                    callback=parameter_confirmation)],
            PARAMETER_CORRECTION: [MessageHandler(filters=Filters.regex('^(?!.*(Вихід|Продовжити роботу|Назад до вибору режиму))'),
                                                  callback=parameter_correction)],

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
