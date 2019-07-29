import twitter
import os

api = twitter.Api(consumer_key=os.getenv("IMBPOT_TWIT_CONSUMER_KEY"),
                  consumer_secret=os.getenv("IMPBOT_TWIT_CONSUMER_SEC"),
                  access_token_key=os.getenv("IMPBOT_TWIT_ACCESS_TOKEN"),
                  access_token_secret=os.getenv("IMPBOT_TWIT_ACCESS_SEC"))

def post_tweet(tweetcontents):
    return api.PostUpdate(tweetcontents)
