from __future__ import print_function
import argparse
import logging

from ruamel import yaml
from kinto_http import cli_utils

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

    # dump sub-command.
    subparser = subparsers.add_parser('dump')
    subparser.set_defaults(which='dump')
    cli_utils.add_parser_options(subparser)
    subparser.add_argument('--full',
                           help='Full output',
                           action='store_true')

    # Parse CLI args.
    args = parser.parse_args()
    cli_utils.setup_logger(logger, args)
    kinto_logger = logging.getLogger('kinto_http')
    cli_utils.setup_logger(kinto_logger, args)

    logger.debug("Instantiate Kinto client.")
    client = cli_utils.create_client_from_args(args)

    # Run chosen subcommand.
    if args.which == 'dump':
        logger.debug("Start %sintrospection..." % ("full " if args.full else ""))
        result = introspect_server(client, bucket=args.bucket, collection=args.collection,
                                   full=args.full)
        yaml_result = yaml.safe_dump(result, default_flow_style=False)
        print(yaml_result, end=u'')

    elif args.which == 'load':
        logger.debug("Start initialization...")
        logger.info("Load YAML file {!r}".format(args.filepath))
        with open(args.filepath, 'r') as f:
            config = yaml.safe_load(f)
            initialize_server(client, config, bucket=args.bucket, collection=args.collection,
                              force=args.force)
