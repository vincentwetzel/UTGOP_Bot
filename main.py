# TODO: Intro dialogues
# TODO: Review all volunteer positions to make sure we have appropriate rooms
# TODO: Create all needed roles
# TODO: TinyURL and QR Code

import discord
from discord.ext import commands
from discord.ext.commands import CommandNotFound

# for general
import logging
from datetime import datetime
import os.path

ADMIN_DISCORD_ID = None
"""This is the main person the bot communicates with"""

# Init bot
description = '''This is Vincent's Bot for the UTGOP server. Use the !command syntax to send a command to the bot. '''
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', description=description, intents=intents)

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


@bot.event
async def on_ready():
    msg = await pad_message("UTGOP Bot is now online!") + "\n"
    await log_msg_to_server_owner(msg, False)

    # Double check everyone's roles.
    for guild in bot.guilds:
        for member in guild.members:
            if len(member.roles) == 1 and member.roles[0].name == "@everyone":
                await add_pleb_role(member)


@bot.event
async def on_socket_raw_receive(msg) -> None:
    """
    Logs whenever a socket receives raw content.
    :param msg: The information received by the socket
    :return: None
    """
    # logging.debug(msg)  # Comment this line out during normal operations
    pass


@bot.event
async def on_message(message: discord.Message) -> None:
    """
    This runs when the bot detects a new message.
    :param message: The Message that the bot has detected.
    :return: None
    """
    # we do not want the bot to reply to itself
    if message.author == bot.user:
        return

    # need this line, it prevents the bot from hanging
    await bot.process_commands(message)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member) -> None:
    """
    Handle Member status updates
    :param before: The Member before the status change.
    :param after: The Member after the status change
    :return: None
    """

    # Process status changes
    if before.status != after.status:
        # Desktop change
        if before.mobile_status is discord.enums.Status.offline and after.mobile_status is discord.enums.Status.offline:
            msg = ((str(before.display_name) + " is now:").ljust(35, ' ') + str(after.status).upper()).ljust(44,
                                                                                                             ' ') + ", \twas " + str(
                before.status).upper()
        elif before.mobile_status is not after.mobile_status:
            msg = ((str(before.display_name) + " is now:").ljust(35, ' ') + str(after.status).upper()).ljust(44,
                                                                                                             ' ') + " (MOBILE), \t was " + str(
                before.status).upper() + " (MOBILE)."
        elif before.web_status is not after.web_status:
            msg = (str(before.display_name + " is now:").ljust(35, ' ') + str(after.status).upper()).ljust(44,
                                                                                                           ' ') + " (WEB), \t was " + str(
                before.status).upper() + " (WEB)."
        else:
            msg = "Something weird happened when " + before.display_name + " updated their status."

    # Process nickname changes
    elif before.nick != after.nick:
        if after.nick is None:
            msg = (str(before.nick) + "\'s new nickname is: ").ljust(35, ' ') + after.name
        elif before.nick is None:
            msg = (before.name + "\'s new nickname is: ").ljust(35, ' ') + str(after.nick)
        else:
            msg = (str(before.nick) + "\'s new nickname is: ").ljust(35, ' ') + str(after.nick)

    # Process display_name changes
    elif before.display_name != after.display_name:
        msg = (before.name + "\'s new member_name is: ").ljust(35, ' ') + after.name

    # Process role changes
    elif before.roles != after.roles:
        new_roles = ""
        for role in after.roles:
            if str(role.name) == "@everyone":
                continue
            if new_roles == "":
                new_roles += str(role.name)
            else:
                new_roles += ", " + str(role.name)

        msg = (before.name + "\'s roles are now: ") + (new_roles if new_roles != "" else "None")

    # Process errors
    else:
        msg = "ERROR!!! " + after.name + " has caused an error in on_member_update()."

    # Log the changes
    await log_user_activity_to_file(str(before.name), msg)
    await log_msg_to_server_owner(msg)


@bot.event
async def on_member_join(member: discord.Member) -> None:
    """
    Welcomes new members, assigns them the Pleb role.
    :param member: The new Member
    :return: None
    """
    await (await get_text_channel(member.guild, "welcome")).send(
        "Welcome " + member.display_name + " to " + member.guild.name + "!", tts=True)

    msg: str = member.display_name + " has joined " + member.guild.name + "!"
    await log_msg_to_server_owner(msg)
    await log_user_activity_to_file(member.display_name, msg)

    add_pleb_role(member)


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    """
    Event for when a Member is removed from the Guild.
    :param member: The Member who has been removed
    :return: None
    """
    msg = member.display_name + " has left " + str(member.guild) + "."

    await (await get_text_channel(member.guild, "welcome")).send(msg)
    await log_msg_to_server_owner(msg)
    await log_user_activity_to_file(member.display_name, msg)


