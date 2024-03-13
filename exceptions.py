class ErrorSendingMessage(Exception):
    """Ошибка. Не отправляется сообщение."""

    pass


class EmptyAPIResponseError(Exception):
    """Ошибка. Неправильный ответ API."""

    pass


class TelegramError(Exception):
    """Ошибка. Сбой в работе Telegram."""

    pass
