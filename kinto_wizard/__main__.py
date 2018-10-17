from __future__ import print_function
import asyncio
from concurrent.futures import ThreadPoolExecutor
import argparse
import logging

from ruamel import yaml
from kinto_http import cli_utils

from .async_kinto import AsyncKintoClient
from .logger import logger
from .kinto2yaml import introspect_server
from .yaml2kinto import initialize_server


def main():
    parser = argparse.ArgumentParser(description="Wizard to setup Kinto with YAML")
    subparsers = parser.add_subparsers(title='subcommand',
                                       description='Load/Dump',
                                       dest='subcommand',
                                       help="Choose and run with --help")
    subparsers.required = True

    # load sub-command.
    subparser = subparsers.add_parser('load')
    subparser.set_defaults(which='load')
    cli_utils.add_parser_options(subparser)
    subparser.add_argument(dest='filepath', help='YAML file')
    subparser.add_argument('--force',
                           help='Load the file using the CLIENT_WINS conflict resolution strategy',
                           action='store_true')
    subparser.add_argument('--dry-run',
                           help="Do not apply write call to the server",
                           action='store_true')
    subparser.add_argument('--delete-records',
                           help='Delete records that are not in the file.',
                           action='store_true')

    # dump sub-command.
    subparser = subparsers.add_parser('dump')
    subparser.set_defaults(which='dump')
    cli_utils.add_parser_options(subparser)
    subparser.add_argument('--full',
                           help='Full output (same as with both --data and --records options)',
                           action='store_true')
    subparser.add_argument('--data',
                           help='Export buckets, collections and groups data',
                           action='store_true')
    subparser.add_argument('--records',
                           help="Export collections' records",
                           action='store_true')

    # Parse CLI args.
    args = parser.parse_args()
    cli_utils.setup_logger(logger, args)
    kinto_logger = logging.getLogger('kinto_http')
    cli_utils.setup_logger(kinto_logger, args)

    logger.debug("Instantiate Kinto client.")
    client = cli_utils.create_client_from_args(args)

    thread_pool = ThreadPoolExecutor()
    event_loop = asyncio.get_event_loop()
    async_client = AsyncKintoClient(client, event_loop, thread_pool,
                                    dry_run=getattr(args, 'dry_run', False))

    # Run chosen subcommand.
    if args.which == 'dump':
        if args.full:
            data = True
            records = True
        else:
            data = args.data
            records = args.records

        logger.debug("Start introspection with %s%s%s..." % ("data" if data else "",
                                                             " and " if data and records else "",
                                                             "records" if records else ""))
        result = event_loop.run_until_complete(
            introspect_server(async_client, bucket=args.bucket, collection=args.collection,
                              data=data, records=records)
        )
        yaml_result = yaml.safe_dump(result, default_flow_style=False)
        print(yaml_result, end=u'')

    elif args.which == 'load':
        logger.debug("Start initialization...")
        logger.info("Load YAML file {!r}".format(args.filepath))
        with open(args.filepath, 'r') as f:
            config = yaml.safe_load(f)
            event_loop.run_until_complete(
                initialize_server(
                    async_client,
                    config,
                    bucket=args.bucket,
                    collection=args.collection,
                    force=args.force,
                    delete_missing_records=args.delete_records
                )
            )
