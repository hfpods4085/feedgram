#! /usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import feedparser
from github import gh
from loguru import logger
from videogram.utils import load_json


def modify_feed_url(url: str) -> str:
    if os.getenv("RSSHUB_URL") and "https://rsshub.app" in url:
        url = url.replace("https://rsshub.app", os.environ["RSSHUB_URL"])
    return url


def main():
    if not Path(args.config).exists():
        return

    configs = load_json(args.config)
    for conf in configs:
        logger.info(f"Processing {conf['id']}")
        database: list = load_json(f"{args.data_dir}/{conf['id']}.json").get("videos", [])
        processed_vids = {x["link"] for x in database}
        feed_url = modify_feed_url(conf["feed"])
        remote = feedparser.parse(feed_url)
        remote_vids = {x["link"] for x in remote["entries"]}
        if remote_vids.issubset(processed_vids):
            logger.info(f"No new videos found for {conf['id']}")
            continue
        logger.warning(f"New videos found for {conf['id']}, trigger an update.")
        gh.trigger_workflow(feed_id=conf["id"], url=feed_url, proxy=conf["proxy"], cookie=conf["cookie"])


if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--log-level", type=str, default="INFO", required=False, help="Log level")
    parser.add_argument("--data-dir", type=str, default="data", required=False, help="Path to data directory.")
    parser.add_argument("--config", type=str, default="data/config.json", required=False, help="Path to mapping json file.")
    args = parser.parse_args()

    # loguru settings
    logger.remove()  # Remove default handler.
    logger.add(
        sys.stderr,
        colorize=True,
        level=args.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green>| <level>{level: <7}</level> | <cyan>{name: <10}</cyan>:<cyan>{function: ^30}</cyan>:<cyan>{line: >4}</cyan> - <level>{message}</level>",
    )
    main()
