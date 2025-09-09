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
    subparser.add_argument(
        "--full",
        help="Load everything (same as with all --load-... options)",
        action="store_true",
        default=None,
    )
    for resource in ("bucket", "collection", "group", "record"):
        subparser.add_argument(
            f"--{resource}s",
            help=f"Load {resource}s",
            action="store_true",
            dest=f"load_{resource}s",
            default=None,
        )
    subparser.add_argument(
        "--data",
        help="Load attributes",
        action="store_true",
        dest="load_data",
        default=None,
    )
    subparser.add_argument(
        "--permissions",
        help="Load permissions",
        action="store_true",
        dest="load_permissions",
        default=None,
    )

    # dump sub-command.
    subparser = subparsers.add_parser("dump")
    subparser.set_defaults(which="dump")
    cli_utils.add_parser_options(subparser)
    subparser.add_argument(
        "--full",
        help="Full output (same as with --data, --permissions, --collections, --groups and --records options)",
        action="store_true",
    )
    for resource in ("bucket", "collection", "group", "record"):
        subparser.add_argument(
            f"--{resource}s",
            help=f"Export {resource}s",
            action="store_true",
            dest=f"dump_{resource}s",
            default=None,
        )
    subparser.add_argument(
        "--data",
        help="Export buckets, collections and groups data",
        action="store_true",
        default=False,
    )
    subparser.add_argument(
        "--permissions",
        help="Export buckets, collections and groups permissions",
        action="store_true",
        default=False,
    )
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
            records = True
            buckets = True
            collections = True
            groups = True
            attachments = args.attachments or "__attachments__"
            data = True
            permissions = True
        else:
            records = args.dump_records
            buckets = args.dump_buckets
            collections = args.dump_collections
            groups = args.dump_groups
            attachments = args.attachments
            data = args.data
            permissions = args.permissions

        logger.debug(
            "Start introspection with %s...",
            " and ".join(
                filter(
                    None,
                    [
                        "data" if data else None,
                        "permissions" if permissions else None,
                        "collections" if collections else None,
                        "groups" if groups else None,
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
            permissions=permissions,
            buckets=buckets,
            collections=collections,
            groups=groups,
            records=records,
            attachments=attachments,
        )
        yaml = YAML()
        yaml.default_flow_style = False
        yaml.dump(result, sys.stdout)

    elif args.which == "load":
        # If --full is passed or not any --records, etc. specified
        if args.full or not any(
            (args.load_buckets, args.load_collections, args.load_records, args.load_groups)
        ):
            load_buckets = True
            load_collections = True
            load_records = True
            load_groups = True
        else:
            load_buckets = args.load_buckets
            load_collections = args.load_collections
            load_records = args.load_records
            load_groups = args.load_groups
        # If --full is passed or --data and --permissions not specified
        if args.full or (not args.load_data and not args.load_permissions):
            load_data = True
            load_permissions = True
        else:
            load_data = args.load_data
            load_permissions = args.load_permissions

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
            load_buckets=load_buckets,
            load_collections=load_collections,
            load_records=load_records,
            load_groups=load_groups,
            load_data=load_data,
            load_permissions=load_permissions,
        )


def main():
    asyncio.run(execute())
