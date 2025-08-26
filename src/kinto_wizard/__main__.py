from __future__ import print_function

import argparse
import asyncio
import logging
import sys

from kinto_http import AsyncClient, cli_utils
from ruamel.yaml import YAML

from .kinto2yaml import introspect_server
from .logger import logger
from .validate import validate_export
from .yaml2kinto import initialize_server


async def execute():
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
    subparser.add_argument(
        "--attachments", help="Load attachments from specified folder", default=None
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
    subparser.add_argument(
        "--attachments", help="Export collections' attachments to specified folder", default=None
    )

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
    # TODO: add cli_utils.create_async_client_from_args(args)
    async_client = AsyncClient(
        server_url=args.server,
        auth=args.auth,
        bucket=getattr(args, "bucket", None),
        collection=getattr(args, "collection", None),
        retry=args.retry,
        retry_after=args.retry_after,
        dry_mode=getattr(args, "dry_run", False),
        ignore_batch_4xx=args.ignore_batch_4xx,
    )

    # Run chosen subcommand.
    if args.which == "dump":
        if args.full:
            data = True
            records = True
            attachments = args.attachments or "__attachments__"
        else:
            data = args.data
            records = args.records
            attachments = args.attachments

        logger.debug(
            "Start introspection with %s...",
            " and ".join(
                filter(
                    None,
                    [
                        "data" if data else None,
                        "records" if records else None,
                        "attachments" if attachments else None,
                    ],
                )
            ),
        )

        result = await introspect_server(
            async_client,
            bucket=args.bucket,
            collection=args.collection,
            data=data,
            records=records,
            attachments=attachments,
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
        await initialize_server(
            async_client,
            config,
            bucket=args.bucket,
            collection=args.collection,
            force=args.force,
            delete_missing_records=args.delete_records,
            attachments=args.attachments,
        )


def main():
    asyncio.run(execute())
