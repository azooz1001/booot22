import TwitterConnection
from time import sleep
import re
import os
from dotenv import load_dotenv
from Logger import log
from tweepy import TweepyException

import ImageGenerator as generator

load_dotenv()


def handle_tweet(trigger_tweet, og_tweet, queue):

    img_path = tweet_to_image(og_tweet)
    msg = ""

    try:
        TwitterConnection.post_media_tweet_reply(trigger_tweet, img_path, msg)
    except TweepyException as e:
        if 185 not in e.api_codes:
            return
        try:
            log(e, "worker")
            log("Rate limit reached... (15 min backoff)", "worker")
            queue.put(trigger_tweet)
            sleep(900)
        except Exception as pe:
            print(pe)
    return


def tweet_to_image(tweet):
    text = normalize_text(tweet)

    bg_url = tweet.user.profile_image_url.replace("_normal", "_400x400")

    generator.init()
    generator.setAuthor(tweet.user.name)
    generator.setQuote(text)
    generator.setHandle("@%s" % tweet.user.screen_name)
    generator.setProfileImage(bg_url)

    path = "temp.jpg"
    generator.screenshot(path)
    log("Image generated", "worker")

    return path


def normalize_text(tweet):
    text = tweet.full_text[tweet.display_text_range[0]:tweet.display_text_range[1]]
    urls = tweet.entities["urls"]
    for url in urls:
        if re.match(r"(https?://)?(www\.)?twitter.com/[a-zA-Z0-9_]+/status/[0-9]+(\?[^ ]*)?", url["expanded_url"]):
            if url["indices"][1] == tweet.display_text_range[1]:
                text = text.replace(url["url"], "", 1)
                continue
        text = text.replace(url["url"], re.sub(r"https?://", "", url["display_url"], 1))
    text = re.sub(r"twitter\.com/[a-zA-Z0-9]{1,18}/status/[0-9]+$", "", text)
    text = re.sub(r"https?://t\.co/\w+$", "", text)
    return text.strip()


def main():
    consumer_key = os.environ["TWITTER_CONSUMER_KEY"]
    consumer_secret = os.environ["TWITTER_CONSUMER_SECRET"]
    key = os.environ["TWITTER_KEY"]
    secret = os.environ["TWITTER_SECRET"]


    tweepy = TwitterConnection.init(consumer_key, consumer_secret, key, secret)

    TwitterConnection.set_must_follow(True)
    TwitterConnection.react_to_triggers(handle_tweet)
    return


if __name__ == "__main__":
    main()
