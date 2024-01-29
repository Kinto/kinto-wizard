from __future__ import print_function

import argparse
import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor

from kinto_http import cli_utils
from ruamel.yaml import YAML

from .async_kinto import AsyncKintoClient
from .kinto2yaml import introspect_server
from .logger import logger
from .validate import validate_export
from .yaml2kinto import initialize_server


def main():
    parser = argparse.ArgumentParser(description="Wizard to setup Kinto with YAML")
    subparsers = parser.add_subparsers(
        title="subcommand",
        description="Load/Dump/Validate",
        dest="subcommand",
        help="Choose and run with --help",
    )
    subparsers.required = True

    # load sub-command.
    subparser = subparsers.add_parser("load")
    subparser.set_defaults(which="load")
    cli_utils.add_parser_options(subparser)
    subparser.add_argument(dest="filepath", help="YAML file")
    subparser.add_argument(
        "--force",
        help="Load the file using the CLIENT_WINS conflict resolution strategy",
        action="store_true",
    )
    subparser.add_argument(
        "--dry-run", help="Do not apply write call to the server", action="store_true"
    )
    subparser.add_argument(
        "--delete-records", help="Delete records that are not in the file.", action="store_true"
    )

    # dump sub-command.
    subparser = subparsers.add_parser("dump")
    subparser.set_defaults(which="dump")
    cli_utils.add_parser_options(subparser)
    subparser.add_argument(
        "--full",
        help="Full output (same as with both --data and --records options)",
        action="store_true",
    )
    subparser.add_argument(
        "--data", help="Export buckets, collections and groups data", action="store_true"
    )
    subparser.add_argument("--records", help="Export collections' records", action="store_true")

    # validate sub-command.
    subparser = subparsers.add_parser("validate")
    subparser.set_defaults(which="validate")
    subparser.set_defaults(verbosity=logging.INFO)
    subparser.add_argument(dest="filepath", help="YAML file to validate")
    cli_utils.add_parser_options(subparser)

    # Parse CLI args.
    args = parser.parse_args()
    cli_utils.setup_logger(logger, args)
    kinto_logger = logging.getLogger("kinto_http")
    cli_utils.setup_logger(kinto_logger, args)

    if args.which == "validate":
        logger.debug("Start validation...")
        logger.info("Load YAML file {!r}".format(args.filepath))
        yaml = YAML(typ="safe")
        with open(args.filepath, "r") as f:
            config = yaml.load(f)
        logger.info("File loaded!")
        fine = validate_export(config)
        sys.exit(0 if fine else 1)

    logger.debug("Instantiate Kinto client.")
    client = cli_utils.create_client_from_args(args)

    thread_pool = ThreadPoolExecutor()
    event_loop = asyncio.get_event_loop()
    async_client = AsyncKintoClient(
        client, event_loop, thread_pool, dry_run=getattr(args, "dry_run", False)
    )

    # Run chosen subcommand.
    if args.which == "dump":
        if args.full:
            data = True
            records = True
        else:
            data = args.data
            records = args.records

        logger.debug(
            "Start introspection with %s%s%s..."
            % (
                "data" if data else "",
                " and " if data and records else "",
                "records" if records else "",
            )
        )
        result = event_loop.run_until_complete(
            introspect_server(
                async_client,
                bucket=args.bucket,
                collection=args.collection,
                data=data,
                records=records,
            )
        )
        yaml = YAML()
        yaml.default_flow_style = False
        yaml.dump(result, sys.stdout)

    elif args.which == "load":
        logger.debug("Start initialization...")
        logger.info("Load YAML file {!r}".format(args.filepath))
        yaml = YAML(typ="safe")
        with open(args.filepath, "r") as f:
            config = yaml.load(f)
        event_loop.run_until_complete(
            initialize_server(
                async_client,
                config,
                bucket=args.bucket,
                collection=args.collection,
                force=args.force,
                delete_missing_records=args.delete_records,
            )
        )
