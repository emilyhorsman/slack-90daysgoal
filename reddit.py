import requests
import requests.auth
import redis
import config

def is_a_daily_goal(moderators, thread):
    if thread["author"] not in moderators:
        return False

    t = thread["title"].lower()
    if t.find("[daily goal]") != -1:
        return True

    return False

def get_auth_string():
    client_auth = requests.auth.HTTPBasicAuth(config.client_id, config.client_secret)
    data = { "grant_type": "password", "username": config.username, "password": config.password }
    response = requests.post("https://www.reddit.com/api/v1/access_token", auth=client_auth, headers=get_headers(), data=data)
    return "{} {}".format(response.json()["token_type"], response.json()["access_token"])


def get_headers(auth_string=None):
    h = { "User-Agent": config.user_agent }
    if auth_string:
        h["Authorization"] = auth_string
    return h

def get_moderators(auth_string):
    response = requests.get("https://oauth.reddit.com/r/90daysgoal/about/moderators", headers=get_headers(auth_string))
    moderators = []
    for item in response.json()["data"]["children"]:
        moderators.append(item["name"])

    return moderators

def check(moderators, auth_string, before=None):
    url_params = {}
    if before:
        url_params["before"] = "t3_{}".format(before)

    response = requests.get("https://oauth.reddit.com/r/90daysgoal/new", headers=get_headers(auth_string), params=url_params).json()

    children = response["data"]["children"]
    if len(children) == 0:
        return

    items = []
    for item in children:
        data = item["data"]
        if not is_a_daily_goal(moderators, data):
            continue

        items.append(data)

    return items

r = redis.from_url(config.redis_url)
k = "{}:threads".format(config.redis_prefix)

latest = r.zrevrange(k, 0, 0)
if len(latest) == 0:
    latest = None
else:
    latest = latest[0]

auth_string = get_auth_string()
moderators  = get_moderators(auth_string)
threads = check(moderators, auth_string, latest)
for thread in threads:
    r.zadd("{}:threads".format(config.redis_prefix), thread["id"], int(thread["created_utc"]))
