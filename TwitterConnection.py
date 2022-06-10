import tweepy
import os
import traceback
from time import sleep
from Logger import log
from queue import Queue
from threading import Thread
from datetime import datetime

self_screen_name = None
api = None
counter = 0
must_follow = False

last_id = "0000000000000000001"


STATUS_MESSAGES = {
    "blocked": "I can't read the tweet because I am blocked.",
    "server_error": "I can't read the tweet due to a server error. Try again later.",
    "private": "I can't read private tweets.",
    "nomessage": "The tweet has to contain a message.",
    "nofollower": "You have to follow to use the bot.",
}


def set_must_follow(val):
    global must_follow
    must_follow = val


def init(consumer_key, consumer_secret, key, secret):
    global api, self_screen_name, last_id
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(key, secret)
    api = tweepy.API(auth)
    self_screen_name = api.verify_credentials().screen_name
    log("\nInitiated the bot as user \"%s\"!\n\n" % self_screen_name, "main")

    try:
        last_tweets = api.user_timeline()
        for tweet in last_tweets:
            if "MakeItAQuote" not in tweet.source:
                continue
            if not tweet.in_reply_to_status_id_str:
                continue
            last_id = tweet.in_reply_to_status_id_str
            break
        if last_id == "0000000000000000001" and len(last_tweets) > 0:
            last_id = last_tweets[0].id_str
    except Exception:
        traceback.print_exc()
        pass
    return api


def filter_tweets(trigger_tweet):
    global self_screen_name

    log("Checking if user is authorized...", "worker")

    if trigger_tweet.user.followers_count >= 10000 or trigger_tweet.user.verified or \
            trigger_tweet.user.screen_name == "DakuuLoL" or trigger_tweet.user.screen_name == self_screen_name:
        log("...it's a VIP!", "worker")
        return True

    if must_follow:
        while True:
            try:
                friendship = api.get_friendship(source_screen_name=self_screen_name,
                                                target_screen_name=trigger_tweet.user.screen_name)[0]
                break
            except tweepy.TooManyRequests:
                log("Too many friendship requests. Backing off for 10 minutes.", "worker")
                sleep(600)

        if must_follow and not friendship.followed_by:
            # filter out if not following
            log("...user isn't following!", "worker")
            post_reply(trigger_tweet, STATUS_MESSAGES["nofollower"])
            return False

    log("...authorized user!", "worker")
    return True


def post_media_tweet(img_path, text):
    log("Posting tweet...", "worker")
    media = api.media_upload(img_path)

    tweet = api.update_status(text, media_ids=[media.media_id_string])
    try:
        log("Deleting local image...", "worker")
        os.remove(img_path)
    except OSError:
        log("Unable to delete local image!", "worker")
    log("Local image deleted!", "worker")
    log("Tweet posted! (%s)" % get_tweet_url(tweet), "worker")
    return tweet


def post_media_tweet_reply(tweet, img_path, text, alt_text=None):
    log("Posting tweet...", "worker")
    media = api.media_upload(img_path)

    if alt_text:
        api.create_media_metadata(media.media_id_string, alt_text)

    tweet = api.update_status("@%s %s" % (tweet.user.screen_name, text), media_ids=[media.media_id_string],
                              in_reply_to_status_id=tweet.id_str)
    try:
        log("Deleting local image...", "worker")
        os.remove(img_path)
        log("Local image deleted!", "worker")
    except OSError:
        log("Unable to delete local image!", "worker")
    log("Tweet posted! (%s)" % get_tweet_url(tweet), "worker")
    return tweet


def post_reply(tweet, text):
    log("Posting reply...", "worker")
    reply = api.update_status("@%s %s" % (tweet.user.screen_name, text), in_reply_to_status_id=tweet.id_str)
    log("Reply posted! (%s)" % get_tweet_url(reply), "worker")


def get_tweet_url(tweet):
    return "https://twitter.com/%s/status/%s" % (tweet.user.screen_name, tweet.id_str)


