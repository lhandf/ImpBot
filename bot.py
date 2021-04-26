from discord.ext import commands
import discord
import os
import urllib.request
import json
import re
import pickle
import asyncio
import time
from datetime import datetime, timedelta

# utility functions
import twit
import redditfetch

newschan = None
gamefeedchan = None
logschan = None
generalchan = None
furryfriendschan = None

logchanid = 604740251889696828
gamefeedid = 604420646184943617
newsid = 603390108506521635
serverid = 603327627742412800
welcomeid = 604497195500306447
generalid = 603327627742412802
botcommandid = 616084613588189268
moderatorchanid = 604743543403053105
furryfriendschanid = 654713808840818708

client = commands.Bot(command_prefix="!")
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
                    asyncio.ensure_future(gamefeedchan.send("{}: {}".format(event['date'], desc)))

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
                        asyncio.ensure_future(generalchan.send("New news post posted in #announce!"))
                        asyncio.ensure_future(newschan.send("New news post posted!"))
                        thesection = section["name"]
                        outstr = newshelper(thesection, num)
                        for i in range(0, len(outstr), 2000):
                            asyncio.ensure_future(newschan.send(outstr[i:i+2000]))
                        num += 1
                        newssections[section["name"]] = num - 1
                        with open("lastnews.pickle", "wb") as fh:
                           pickle.dump(newssections, fh) 

                    except Exception as e:
                        print("Exception posting news: {}".format(e))
        else:
            pass

# BEGIN EVENT HANDLERS

# When a user connects, send a welcome message.
@client.event
async def on_member_join(member):
    welcomechan = server.get_channel(welcomeid)
    msg = "Hello and welcome to the Imperian Discord server, {}! Please take a quick look at the first pinned message in the announcements channel for the ground rules. Feel free to set your nick to your character's name if you'd like, but you're under no obligation to do so!".format(member.mention)
    await welcomechan.send(msg)

# Set up globals on connection
@client.event
async def on_ready():
    global newschan
    global sm_newschan
    global logschan
    global gamefeedchan
    global server
    global generalchan 
    # Set up our objects
    if newschan is None:
        server = client.get_guild(serverid)
        newschan = server.get_channel(newsid)
        gamefeedchan = server.get_channel(gamefeedid)
        logschan = server.get_channel(logchanid)
        generalchan = server.get_channel(generalid)
        furryfriendschan = server.get_channel(furryfriendschanid)
    await client.change_presence(activity=discord.Game(name="Imperian"))
    print("<hacker voice>I'm in</hacker voice>")
    print(client.user)

# track edits made to posts for moderation
@client.event
async def on_message_edit(before, after):
    global logschan
    msg = "**{0.author}** edited their message in {0.channel.mention}:\nOld:\n{0.content}\n\nNew:\n{1.content}"
    await logschan.send(msg.format(before, after))

# track deletions made to posts for moderation
@client.event
async def on_message_delete(message):
    msg = "**{0.author}** deleted their message in {0.channel.mention}({0.channel.id}):\n\n{0.content}"
    await logschan.send(msg.format(message))

# END EVENT HANDLERS

# BEGIN COMMAND HANDLERS

# Command filter functions
def is_botcommands_channel(ctx):
    return ctx.message.channel.id in [botcommandid, moderatorchanid]

def is_pets_channel(ctx):
    return ctx.message.channel.id == furryfriendschanid

@client.command(pass_context=True, hidden=True)
@commands.has_role('Admin')
async def tweet(ctx, *args):
    """ Send a tweet to the Imperian twitter. Admin only. """
    tweet = ' '.join(args)
    if len(tweet) > 280:
        await ctx.send("Tweet too long. Keep it under 280 characters, Dickens.")
        return
    twitreturn = twit.post_tweet(tweet)
    await ctx.send("Tweet posted: {}".format(twitreturn.text))

@client.command(pass_context=True, hidden=True)
@commands.has_role('Admin')
async def idea(ctx, *args):
    """ Give a reminder on how to submit an idea """
    await ctx.send("That's a good idea! Please submit it in-game using the IDEA command. If you're unsure how to use that command, please read `HELP IDEAS` in-game, or here: https://www.imperian.com/game-help/?id=72")

@client.command(pass_context=True, hidden=True)
@commands.has_role('Admin')
async def bug(ctx, *args):
    """ Give a reminder on how to file bugs """
    await ctx.send("If you think you've found a bug in Imperian, please file it in-game using the BUG command! Please include as much context as possible! For more information on filing bugs, read `HELP BUGS` in-game, or here: https://www.imperian.com/game-help/?id=72")

@client.command(pass_context=True, hidden=True)
@commands.has_role('Admin')
async def issues(ctx, *args):
    """ Give a reminder about issues """
    await ctx.send("Discussion of issues is not permitted on this discord (just like it isn't allowed on the forums). If you need to file an issue, please do so in-game and read `HELP ISSUES` and `HELP USINGISSUES`. `HELP ISSUES`: https://www.imperian.com/game-help/?what=customer-service `HELP USINGISSUES`: https://www.imperian.com/game-help/?id=510")

# random utility commands
@client.command(pass_context=True)
@commands.check(is_botcommands_channel)
async def ftoc(ctx, *args):
    """ Convert degrees F to degress C """
    try:
        f = int(args[0])
        c = (f - 32) * 5/9
        await ctx.send("{} degrees F is {} degrees C".format(f, c))
    except:
        await ctx.send("Invalid input.")

@client.command(pass_context=True)
@commands.check(is_botcommands_channel)
async def ctof(ctx, *args):
    """ Convert degrees C to degress F """
    try:
        c = int(args[0])
        f = c * 9/5 + 32
        await ctx.send("{} degrees C is {} degrees F".format(c, f))
    except:
        await ctx.send("Invalid input.")

# fun things
@client.command(pass_context=True)
@commands.check(is_pets_channel)
async def corgme(ctx, *args):
    """ Fetch a random post from r/corgis r/corgi r/corgibutts r/babycorgis or r/corgigifs. Restricted to the furryfriends channel """
    try:
        post = redditfetch.random_from_several(["corgis", "corgi", "corgibutts", "babycorgis", "corgigifs"])
    except Exception as e:
        await ctx.send("Exception occurred!")
        return
    await ctx.send("__Title__: {}\n{}".format(post.title, post.url))

# END COMMAND HANDLERS

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
