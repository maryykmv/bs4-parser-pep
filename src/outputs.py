import csv
import datetime as dt
import logging

from prettytable import PrettyTable

from constants import (
    BASE_DIR, DATETIME_FORMAT, CODE_PAGES, OUTPUT_PRETTY, OUTPUT_FILE, RESULTS_DIR, DEFAULT_OUTPUT
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
    parser_mode = cli_args.mode
    now_formatted = dt.datetime.now().strftime(DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = results_dir / file_name
    with open(file_path, 'w', encoding=CODE_PAGES) as file:
        writer = csv.writer(file, dialect='unix')
        writer.writerows(results)
    message = DOWNLOAD_RESULT.format(path=file_path)
    logging.info(message)
