"""This python file will host discord bot."""
import json
import time

import discord
import zmq
from discord import File
from discord import app_commands
from discord.ext import commands

import line_notify
import utilities as utils

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="!", intents=discord.Intents.all())

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5555")

supported_image_format = ('.jpg', '.png', '.jpeg')
supported_video_format = '.mp4'
supported_audio_format = ('.m4a', '.wav', '.mp3', '.aac', '.flac', '.ogg', '.opus')

config = utils.read_config()


@client.event
async def on_ready():
    """Initialize discord bot."""
    print("Bot is ready.")
    try:
        synced = await client.tree.sync()
        print(f"Synced {synced} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@client.tree.command(name="about", description="About this robot, view the services currently being synchronized")
@app_commands.describe()
async def about(interaction: discord.Interaction):
    subscribed_info = utils.get_subscribed_info_by_discord_channel_id(str(interaction.channel.id))
    if subscribed_info:
        sync_info = f"=======================================\n" \
                    f"Discord channel：{subscribed_info['discord_channel_name']}\n" \
                    f"Line group      ：{subscribed_info['line_group_name']}\n" \
                    f"=======================================\n"
    else:
        sync_info = f"尚未綁定任何Line群組！\n"
    all_commands = await client.tree.fetch_commands()
    help_command = discord.utils.get(all_commands, name="help")
    embed_message = discord.Embed(title="Discord <> Line message synchronization robot",
                                  description=f"A free service that helps you synchronize messages between two platforms\n\n"
                                              f"Services currently being synchronized:\n"
                                              f"{sync_info}\n"
                                              f"This project is developed by [Finder](https://github.com/finder1793),"
                                              f"And open source welcomes everyone to maintain it\n."
                                              f"You can use the command {help_command.mention} to learn how\nto use this bot\n",
                                  color=0x2ecc71)
    embed_message.set_author(name=client.user.name, icon_url=client.user.avatar)
    embed_message.add_field(name="author", value="LD", inline=True)
    embed_message.add_field(name="Developer", value=config['bot_owner'], inline=True)
    embed_message.add_field(name="Version", value="v0.2.2", inline=True)
    await interaction.response.send_message(embed=embed_message, view=AboutCommandView())


class AboutCommandView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=0)
        if 'line_bot_invite_link' in config:
            self.add_item(discord.ui.Button(label="Line Bot Invitation link",
                                            url=config['line_bot_invite_link'],
                                            style=discord.ButtonStyle.link,
                                            emoji="💬"))
            self.add_item(discord.ui.Button(label="Line Notify Invitation link",
                                            url="https://liff.line.me/1645278921-kWRPP32q/?accountId=linenotify",
                                            style=discord.ButtonStyle.link,
                                            emoji="🔔"))
        if 'discord_bot_invite_link' in config:
            self.add_item(discord.ui.Button(label="Discord Bot Invitation link",
                                            url=config['discord_bot_invite_link'],
                                            style=discord.ButtonStyle.link,
                                            emoji="🤖", row=1))
        self.add_item(discord.ui.Button(label="Github source code",
                                        url="https://github.com/finder1793/Discord-Line-Message-Sync",
                                        style=discord.ButtonStyle.link,
                                        emoji="🔬", row=1))


@client.tree.command(name="help", description="This command will help you use this bot")
@app_commands.describe()
async def help(interaction: discord.Interaction):
    all_commands = await client.tree.fetch_commands()
    about_command = discord.utils.get(all_commands, name="about")
    link_command = discord.utils.get(all_commands, name="link")
    unlink_command = discord.utils.get(all_commands, name="unlink")
    embed_message = discord.Embed(title="Discord <> Line message synchronization robot",
                                  description=f"`1.` {about_command.mention}｜About the bot\n"
                                              f">View the detailed information of the bot and the services currently being synchronized\n\n"
                                              f"`2.` {link_command.mention}｜Bind Line group and start synchronization\n"
                                              f"> Please make sure you have invited Line bot/Line Notify to the group\n"
                                              f"> and enter `!bind` in the group to get the Discord binding code\n\n"
                                              f"`3.` {unlink_command.mention}｜Unbind Line group and cancel synchronization\n"
                                              f">Unbind the Line group and cancel the message synchronization service\n\n",
                                  color=0x2ecc71)
    embed_message.set_author(name=client.user.name, icon_url=client.user.avatar)
    await interaction.response.send_message(embed=embed_message)