def get_mentions(q):
    global last_id

    mentions = api.mentions_timeline(since_id=last_id, count="200", tweet_mode="extended")

    if len(mentions) == 0:
        return

    log("\n%d new mentions!\n" % len(mentions), "main")

    i = 0
    j = 0
    for mention in reversed(mentions):

        new_id = mention.id_str

        # filter retweets
        if hasattr(mention, "retweeted_status"):
            continue

        # filter false requests
        if not mention.is_quote_status and not mention.in_reply_to_status_id_str:
            continue

        # filter implicit mentions
        display_range = mention.display_text_range

        if ("@%s" % self_screen_name).lower() not in (
                mention.full_text[display_range[0]:display_range[1]]).lower():
            continue

        i += 1
        q.put(mention)

    log("\nEnqueued %d requests. Enqueued %d deletions.\n" % (i, j), "main")
    last_id = new_id


def react_to_triggers(callback):
    global last_id
    if last_id == "0000000000000000001":
        last_mention = api.mentions_timeline(count=1)
        if len(last_mention) > 0:
            last_id = last_mention[0].id_str

    # init request queue
    queue = Queue()

    log("Waiting for mentions", "main")

    # starting worker thread
    worker = Thread(target=process_queue, args=[queue, callback])
    worker.setDaemon(True)
    worker.start()


    # retrieving mentions
    errors = 0
    while True:
        try:
            get_mentions(queue)
            errors = 0
            sleep(15)
        except tweepy.TweepyException as e:
            errors += 1
            traceback.print_exc()
            sleep(30 * errors)



def handle_request(mention, callback, queue):

    # if tweet older than 30s, check if got deleted
    if datetime.now().timestamp() - mention.created_at.timestamp() > 30:
        log("The tweet is older than 30s, checking if it got deleted...", "worker")
        try:
            mention = api.get_status(mention.id_str, tweet_mode="extended")
        except tweepy.NotFound:
            log("...it got deleted.", "worker")
            return
        log("...it's still available!", "worker")

    if not filter_tweets(mention):
        log("Tweet filtered out!", "worker")
        return

    og_tweet = None
    try:
        if mention.is_quote_status:
            log("It is a quote!", "worker")
            og_tweet = api.get_status(mention.quoted_status_id, tweet_mode="extended")
        elif mention.in_reply_to_status_id_str:
            log("It is a reply!", "worker")
            og_tweet = api.get_status(mention.in_reply_to_status_id_str, tweet_mode="extended")
    except tweepy.NotFound:
        log("Not found")
        return
    except tweepy.Unauthorized:
        log("Unauthorized", "worker")
        post_reply(mention, STATUS_MESSAGES["blocked"])
        return
    except tweepy.Forbidden:
        log("Forbidden", "worker")
        post_reply(mention, STATUS_MESSAGES["private"])
        return
    except tweepy.TooManyRequests:
        log("Too many requests", "worker")
        queue.put(mention)
        sleep(900)
        return
    except tweepy.TweepyException:
        log("Can't retrieve tweet:", "worker")
        traceback.print_exc()
        post_reply(mention, STATUS_MESSAGES["server_error"])
        return

    if not og_tweet:
        log("It was neither a reply nor a quote!", "worker")
        return

    if og_tweet.full_text[og_tweet.display_text_range[0]:og_tweet.display_text_range[1]] == "":
        post_reply(mention, STATUS_MESSAGES["nomessage"])
        return

    callback(mention, og_tweet, queue)
    return


def process_queue(q, callback):
    log("Worker thread started!", "worker")
    while True:
        try:
            log("\nApprox %d tweets in the queue." % q.qsize(), "worker")
            tweet = q.get()
            log("\nHandling next mention... (@%s)" % tweet.user.screen_name, "worker")
            handle_request(tweet, callback, q)
            q.task_done()
        except tweepy.TooManyRequests:
            log("Rate limit reached... (15 min backoff) (retrieving too many tweets)", "worker")
            q.put(tweet)
            sleep(600)
        except:
            pass
    return