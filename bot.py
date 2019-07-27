import discord
import os
import urllib.request
import json
import re
import pickle
import asyncio
import time
from datetime import datetime, timedelta

newschan = None
gamefeedchan = None

client = discord.Client()
seennewbies = dict()
seenids = dict()
server = None

token = os.getenv("IMPBOT_TOKEN")

NEWSFORMAT="""
{} NEWS {}
Date: {}
Author: {}
To: {}
Subject: {}

{}"""

def newshelper(section, postnum):
    try:
        section = section.lower()
        url = 'https://api.imperian.com/news/{}/{}.json'.format(section, postnum)
        page = urllib.request.urlopen(url)
        if page.getcode() != 200:
            print ("Failed to get news post {} #{} - does it exist?".format(section, postnum))
            return
        post = json.loads(page.read())["post"]
        poststring = NEWSFORMAT.format(post["section"].upper(), post["id"], time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(post["date"])), post["from"], post["to"], post["subject"], post["message"])
        return poststring
    except Exception as e:
        print("Exception in newshelper: {}".format(e))

def getnews(message):
    try:
        section = message.content.split(' ', 2)[1]
        postnum = message.content.split(' ', 3)[2]
        return newshelper(section, postnum)
    except Exception as e:
        print("Exception in getnews/newsh {}".format(e))

def periodicTasks():
    global seenids
    global seennewbies
    loop = asyncio.get_event_loop()  
    loop.call_later(5, periodicTasks)

    # Fetch the imperian gamefeed and output it
    outstr = ""
    try:
        page = urllib.request.urlopen('https://api.imperian.com/gamefeed.json')
        if page.getcode() == 200:
            feed = json.loads(page.read())
            # check the newbies in the list, remove any older than 24h
            now = datetime.utcnow()
            todelete=list()
            for newbie in seennewbies:
                if (now - seennewbies[newbie]) > timedelta(1):
                    todelete.append(newbie)
            for newbie in todelete:
                del seennewbies[newbie]
            with open("seennewbies.pickle", "wb") as fh:
                pickle.dump(seennewbies, fh)
            # parse the feed. Any new messages (that aren't excluded for another reason) are sent to discord
            for event in feed:
                if event['type'] == "NEW":
                    name = event['description'].split()[4]
                    event['description'] = event['description'] + " (ignoring level up and achievement feed for 24h)"
                    seennewbies[name] = now
                if event['id'] not in seenids:
                    if len(seenids) >= 25:
                        # clear off one ID, since only 25 are sent at a time anyway
                        seenids = seenids[1:]
                    seenids.append(event['id'])
                    # ignore level up or achievement events for newbies we've seen in the last 24h
                    skip = False
                    if event['type'] == 'LUP' or event['type'] == 'ACH':
                        for newbie in seennewbies:
                            if newbie in event['description']:
                                skip = True
                                break
# Uncomment to ignore everything but death events
#                    if event['type'] != 'DEA':
#                        skip = True
                    if skip:
                        continue
                    desc = event['description']
                    asyncio.ensure_future(client.send_message(gamefeedchan, "{}: {}".format(event['date'], desc)))

            with open("seennewbies.pickle", "wb") as fh:
                pickle.dump(seennewbies, fh)
    except Exception as e:
        pass
    try:
        with open("gamefeedIDs.pickle", "wb") as fh:
            pickle.dump(seenids, fh)
    except Exception as e:
        print("Failed to save gamefeed IDs pickle...{}".format(e))

    # Check the news to see if the newest post is newer than what we've seen.
    url = 'https://api.imperian.com/news.json'
    page = urllib.request.urlopen(url)
    if page.getcode() != 200:
        pass
    sections = json.loads(page.read())
    knownsections = newssections.keys()
    for section in sections:
        #if section["name"] in knownsections:
        # only posting announce, not all sections
        if section["name"] == "Announce":
            if section["total"] > newssections[section["name"]]:
                num = newssections[section["name"]] + 1
                while num <= section["total"]:
                    try:
                        print("Posting {} {}".format(section["name"], num))
                        asyncio.ensure_future(client.send_message(newschan, "New news post posted!"))
                        thesection = section["name"]
                        outstr = newshelper(thesection, num)
                        for i in range(0, len(outstr), 2000):
                            asyncio.ensure_future(client.send_message(newschan, outstr[i:i+2000]))
                        num += 1
                        newssections[section["name"]] = num - 1
                        with open("lastnews.pickle", "wb") as fh:
                           pickle.dump(newssections, fh) 

                    except Exception as e:
                        print("Exception posting news: {}".format(e))
        else:
            pass

@client.event
async def on_member_join(member):
    welcomechan = server.get_channel("604497195500306447")
    msg = "Hello and welcome to the Imperian Discord server, {}! Please take a quick look at the first pinned message in the announcements channel for the ground rules. Feel free to set your nick to your character's name if you'd like, but you're under no obligation to do so!".format(member.mention)
    await client.send_message(welcomechan, msg)

@client.event
async def on_ready():
    global newschan
    global sm_newschan
    global logschan
    global gamefeedchan
    global server
    # Set up our objects
    if newschan is None:
        server = client.get_server("603327627742412800")
        newschan = server.get_channel("603390108506521635")
        gamefeedchan = server.get_channel("604420646184943617")
    await client.change_presence(game=discord.Game(name="Imperian"))
    print("<hacker voice>I'm in</hacker voice>")
    print(client.user)

# load current news limits
newssections = dict()
try:
    with open("lastnews.pickle", "rb") as fh:
        newssections = pickle.load(fh)
    for section in newssections:
        print("Section: {}. Post: {}.".format(section, newssections[section]))
except Exception as e:
    print("Failed to load seen news. Fetching the current maxes.")
    url = 'https://api.imperian.com/news.json'
    page = urllib.request.urlopen(url)
    if page.getcode() != 200:
        print("Failed to get news posts")
    sections = json.loads(page.read())
    for section in sections:
        newssections[section["name"]] = int(section["total"])
    with open("lastnews.pickle", "wb") as fh:
       pickle.dump(newssections, fh) 

# load list of seen gamefeed IDs
try:
    with open("gamefeedIDs.pickle", "rb") as fh:
        seenids = pickle.load(fh)
except Exception as e:
    print("Failed to load gamefeed IDs")
    seenids = list()

# load seen newbies
try:
    with open("seennewbies.pickle", "rb") as fh:
        seennewbies = pickle.load(fh)
except Exception as e:
    print("Failed to load seennewbies. Initializing dict.")
    seennewbies = dict()

loop = asyncio.get_event_loop()
loop.call_later(5, periodicTasks)

client.run(token)
loop.close()
