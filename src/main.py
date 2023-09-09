import logging
import re
from collections import Counter
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, MAIN_DOC_URL, PEP_DOC_URL, EXPECTED_STATUS, ERROR_MESSAGE
from outputs import control_output
from utils import get_response, find_tag


def whats_new(session):
    # Вместо константы WHATS_NEW_URL, используйте переменную whats_new_url.
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
# Загрузка веб-страницы с кешированием.
    response = session.get(whats_new_url)
    response.encoding = 'utf-8'
    # print(response.text)
    soup = BeautifulSoup(response.text, 'lxml')
    # Шаг 1-й: поиск в "супе" тега section с нужным id. Парсеру нужен только
    # первый элемент, поэтому используется метод find().
    # main_div = soup.find('section', attrs={'id': 'what-s-new-in-python'})
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})

    # Шаг 2-й: поиск внутри main_div следующего тега div с
    # классом toctree-wrapper.
    # Здесь тоже нужен только первый элемент, используется метод find().
    # div_with_ul = main_div.find('div', attrs={'class': 'toctree-wrapper'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})

    # Шаг 3-й: поиск внутри div_with_ul всех элементов списка
    # li с классом toctree-l1.
    # Нужны все теги, поэтому используется метод find_all().
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )

    # Печать найденных элементов.
    # results = []
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        # response = session.get(version_link)
        # response.encoding = 'utf-8'
        response = get_response(session, version_link)
        # Если страница не загрузится, программа перейдёт к следующей ссылке
        if response is None:
            continue
        soup = BeautifulSoup(response.text, 'lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', '')
        results.append((version_link, h1.text, dl_text))
    return results
    # for result in results:
    #     print(*result)


def latest_versions(session):
    # response = session.get(MAIN_DOC_URL)
    # response.encoding = 'utf-8'
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Ничего не нашлось')
    # results = []
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        # print(a_tag.text)
        text_match = re.search(pattern, a_tag.text)
        # print(text_match)
        if text_match is None:
            version, status = a_tag.text, ''
        else:
            version, status = text_match.groups()
        results.append((link, version, status))
    return results
    # for result in results:
    #     print(*result)


def pep(session):
    response = get_response(session, PEP_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
    a_tags = main_div.find_all('a', attrs={'class': 'pep reference internal'})
    # print(a_tags)
    # print(abbr_tags)
    results = [('Статус', 'Количество')]
    statuses = []
    for a_tag in a_tags:
        link = a_tag['href']
        # print(link)
        pep_url = urljoin(PEP_DOC_URL, link)
        # print(pep_url)
        response = get_response(session, pep_url)
        if response is None:
            return
        soup = BeautifulSoup(response.text, 'lxml')
        abbr_tags = find_tag(soup, 'abbr')
        status = abbr_tags.text
        preview_status = status[0]
        # print(preview_status)
        if status not in EXPECTED_STATUS[preview_status]:
            error_message = ERROR_MESSAGE.format(
                pep_url=pep_url,
                status=status,
                expected_status=EXPECTED_STATUS[preview_status]
            )
            logging.warning(error_message)
        statuses.append(status)
    counter = Counter(statuses)
    # print(counter)
    for status, count in counter.items():
        results.append((status, count))
    return results


def download(session):
    # Вместо константы DOWNLOADS_URL, используйте переменную downloads_url.
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = session.get(downloads_url)
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')
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
    # На запись открывается файл test.txt и ассоциируется
    # с переменной test_file.
    with open('test.txt', 'w') as test_file:
        test_file.write('Hello World!')

    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep
}


def main():
    # Запускаем функцию с конфигурацией логов.
    configure_logging()
    # Отмечаем в логах момент запуска программы.
    logging.info('Парсер запущен!')
    # Конфигурация парсера аргументов командной строки —
    # передача в функцию допустимых вариантов выбора.
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    # Считывание аргументов из командной строки.
    args = arg_parser.parse_args()
    # Логируем переданные аргументы командной строки.
    logging.info(f'Аргументы командной строки: {args}')
    # Создание кеширующей сессии.
    session = requests_cache.CachedSession()
    # Если был передан ключ '--clear-cache', то args.clear_cache == True.
    if args.clear_cache:
        # Очистка кеша.
        session.cache.clear()
    # Получение из аргументов командной строки нужного режима работы.
    parser_mode = args.mode
    # Поиск и вызов нужной функции по ключу словаря.
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)
    # Логируем завершение работы парсера.
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
