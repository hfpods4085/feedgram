#! /usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import asyncio
import os
import sys

import feedparser
from loguru import logger
from videogram.utils import load_json, save_json
from videogram.videogram import sync
from yt_dlp.utils import YoutubeDLError


async def process_single_entry(entry: dict, conf: dict) -> dict:
    res = {"updated": False}
    logger.info(f"Syncing to Telegram: {entry['title']}")
    try:
        await sync(entry["link"], tg_id=conf["tg_target"], sync_audio=False, use_cookie=conf["cookie"])
    except YoutubeDLError as e:
        logger.error(f"Error message: {e.msg}")
        if "年龄" in e.msg or "版权" in e.msg:  # type: ignore
            logger.warning(f"Skip video due to restriction: {entry['title']}")
        elif "直播" in e.msg or "首播" in e.msg:  # type: ignore
            logger.warning(f"Skip video due to not started yet: {entry['title']}")
            return res
        else:
            raise
    res["updated"] = True

    return res


async def main():
    conf = next(x for x in load_json(args.config) if x["id"] == args.id)
    database = f"data/{args.id}.json"
    db: dict = load_json(database)
    if "videos" not in db:
        db["videos"] = []

    # process unfinished feed
    for entry in db["videos"]:
        if entry["finished"]:
            continue
        logger.info(f"Process unfinished video: [{entry['link']}] {entry['title']}")
        res = await process_single_entry(entry, conf)
        if res["updated"]:
            entry["finished"] = True
            save_json(db, database)

    # process new
    database_vids = {x["link"] for x in db["videos"]}
    remote = feedparser.parse(args.url)
    for entry in remote["entries"][::-1]:  # from oldest to latest
        if entry["link"] in database_vids:
            logger.debug(f"Skip video in database: {entry['title']}")
            continue
        logger.info(f"New video found: [{entry['link']}] {entry['title']}")

        # Save the new entry first, mark it as not finished
        db["videos"].insert(0, {"title": entry["title"], "link": entry["link"], "finished": False})
        save_json(db, database)
        res = await process_single_entry(entry, conf)
        if res["updated"]:
            db["videos"][0]["finished"] = True
            save_json(db, database)


if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(description="Sync videos from feed url to Telegram")
    parser.add_argument("--config", type=str, default="data/config.json", required=False, help="Path to mapping json file.")
    parser.add_argument("--id", type=str, required=True, help="Feed id to sync.")
    parser.add_argument("--url", type=str, required=True, help="Feed url.")
    args = parser.parse_args()

    # loguru settings
    logger.remove()  # Remove default handler.
    logger.add(
        sys.stderr,
        colorize=True,
        level=os.getenv("LOG_LEVEL", "DEBUG"),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green>| <level>{level: <7}</level> | <cyan>{name: <10}</cyan>:<cyan>{function: ^30}</cyan>:<cyan>{line: >4}</cyan> - <level>{message}</level>",
    )
    asyncio.run(main())