@bot.event
async def on_member_ban(guild: discord.Guild, member: discord.Member) -> None:
    """
    Stuff that happens when a member gets banned
    :param member: The person who got banned
    :return: None
    """
    msg = ("Member " + str(member.display_name) + " has been banned from " + str(member.guild) + "!")
    await (await get_text_channel(member.guild, "welcome")).send(msg, tts=True)
    await log_msg_to_server_owner(msg)
    await log_user_activity_to_file(member.display_name, msg)


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
    if after.channel != None:
        msg = member.display_name + " joined voice channel_name: ".ljust(25, ' ') + after.channel.name
    else:
        msg = member.display_name + " left voice channel_name: ".ljust(25, ' ') + before.channel.name
    await log_msg_to_server_owner(msg)
    await log_user_activity_to_file(member.display_name, msg)


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel) -> None:
    """
    Handles the event when a new guild channel_name is created.
    :param channel: The channel_name that was created
    :return: None
    """
    msg: str = "A new channel_name named \"" + channel.name + "\" has been created."
    await (await get_text_channel(channel.guild, "admin")).send(msg)
    await log_msg_to_server_owner(msg)


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel) -> None:
    """
    Handles the event when a guild channel_name is deleted.
    :param channel: The channel_name that was deleted
    :return: None
    """
    msg: str = "The channel_name \"" + channel.name + "\" has been deleted."
    await (await get_text_channel(channel.guild, "admin")).send(msg)
    await log_msg_to_server_owner(msg)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, CommandNotFound):
        return
    raise error


async def pad_message(msg, add_time_and_date=True, dash_count=75) -> str:
    """
    Pads a message with stars
    :param msg: The message
    :param add_time_and_date: Adds time and date
    :param dash_count: The number of stars to use in the padding
    :return: A new string with the original message padded with stars.
    """
    if add_time_and_date:
        msg = "\n" + (await add_time_and_date_to_string(msg)) + "\n"
    else:
        msg = "\n" + msg + "\n"
    # dash_count = len(log_msg) - 2
    for x in range(dash_count):
        msg = "-".join(["", msg, ""])
    return msg


async def add_time_and_date_to_string(msg):
    return datetime.now().strftime("%m-%d-%y") + "\t" + datetime.now().strftime("%I:%M:%S%p") + "\t" + msg


async def log_msg_to_server_owner(msg: str, add_time_and_date: bool = True, tts_param=False):
    """
    Sends a DM to the bot's owner.
    :param msg: The message to send
    :param add_time_and_date: Prepend information about the date and time of the logging item
    :param tts_param: Text-to-speech option
    :return:
    """
    msg = await add_time_and_date_to_string(msg) if (add_time_and_date is True) else msg
    await (await bot.fetch_user(ADMIN_DISCORD_ID)).send(msg, tts=tts_param)


async def log_user_activity_to_file(member_name: str, log_msg: str) -> None:
    """
    Creates/appends to a log file specific for a user.
    :param member_name: The name of the uer being logged
    :param log_msg: The information to be logged
    :return: None
    """
    log_msg = await add_time_and_date_to_string(log_msg)
    filepath = "logs/" + member_name + ".txt"
    if not os.path.isdir("logs"):
        os.mkdir("logs")
    with open(filepath, "a+", encoding="utf-8") as file:  # "a+" means append mode, create the file if it doesn't exist.
        file.write(log_msg + "\n")


async def get_text_channel(guild: discord.Guild, channel_name: str) -> discord.TextChannel:
    """
    Gets the text channel_name requested, creates if the channel_name does not exist.
    :param guild: The Guild for this request
    :param channel_name: The channel_name to be fetched or created
    :return: The Text Channel object
    """
    # Find the channel_name if it exists
    for channel in list(guild.text_channels):
        if channel.name == channel_name:
            return channel

    # If no Text Channel with this name exists, create one.
    return await guild.create_text_channel(channel_name, reason="Text Channel was requested but did not exist.")


async def add_pleb_role(member: discord.Member) -> None:
    """
    Adds the pleb Role to a Member.
    :param member: The Member to add the role to
    :return: None
    """
    pleb_role: discord.Role = discord.utils.get(member.guild.roles, name="Plebs")
    if pleb_role is None:
        pleb_role = await member.guild.create_role(name="Plebs", hoist=True, mentionable=True,
                                                   reason="Pleb role for the plebs")
        await log_msg_to_server_owner("The Pleb role did not exist, so the bot has created it.")
    await member.add_roles(pleb_role)


