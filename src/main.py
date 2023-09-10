import logging
import re
from collections import Counter
from urllib.parse import urljoin

import requests_cache
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (
    BASE_DIR, MAIN_DOC_URL, PEP_DOC_URL, EXPECTED_STATUS, DOWNLOAD_DIR,
    MODE_OPEN_DONLOWD
)
from outputs import control_output
from utils import get_response, find_tag, get_soup

ERROR_PEP_STATUS = (
    '\nНесовпадающие статусы:'
    '\n{pep_url}'
    '\nСтатус в карточке:'
    '\n{status}'
    '\nОжидаемые статусы:'
    '\n{expected_status}'
)

CHECK_URL = 'Возникла ошибка при загрузке страницы {url}'
DOWNLOAD_RESULT = 'Архив был загружен и сохранён: {path}'
CMD_ARGS = 'Аргументы командной строки: {args}'
PARSER_START = 'Парсер запущен!'
PARSER_END = 'Парсер завершил работу.'
MESSAGE_ERRORS = 'Произошел сбой: {error}'
NO_RESULTS = 'Ничего не нашлось'
HEADER_WHATS_NEW = ('Ссылка на статью', 'Заголовок', 'Редактор, Автор')
HEADER_LATEST_VERSION = ('Ссылка на документацию', 'Версия', 'Статус')
HEADER_PEP = ('Статус', 'Количество')
PATH_NAME_WHATS_NEW = 'whatsnew/'
PAGE_NAME_DOWNLOAD = 'download.html'


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, PATH_NAME_WHATS_NEW)
    try:
        soup = get_soup(session, whats_new_url)
    except ValueError as error:
        logging.error(CHECK_URL.format(url=whats_new_url, error=error))
    a_tags = soup.select(
        '#what-s-new-in-python div.toctree-wrapper '
        'li.toctree-l1 a[href$=".html"]'
    )
    results = [HEADER_WHATS_NEW]
    for a_tag in tqdm(a_tags):
        version_link = urljoin(whats_new_url, a_tag['href'])
        try:
            soup = get_soup(session, version_link)
        except ValueError as error:
            logging.error(CHECK_URL.format(url=version_link, error=error))
        results.append((
            version_link,
            find_tag(soup, 'h1').text,
            find_tag(soup, 'dl').text.replace('\n', '')
        ))
    return results


def latest_versions(session):
    soup = get_soup(session, MAIN_DOC_URL)
    ul_tags = soup.select('div.sphinxsidebarwrapper ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise ValueError(NO_RESULTS)
    results = [HEADER_LATEST_VERSION]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        text_match = re.search(pattern, a_tag.text)
        if text_match is None:
            version, status = a_tag.text, ''
        else:
            version, status = text_match.groups()
        results.append((a_tag['href'], version, status))
    return results


def pep(session):
    soup = get_soup(session, PEP_DOC_URL)
    a_tags = soup.select(
        '#numerical-index a.pep.reference.internal'
    )
    statuses = []
    messages = []
    for a_tag in tqdm(a_tags):
        link = a_tag['href']
        pep_url = urljoin(PEP_DOC_URL, link)
        try:
            soup = get_soup(session, pep_url)
        except ValueError as error:
            logging.error(CHECK_URL.format(url=pep_url, error=error))
        abbr_tags = find_tag(soup, 'abbr')
        status = abbr_tags.text
        abbreviation_status = status[0]
        statuses.append(status)
        if status not in EXPECTED_STATUS[abbreviation_status]:
            messages.append(ERROR_PEP_STATUS.format(
                pep_url=pep_url,
                status=status,
                expected_status=EXPECTED_STATUS[abbreviation_status]
            ))
    logging.warning(messages)
    counter = Counter(statuses)
    results = [
            (HEADER_PEP),
            *counter.items(),
    ]
    results.append(('Итого:', len(statuses)))
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, PAGE_NAME_DOWNLOAD)
    response = get_response(session, downloads_url)
    soup = get_soup(session, downloads_url)
    pdf_a4_link = soup.select_one(
        'div table.docutils a[href$="a4.zip"]')['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    download_dir = BASE_DIR / DOWNLOAD_DIR
    download_dir.mkdir(exist_ok=True)
    archive_path = download_dir / filename
    with open(archive_path, MODE_OPEN_DONLOWD) as file:
        file.write(response.content)
    message = DOWNLOAD_RESULT.format(path=archive_path)
    logging.info(message)


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep
}


def main():
    try:
        configure_logging()
        logging.info(PARSER_START)
        arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
        args = arg_parser.parse_args()
        message = CMD_ARGS.format(args=args)
        logging.info(message)
        session = requests_cache.CachedSession()
        if args.clear_cache:
            session.cache.clear()
        parser_mode = args.mode
        results = MODE_TO_FUNCTION[parser_mode](session)
        if results is not None:
            control_output(results, args)
        logging.info(PARSER_END)
    except Exception as error:
        logging.exception(MESSAGE_ERRORS.format(error=error))


if __name__ == '__main__':
    main()
