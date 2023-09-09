import logging

from bs4 import BeautifulSoup
from requests import RequestException

from constants import CODE_PAGES
from exceptions import ParserFindTagException

ERROR_PAGE = 'Возникла ошибка при загрузке страницы {url}'
ERROR_TAG = 'Не найден тег {tag} {attrs}'


def get_response(session, url):
    try:
        response = session.get(url)
        response.encoding = CODE_PAGES
        return response
    except RequestException:
        message = ERROR_PAGE.format(url=url)
        logging.exception(message, stack_info=True)


def get_soup(session, url):
    try:
        response = session.get(url)
        response.encoding = CODE_PAGES
        if response is None:
            return
        soup = BeautifulSoup(response.text, 'lxml')
        return soup
    except RequestException:
        message = ERROR_PAGE.format(url=url)
        logging.exception(message, stack_info=True)


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        message = ERROR_TAG.format(tag=tag, attrs=attrs)
        logging.error(message, stack_info=True)
        raise ParserFindTagException(message)
    return searched_tag