@client.tree.command(name="link", description="This command is used to bind to the Line group and synchronize messages")
@app_commands.describe(binding_code="Enter your binding code")
async def link(interaction: discord.Interaction, binding_code: str):
    binding_info = utils.get_binding_code_info(binding_code)
    if not binding_info:
        reply_message = "Binding failed. The binding code was entered incorrectly or in an incorrect format. Please try again."
        await interaction.response.send_message(reply_message, ephemeral=True)
    elif binding_info['expiration'] < time.time():
        utils.remove_binding_code(binding_code)
        reply_message = "Binding failed. This binding code has not been used for more than 5 minutes and has expired. Please re-enter in the Line group: `!Binding`"
        await interaction.response.send_message(reply_message, ephemeral=True)
    else:
        webhook = await interaction.channel.create_webhook(name="Line message synchronization")
        utils.add_new_sync_channel(binding_info['line_group_id'], binding_info['line_group_name'],
                                   binding_info['line_notify_token'], str(interaction.channel.id),
                                   interaction.channel.name, webhook.url)
        utils.remove_binding_code(binding_code)
        push_message = f"Binding successful!\n" \
                       f" ----------------------\n" \
                       f" | Discord <> Line |\n" \
                       f" | Message synchronization robot |\n" \
                       f" ----------------------\n\n" \
                       f"Discord channel: {interaction.channel.name}\n" \
                       f"Line group: {binding_info['line_group_name']}\n" \
                       f"===================\n" \
                       f"Currently supports synchronization: text messages, pictures, videos, audios"
        reply_message = f"**【Discord <> Line message synchronization robot - binding successfully!】**\n\n" \
                        f"Discord channel: {interaction.channel.name}\n" \
                        f"Line group: {binding_info['line_group_name']}\n" \
                        f"========================================\n" \
                        f"Currently supports synchronization: text messages, pictures, videos, audios"
        line_notify.send_message(push_message, binding_info['line_notify_token'])
        await interaction.response.send_message(reply_message)


@client.tree.command(name="unlink", description="此指令用來解除與Line群組的綁定, 並取消訊息同步")
@app_commands.describe()
async def unlink(interaction: discord.Interaction):
    channel_id = str(interaction.channel.id)
    subscribed_info = utils.get_subscribed_info_by_discord_channel_id(channel_id)
    if not subscribed_info:
        reply_message = "This channel is not bound to any Line group!"
        await interaction.response.send_message(reply_message, ephemeral=True)
    else:
        reply_message = f"**【Discord <> Line message synchronization bot - unsynchronize!】**\n\n" \
                        f"Discord channel: {subscribed_info['discord_channel_name']}\n" \
                        f"Line group: {subscribed_info['line_group_name']}\n" \
                        f"========================================\n" \
                        f"Are you sure you want to desynchronize?"
        await interaction.response.send_message(reply_message,
                                                view=UnlinkConfirmation(subscribed_info),
                                                ephemeral=True)


class UnlinkConfirmation(discord.ui.View):
    def __init__(self, subscribed_info):
        super().__init__(timeout=20)
        self.subscribed_info = subscribed_info

    @discord.ui.button(label="⛓️Confirm desynchronization", style=discord.ButtonStyle.danger)
    async def unlink_confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        utils.remove_sync_channel_by_discord_channel_id(self.subscribed_info['discord_channel_id'])
        push_message = f"Unsynchronized!\n" \
                       f" ----------------------\n" \
                       f" | Discord <> Line |\n" \
                       f" | Message synchronization robot |\n" \
                       f" ----------------------\n\n" \
                       f"Discord channel: {self.subscribed_info['discord_channel_name']}\n" \
                       f"Line group: {self.subscribed_info['line_group_name']}\n" \
                       f"===================\n" \
                       f"Executor: {interaction.user.display_name}\n"
        reply_message = f"**【Discord <> Line message synchronization robot - desynchronized!】**\n\n" \
                        f"Discord channel: {self.subscribed_info['discord_channel_name']}\n" \
                        f"Line group: {self.subscribed_info['line_group_name']}\n" \
                        f"========================================\n" \
                        f"Executor: {interaction.user.display_name}\n"
        self.stop()
        line_notify.send_message(push_message, self.subscribed_info['line_notify_token'])
        await interaction.response.send_message(reply_message)

    @discord.ui.button(label="Cancel operation", style=discord.ButtonStyle.primary)
    async def unlink_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        reply_message = "Operation canceled！"
        self.stop()
        await interaction.response.send_message(reply_message, ephemeral=True)


