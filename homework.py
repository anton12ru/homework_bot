from http import HTTPStatus
import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

from exceptions import HWStatusRaise

load_dotenv()


PRACTICUM_TOKEN = os.getenv('ya_token')
TELEGRAM_TOKEN = os.getenv('tg_token')
TELEGRAM_CHAT_ID = os.getenv('chat_id')

SECRET_TOKENS = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    format=(
        '%(asctime)s - %(name)s - %(levelname)s -'
        '%(message)s - %(funcName)s - %(lineno)d'
    ),
    level=logging.DEBUG,
    filename='main.log',
    encoding='UTF-8',
    filemode='a',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправляет сообщение."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logging.info(f'отправлено сообщение: "{message}"')


def get_api_answer(current_timestamp):
    """Извлекаем информацию из Эндпоинта API сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        message = f'Ошибка при запросе к основному API: {error}'
        logging.error(message)
        raise IndexError(message)
    if response.status_code != HTTPStatus.OK:
        message = f'код запроса API не равен {HTTPStatus.OK}'
        logging.error(message)
        raise Exception(message)
    return response.json()


def check_response(response):
    """Проверяет запрос API на корректность работы.
    возвращая список домашних работ.
    """
    try:
        homework = response['homeworks']
    except KeyError:
        logger.error('Не найден ключ "homeworks"')
        raise KeyError('Не найден ключ "homeworks"')
    if not isinstance(homework, list):
        message = 'Ответ от API не может быть списком'
        logging.error(message)
        raise TypeError(message)
    try:
        homework = homework[0]
    except IndexError:
        message = 'На проверке нет домашней работы'
        logging.error(message)
        raise IndexError(message)
    return homework


def parse_status(homework):
    """Функция извлекает из информации о конкретной домашней работе.
    статус этой работы.
    """
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')
    if homework_status not in HOMEWORK_STATUSES:
        message = f'ключ {homework_status} не найден'
        logging.error(message)
        raise HWStatusRaise(f'ключ {homework_status} не найден')
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяем доступность переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        logger.critical(
            'Проверить наличие переменных окружения в .env'
        )
        raise Exception('Проверить наличие переменных окружения в .env')

    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response['current_date']
            homework = check_response(response)
            if homework:
                parse_status_result = parse_status(homework)
                send_message(bot, parse_status_result)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = str(error)
            logger.error(message)
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            time.sleep(RETRY_TIME)
            raise Exception(message)


if __name__ == '__main__':
    main()
