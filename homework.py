import logging
import os
import time
import sys
from logging import StreamHandler
from http import HTTPStatus

import requests
import telegram
from telegram import TelegramError
from dotenv import load_dotenv

import exceptions


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.debug(f'Сообщение отправленно: {message}')
    except TelegramError as error:
        logger.error(f'Не удалось отправить сообщение {error}')
        raise exceptions.ErrorSendingMessage(
            f'Не удалось отправить сообщение {error}')


def get_api_answer(current_timestamp):
    """Получить статус домашней работы."""
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': current_timestamp},
    }
    try:
        responce = requests.get(**params_request)
        if responce.status_code != HTTPStatus.OK:
            raise Exception('Ошибка статуса')
        return responce.json()

    except Exception:
        raise exceptions.EmptyAPIResponseError(
            'Не верный код ответа параметры запроса: url = {url},'
            'headers = {headers},'
            'params = {params}'.format(**params_request))


def check_response(response):
    """Проверить валидность ответа."""
    logging.debug('Начало проверки')
    if not isinstance(response, dict):
        raise TypeError(f'Ошибка в типе ответа API:{response}')
    if 'homeworks' not in response:
        raise KeyError('Ключ homeworks отсутствует')
    if 'current_date' not in response:
        raise KeyError('Ключ current_date отсутствует')

    homework_list = response.get('homeworks')
    if not isinstance(homework_list, list):
        raise TypeError('Homeworks не является списком')

    return homework_list


def parse_status(homework):
    """Распарсить ответ."""
    if 'homework_name' not in homework:
        raise KeyError('Ключ homework_name отсутствует')

    if 'status' not in homework:
        raise KeyError('Ключ homework_status отсутствует')

    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if homework_status not in HOMEWORK_VERDICTS:
        message = f'Неизвестный статус домашней работы: {homework_status}'
        raise ValueError(message)
    verdict = HOMEWORK_VERDICTS[homework_status]
    logger.info('Вердикт обновлен')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    if not check_tokens():
        logger.critical('Токен(ы) отсутствует(ют)')
        sys.exit()

    first_message = ''

    while True:

        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            message = parse_status(homeworks[0])
            if first_message != message:
                send_message(bot, message)
                first_message = message
                current_timestamp = int(time.time())
            else:
                logger.info('домашек нет')

        except exceptions.ErrorSendingMessage as error:
            message = f'Сбой в работе Telegram: {error}'
            logger.error(message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if first_message != message:
                logger.error(message)
                send_message(bot, message)
                first_message = message
            else:
                logging.error(f'Повторяющееся сообщение: {message}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=(
            '%(asctime)s, %(levelname)s, Путь - %(pathname)s, '
            'Файл - %(filename)s, Функция - %(funcName)s, '
            'Номер строки - %(lineno)d, %(message)s'
        ),
        handlers=[logging.FileHandler('log.txt', encoding='UTF-8'),
                  logging.StreamHandler(sys.stdout)])
    main()
