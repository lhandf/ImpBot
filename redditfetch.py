import praw
import random
import os

r = praw.Reddit(client_id=os.getenv("REDDITTOKEN"), client_secret=os.getenv('REDDITSECRET'), user_agent='impbot')

def random_post(subreddit, num=40):
    sub = r.subreddit(subreddit)
    posts = [post for post in sub.hot(limit=num) if not "reddit.com/" in post.url.lower() and "v.redd.it" not in post.url.lower() and "https://youtu.be" not in post.url.lower()]
    post = random.choice(posts)
    return post

def random_from_several(subreddits, num=40):
    allposts = list()
    for s in subreddits:
        sub = r.subreddit(s)
        posts = [post for post in sub.hot(limit=num) if not "reddit.com/" in post.url.lower() and "v.redd.it" not in post.url.lower() and "https://youtu.be" not in post.url.lower()]
        allposts = allposts + posts
    post = random.choice(allposts)
    return post
