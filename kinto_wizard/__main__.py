import argparse
import logging

import ruamel.yaml
from kinto_http import cli_utils
from kinto_http import exceptions as kinto_exceptions


logger = logging.getLogger(__name__)


def initialize_server(client, filepath):
    logger.info("Load YAML file {!r}".format(filepath))


def introspect_server(client):
    logger.info("Fetch buckets list.")
    buckets = client.get_buckets()
    return {
        bucket['id']: introspect_bucket(client, bucket['id'])
        for bucket in buckets
    }


def introspect_bucket(client, bid):
    logger.info("Fetch information of bucket {!r}".format(bid))
    try:
        bucket = client.get_bucket(bucket=bid)
    except kinto_exceptions.BucketNotFound:
        logger.error("Could not read bucket {!r}".format(bid))
        return None

    permissions = bucket.get('permissions', {})
    if 'write' not in permissions:
        error_msg = 'Could not read permissions of bucket {!r}'.format(bid)
        raise kinto_exceptions.KintoException(error_msg)

    collections = client.get_collections(bucket=bid)
    groups = client.get_groups(bucket=bid)
    return {
        'permissions': permissions,
        'collections': {
            collection['id']: introspect_collection(client, bid, collection['id'])
            for collection in collections
        },
        'groups': {
            group['id']: introspect_group(client, bid, group['id'])
            for group in groups
        }
    }


def introspect_collection(client, bid, cid):
    logger.info("Fetch information of collection {!r}/{!r}".format(bid, cid))
    collection = client.get_collection(bucket=bid, collection=cid)
    return {
        'permissions': collection['permissions'],
    }


def introspect_group(client, bid, gid):
    logger.info("Fetch information of group {!r}/{!r}".format(bid, gid))
    group = client.get_group(bucket=bid, group=gid)
    return {
        'data': {'members': group['data']['members']},
        'permissions': group['permissions']
    }


def main():
    parser = argparse.ArgumentParser(description="Wizard to setup Kinto with YAML")
    subparsers = parser.add_subparsers(title='subcommand',
                                       description='Load/Dump',
                                       dest='subcommand',
                                       help="Choose and run with --help")
    subparsers.required = True
    for command in ('load', 'dump'):
        subparser = subparsers.add_parser(command)
        subparser.set_defaults(which=command)

        cli_utils.add_parser_options(subparser,
                                     include_bucket=False,
                                     include_collection=False)

        if command == 'load':
            subparser.add_argument(dest='filepath', help='YAML file')

    args = parser.parse_args()
    cli_utils.setup_logger(logger, args)

    logger.debug("Instantiate Kinto client.")
    client = cli_utils.create_client_from_args(args)

    if args.which == 'dump':
        logger.debug("Start introspection...")
        result = introspect_server(client)
        print(ruamel.yaml.safe_dump(result, default_flow_style=False))

    elif args.which == 'load':
        logger.debug("Start initialization...")
        initialize_server(client, args.filepath)


if __name__ == "__main__":
    main()
