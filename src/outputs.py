import csv
import datetime as dt
import logging

from prettytable import PrettyTable

from constants import (
    BASE_DIR, DATETIME_FORMAT, CODE_PAGES, OUTPUT_PRETTY,
    OUTPUT_FILE, DEFAULT_OUTPUT
)

DOWNLOAD_RESULT = 'Файл с результатами был сохранён: {path}'


def control_output(results, cli_args):
    output = cli_args.output
    output_names = [
        [OUTPUT_PRETTY, pretty_output],
        [OUTPUT_FILE, file_output],
        [DEFAULT_OUTPUT, default_output]
    ]
    for output_type, output_function in output_names:
        if output == output_type:
            output_function(results, cli_args)


def default_output(results, cli_args=''):
    for row in results:
        print(*row)


def pretty_output(results, cli_args=''):
    table = PrettyTable()
    table.field_names = results[0]
    table.align = 'l'
    table.add_rows(results[1:])
    print(table)


def file_output(results, cli_args):
    results_dir = BASE_DIR / 'results'
    results_dir.mkdir(exist_ok=True)
    # Не могу изменить на контсанту тесты падают:
    # FAILED tests/test_main.py::test_download -
    # AssertionError: Убедитесь что для хранения архивов с
    # документацией Python в директории `src` создаётся директория `results`
    # RESULTS_DIR.mkdir(exist_ok=True)
    # archive_path = RESULTS_DIR / filename
    parser_mode = cli_args.mode
    # Не могу изменить на контсанту тесты падают: пока
    # сюда дойдет пройдут секунды
    # из-за этого падают тесты
    # E       AssertionError: Убедитесь что имя файла соотвествует
    # паттерну <имя-режима_дата_в_формате_%Y-%m-%d_%H-%M-%S>.csv
    # E         С форматами кодов вы можете познакомиться тут -
    # E https://docs.python.org/3/library/datetime.html?highlight=strftime
    # #strftime-and-strptime-format-codes
    # E assert 'pep_2023-09-10_01-20-27.csv' == 'pep_2023-09-10_01-20-33.csv'
    # E - pep_2023-09-10_01-20-33.csv
    # E ?                      ^^
    # E + pep_2023-09-10_01-20-27.csv
    # E ?
    now_formatted = dt.datetime.now().strftime(DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = results_dir / file_name
    with open(file_path, 'w', encoding=CODE_PAGES) as file:
        writer = csv.writer(file, dialect=csv.unix_dialect)
        writer.writerows(results)
    message = DOWNLOAD_RESULT.format(path=file_path)
    logging.info(message)
