import logging
import re
from collections import Counter
from urllib.parse import urljoin

import requests_cache
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (
    BASE_DIR, MAIN_DOC_URL, PEP_DOC_URL, EXPECTED_STATUS
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

MESSAGE_ERRORS = 'Произошел сбой: {error}'


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = get_soup(session, whats_new_url)
    sections_by_python = soup.select(
        '#what-s-new-in-python div.toctree-wrapper li.toctree-l1'
    )
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        soup = get_soup(session, version_link)
        if soup is None:
            message = CHECK_URL.format(url=version_link)
            logging.exception(message, stack_info=True)
        results.append((
            version_link,
            find_tag(soup, 'h1').text,
            find_tag(soup, 'dl').text.replace('\n', '')
        ))
    return results


def latest_versions(session):
    soup = get_soup(session, MAIN_DOC_URL)
    sidebar = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise KeyError('Ничего не нашлось')
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
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
    main_div = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
    a_tags = main_div.find_all('a', attrs={'class': 'pep reference internal'})
    statuses = []
    for a_tag in tqdm(a_tags):
        link = a_tag['href']
        pep_url = urljoin(PEP_DOC_URL, link)
        soup = get_soup(session, pep_url)
        if soup is None:
            message = CHECK_URL.format(url=pep_url)
            logging.exception(message, stack_info=True)
        abbr_tags = find_tag(soup, 'abbr')
        status = abbr_tags.text
        abbreviation_status = status[0]
        statuses.append(status)
    if status not in EXPECTED_STATUS[abbreviation_status]:
        error_message = ERROR_PEP_STATUS.format(
            pep_url=pep_url,
            status=status,
            expected_status=EXPECTED_STATUS[abbreviation_status]
        )
        logging.warning(error_message)
    counter = Counter(statuses)
    results = [
            ('Статус', 'Количество'),
            *counter.items(),
    ]
    results.append(('Итого:', len(statuses)))
    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    soup = get_soup(session, downloads_url)
    # file_name = re.compile(r'.+pdf-a4\.zip$')
    # pdf_a4_link = soup.select_one(
    # f'div.main table.docutils > [href$={file_name}]'
    # )['href']
    main_div = find_tag(soup, 'div', attrs={'role': 'main'})
    table_tag = find_tag(main_div, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(
        table_tag, 'a', {'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    download_dir = BASE_DIR / 'downloads'
    download_dir.mkdir(exist_ok=True)
    archive_path = download_dir / filename
    # Не могу изменить на контсанту тесты падают:
    # FAILED tests/test_main.py::test_download -
    # AssertionError: Убедитесь что для хранения архивов с
    # документацией Python в директории `src` создаётся директория `downloads`
    # DOWNLOAD_DIR.mkdir(exist_ok=True)
    # archive_path = DOWNLOAD_DIR / filename
    with open('test.txt', 'w') as test_file:
        test_file.write('Hello World!')

    with open(archive_path, 'wb') as file:
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
        logging.info('Парсер запущен!')
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
        logging.info('Парсер завершил работу.')
    except Exception as error:
        message = MESSAGE_ERRORS.format(error=error)
        logging.exception(message)


if __name__ == '__main__':
    main()