def init_bot_token(token_file: str) -> str:
    """
    Gets the bot's token from a file
    :param token_file: The token file from which to get the bot's token number.
    :return: The bot's token as a string.
    """
    if not os.path.exists(token_file):
        with open(token_file, 'a') as f:  # 'a' opens for appending without truncating
            token = input("The token file does not exist. Please enter the bot's token: ")
            f.write(token)
    else:
        with open(token_file, 'r+') as f:  # 'r+' is reading/writing mode, stream positioned at start of file
            token = f.readline().rstrip('\n')  # readline() usually has a \n at the end of it
            if not token:
                token = input("The token file is empty. Please enter the bot's token: ")
                f.write(token)
    return token


def init_admin_discord_id(id_fname: str) -> int:
    """
    Initializes the owner ID so the bot knows who is in charge.
    :param id_fname: The name of the file that contains the admin's id number
    :return: The ID of the admin user as a string.
    """
    if os.path.isfile("admin_dicord_id.txt"):
        with open("admin_dicord_id.txt", 'r') as f:
            try:
                line = f.readline().strip()
                if line and len(line) == 18:  # Discord IDs are 18 characters.
                    try:
                        return int(line)
                    except ValueError as e:
                        print(e)
                        print("There was an issue with the discord ID found in " + id_fname
                              + ". This file should only contain an 18-digit number and nothing else")
            except EOFError as e:
                print(e)
                print(id_fname + " is empty. This file must contain the user ID of the bot's admin")
    with open("admin_dicord_id.txt", "w") as f:
        id = input("Please enter the Discord ID number for the admin you want this bot to report to: ")
        f.write(id)
        return id


@bot.command(hidden=True)
async def msg(ctx: discord.ext.commands.Context, channel_name, *message) -> None:
    """
    Sends a message as the bot
    :param ctx: The ctx of the command
    :param channel_name: The Text Channel to send the message to
    :param message: The message to send
    :return: None
    """
    if ctx.message.author.id != ADMIN_DISCORD_ID:
        return
    await (await get_text_channel(ctx.guild, channel_name)).send(" ".join(message), tts=True)
    await ctx.send('You passed {}, {}, and {}'.format(ctx, channel_name, " ".join(message)))


@bot.command()
async def map(ctx: discord.ext.commands.Context) -> None:
    """
    Displays a PNG map of the Maverick Center.
    """
    with open("2021 GOP Convention Layout_Maverik Center-1.png", 'rb') as f:
        picture = discord.File(f)
        await ctx.channel.send(file=picture)


@bot.command()
async def phone(ctx: discord.ext.commands.Context) -> None:
    """
    Displays the phone numbers of convention leadership.
    :type ctx: The Context
    :return: None
    """
    msg = ""
    with open("phones.txt", 'r') as f:
        for line in f.readlines():
            msg += line
    await ctx.channel.send(msg)


@bot.command()
async def allocation(ctx: discord.ext.commands.Context) -> None:
    """
    Displays the number of delegates allocated to each county.
    :param ctx: The Context
    :return: None
    """
    await ctx.channel.send("Beaver: 10"
                           "\nBox Elder: 84"
                           "\nCache: 179"
                           "\nCarbon: 28"
                           "\nDaggett: 3"
                           "\nDavis: 547"
                           "\nDuchesne: 34"
                           "\nEmery: 18"
                           "\nGarfield: 11"
                           "\nGrand: 12"
                           "\nIron: 73"
                           "\nJuab: 17"
                           "\nKane: 13"
                           "\nMillard: 23"
                           "\nMorgan: 23"
                           "\nPiute: 5"
                           "\nRich: 5"
                           "\nSalt Lake: 1160"
                           "\nSan Juan: 21"
                           "\nSanpete: 44"
                           "\nSevier: 39"
                           "\nSummit: 51"
                           "\nTooele: 79"
                           "\nUintah: 58"
                           "\nUtah: 867"
                           "\nWasatch: 45"
                           "\nWashington: 256"
                           "\nWayne: 7"
                           "\nWeber288"
                           "\n\nTOTAL: 4000")


@bot.command()
async def tables(ctx: discord.ext.commands.Context) -> None:
    """
    Shows the setup/allocation for tables and chairs.
    :param ctx: The Context
    :return: None
    """
    with open("Maverick Tables Chairs and Baricades.png", 'rb') as f:
        picture = discord.File(f)
        await ctx.channel.send(file=picture)


@bot.command()
async def chairs(ctx: discord.ext.commands.Context) -> None:
    """
    Shows the setup/allocation for tables and chairs.
    :param ctx: The Context
    :return: None
    """
    with open("Maverick Tables Chairs and Baricades.png", 'rb') as f:
        picture = discord.File(f)
        await ctx.channel.send(file=picture)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    try:
        ADMIN_DISCORD_ID = int(init_admin_discord_id("admin_discord_id.txt"))
    except TypeError as e:
        print(e)
        print("This error means that there is something wrong with your admin_discord_id.txt file.")
    bot.run(init_bot_token("discord_token.txt"))
