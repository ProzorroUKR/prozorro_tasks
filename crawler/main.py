# -*- coding: utf-8 -*-
import argparse

from functools import partial

from prozorro_crawler.main import main

from crawler import resources
from crawler.handlers import data_handler

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Start tasks crawler.'
    )
    choices = resources.configs.choices()
    parser.add_argument(
        'resource',
        type=str,
        choices=choices,
        help=f'resource name'
    )
    args = parser.parse_args()
    config = resources.configs.get(args.resource)
    main(
        partial(data_handler, handlers=config.handlers),
        resource=args.resource,
        opt_fields=config.opt_fields
    )