@client.event
async def on_message(message):
    """Handle message event."""
    if message.author == client.user:
        return
    discord_webhook_bot_ids = utils.get_discord_webhook_bot_ids()
    if message.author.id in discord_webhook_bot_ids:
        return
    subscribed_discord_channels = utils.get_subscribed_discord_channels()
    if message.channel.id in subscribed_discord_channels:
        subscribed_info = utils.get_subscribed_info_by_discord_channel_id(str(message.channel.id))
        sub_num = subscribed_info['sub_num']
        author = message.author.display_name
        if message.attachments:
            for attachment in message.attachments:
                if attachment.filename.endswith(supported_image_format):
                    message = message.clean_content
                    image_file_path = utils.download_file_from_url(subscribed_info['folder_name'],
                                                                   attachment.url,
                                                                   attachment.filename)
                    if message == '':
                        message = f"{author}: Sent picture"
                    else:
                        message = f"{author}: {message}(picture)"
                    line_notify.send_image_message(message, image_file_path,
                                                   subscribed_info['line_notify_token'])
                if attachment.filename.endswith(supported_video_format):
                    video_file_path = utils.download_file_from_url(subscribed_info['folder_name'],
                                                                   attachment.url,
                                                                   attachment.filename)
                    thumbnail_path = utils.generate_thumbnail(video_file_path)

                    # Send thumbnail to discord, get url, and delete the message.
                    thumbnail_message = await message.channel.send(thumbnail_path,
                                                                   file=File(thumbnail_path))
                    thumbnail_url = thumbnail_message.attachments[0].url
                    await thumbnail_message.delete()

                    message = message.clean_content
                    send_to_line_bot('video', sub_num, author, message,
                                     video_url=attachment.url, thumbnail_url=thumbnail_url)
                if attachment.filename.endswith(supported_audio_format):
                    audio_file_path = utils.download_file_from_url(sub_num, attachment.url,
                                                                   attachment.filename)
                    if not attachment.filename.endswith('.m4a'):
                        audio_file_path = utils.convert_audio_to_m4a(audio_file_path)
                    audio_duration = utils.get_audio_duration(audio_file_path)
                    message = message.clean_content
                    send_to_line_bot('audio', sub_num, author, message,
                                     audio_url=attachment.url, audio_duration=audio_duration)
                else:
                    # TODO(LD): Handle other file types.
                    pass
        else:
            message = message.clean_content
            line_notify.send_message(f"{author}: {message}", subscribed_info['line_notify_token'])


def send_to_line_bot(msg_type, sub_num, author, message, video_url=None, thumbnail_url=None,
                     audio_url=None, audio_duration=None):
    """Send message to line bot.

    Use zmq to send messages to line bot.

    :param msg_type: Message type, can be 'video', 'audio'.
    :param sub_num: Subscribed sync channels num.
    :param author: Author of the message.
    :param message: Message content.
    :param video_url: Video url.
    :param thumbnail_url: Thumbnail url.
    :param audio_url: Audio url.
    :param audio_duration: Audio duration.
    """
    data = {'msg_type': msg_type, 'sub_num': sub_num, 'author': author, 'message': message}
    if msg_type == 'video':
        data['video_url'] = video_url
        data['thumbnail_url'] = thumbnail_url
    if msg_type == 'audio':
        data['audio_url'] = audio_url
        data['audio_duration'] = audio_duration
    json_data = json.dumps(data, ensure_ascii=False)
    for i in range(2):
        if i == 1:
            socket.send_json(json_data)
        time.sleep(1)


client.run(config.get('discord_bot_token'))
