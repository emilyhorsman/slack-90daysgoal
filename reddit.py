#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from datetime import datetime
import json
import requests
import redis
import praw
import config

def check(before=None):
    r = praw.Reddit(user_agent=config.user_agent)

    url_params = {}
    if before:
        url_params["before"] = "t3_{}".format(before)
    subreddit  = r.get_subreddit("90daysgoal")
    threads    = subreddit.get_new(params=url_params)
    moderators = map(lambda m: m.name, subreddit.get_moderators())


    items = []
    for thread in threads:
        if thread.author.name not in moderators:
            continue

        if thread.title.lower().find("[daily goal]") == -1:
            continue

        items.append(thread)

    return items

def get_latest(k, redis_client):
    latest = redis_client.zrevrange(k, 0, 0)
    if len(latest) > 0:
        return latest[0]

def post_to_slack(url):
    d = datetime.now().strftime("%b %-d ’%y *%-I:%M %p*")
    msg = "Latest Daily Goal thread as of {}: {}".format(d, url)
    payload = {
        "text": msg,
        "channe": config.bot_channel,
        "icon_emoji": config.bot_emoji,
        "username": config.bot_username
        }
    r = requests.post(config.slack_webhook, data=json.dumps(payload))

r = redis.from_url(config.redis_url)
k = "{}:threads".format(config.redis_prefix)

latest = get_latest(k, r)

for thread in check(latest):
    r.zadd(k, thread.id, int(thread.created_utc))

latest = get_latest(k, r)
post_to_slack(config.thread_url.format(latest))
