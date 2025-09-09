import asyncio
import itertools
import os

from kinto_http import exceptions as kinto_exceptions

from .logger import logger


MAX_PARALLEL_REQUESTS = 8


def sorted_principals(permissions):
    return {perm: sorted(principals) for perm, principals in sorted(permissions.items())}


async def gather_dict(dct):
    """Utility function to do asyncio.gather for dictionaries

    Do asyncio.gather on the dictionary's values, and return the
    dictionary with the futures' results replacing the futures.

    >>> promise = Future()
    >>> promise.set_result("value")
    >>> await gather_dict({"key": promise})
    {"key": "value"}
    """
    items = dct.items()
    results = await asyncio.gather(*(item[1] for item in items))
    keys_results = zip((item[0] for item in items), results)
    return {k: v for k, v in keys_results if v is not None}


async def introspect_server(
    client,
    bucket=None,
    collection=None,
    data=False,
    permissions=True,
    buckets=True,
    collections=True,
    groups=True,
    records=False,
    attachments=None,
):
    if bucket:
        logger.info("Only inspect bucket `{}`.".format(bucket))
        bucket_info = await introspect_bucket(
            client,
            bucket,
            collection=collection,
            data=data,
            permissions=permissions,
            buckets=buckets,
            collections=collections,
            groups=groups,
            records=records,
            attachments=attachments,
        )
        if bucket_info:
            return {"buckets": {bucket: bucket_info}}
        return {"buckets": {}}

    logger.info("Fetch buckets list.")
    buckets = await client.get_buckets()
    buckets_tree = await gather_dict(
        {
            bucket["id"]: introspect_bucket(
                client,
                bucket["id"],
                collection=collection,
                data=data,
                permissions=permissions,
                buckets=buckets,
                collections=collections,
                groups=groups,
                records=records,
                attachments=attachments,
            )
            for bucket in buckets
        }
    )
    return {"buckets": buckets_tree}


async def introspect_bucket(
    client,
    bid,
    collection=None,
    data=False,
    permissions=True,
    buckets=True,
    collections=True,
    groups=True,
    records=False,
    attachments=None,
):
    logger.info("Fetch information of bucket {!r}".format(bid))
    try:
        bucket = await client.get_bucket(id=bid)
    except kinto_exceptions.BucketNotFound:
        logger.error("Could not read bucket {!r}".format(bid))
        return None

    if collection:
        try:
            result = {
                "collections": {
                    collection: await introspect_collection(
                        client,
                        bid,
                        collection,
                        data=data,
                        permissions=permissions,
                        collections=collections,
                        records=records,
                        attachments=attachments,
                    )
                },
            }
        except kinto_exceptions.CollectionNotFound:
            return None
    else:
        result = {}
        if collections:
            result["collections"] = await gather_dict(
                {
                    collection["id"]: introspect_collection(
                        client,
                        bid,
                        collection["id"],
                        data=data,
                        permissions=permissions,
                        collections=collections,
                        records=records,
                        attachments=attachments,
                    )
                    for collection in (await client.get_collections(bucket=bid))
                }
            )

        if groups:
            result["groups"] = await gather_dict(
                {
                    group["id"]: introspect_group(
                        client, bid, group["id"], data=data, permissions=permissions
                    )
                    for group in (await client.get_groups(bucket=bid))
                }
            )

    if buckets and permissions:
        if len(bucket["permissions"]) == 0:
            logger.warning(
                "⚠️ Could not read permissions of bucket {!r}".format(bid)
            )  # pragma: no cover
        result["permissions"] = sorted_principals(bucket["permissions"])

    if buckets and data:
        result["data"] = bucket["data"]

    return result


async def introspect_collection(
    client,
    bid,
    cid,
    data=False,
    permissions=True,
    collections=True,
    records=False,
    attachments=None,
):
    logger.info("Fetch information of collection {!r}/{!r}".format(bid, cid))
    collection = await client.get_collection(bucket=bid, id=cid)

    result = {}

    if collections and permissions:
        if len(collection["permissions"]) == 0:
            logger.warning(
                "⚠️ Could not read permissions of collection {!r}/{!r}".format(bid, cid)
            )  # pragma: no cover
        result["permissions"] = sorted_principals(collection["permissions"])

    if collections and data:
        result["data"] = collection["data"]

    if records or attachments:
        records = await client.get_records(bucket=bid, collection=cid)
        result["records"] = {
            # XXX: we don't show permissions, until we have a way to fetch records
            # in batch (see Kinto/kinto-http.py#145)
            record["id"]: {"data": record, "permissions": {}} if permissions else {"data": record}
            for record in records
        }

    if attachments:
        futures = [
            client.download_attachment(
                record,
                filepath=os.path.join(attachments, record["attachment"]["location"]),
                save_metadata=True,
            )
            for record in records
            if "attachment" in record
        ]
        if futures:
            logger.info("Dump attachments to %s", attachments)
        chunks = itertools.batched(futures, MAX_PARALLEL_REQUESTS)
        for chunk in chunks:
            await asyncio.gather(*chunk)

    return result


async def introspect_group(client, bid, gid, data=False, permissions=True):
    logger.info("Fetch information of group {!r}/{!r}".format(bid, gid))
    group = await client.get_group(bucket=bid, id=gid)

    result = {}

    if permissions:
        if len(group["permissions"]) == 0:
            logger.warning(
                "⚠️ Could not read permissions of group {!r}/{!r}".format(bid, gid)
            )  # pragma: no cover
        result["permissions"] = sorted_principals(group["permissions"])

    data = group["data"] if data else {}
    data["members"] = group["data"]["members"]
    result["data"] = data

    return result
