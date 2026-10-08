import discord
from common.error_handlers import error_embed
from common.embed import create_embed_with_footer, create_embed


class PostModal(discord.ui.Modal, title = "Create Post"):
    def __init__(self):
        super().__init__()
        self.post_title = discord.ui.TextInput(required = False, max_length = 256, placeholder = "Extra! Extra! (Optional)")
        self.message = discord.ui.TextInput(style = discord.TextStyle.paragraph, max_length = 4000, placeholder = "Can use markdowns and [links](https://example.com)")
        self.channel = discord.ui.ChannelSelect(required = True, channel_types = [discord.ChannelType.text, discord.ChannelType.news], placeholder = "Pick a channel to post in", min_values = 1, max_values = 1)
        self.ping_targets = discord.ui.MentionableSelect(required = False, min_values = 0, max_values = 15, placeholder = "Roles/User to ping (Optional)")
        self.mass_ping = discord.ui.Select(
            options = [
                discord.SelectOption(label = "No Mass Ping", value = "none", default = True),
                discord.SelectOption(label = "@here (Online Members)", value = "here"),
                discord.SelectOption(label = "@everyone", value = "everyone"),
            ],
            min_values = 1, max_values = 1 
        )
        
        for text, component in (
            ("Title", self.post_title),
            ("Message", self.message),
            ("Channel", self.channel),
            ("Ping Roles/Users", self.ping_targets),
            ("Mass Ping", self.mass_ping)
        ):
            self.add_item(discord.ui.Label(text = text, component = component))
        
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = guild.get_channel(self.channel.values[0].id)
        if channel is None:
            await interaction.response.send_message(embed = error_embed("Channel Not Found", "Make sure the channel exists in the server"), ephemeral = True)
            return
        
        user_perms = channel.permissions_for(interaction.user)
        bot_perms = channel.permissions_for(guild.me)
        if not (user_perms.view_channel and user_perms.send_messages):
            await interaction.response.send_message(emebed = error_embed("No Permission", f"You can't post in {channel.mention}", ephemeral = True))
            return
        if not (bot_perms.send_messages and bot_perms.embed_links):
            await interaction.response.send_message(embed = error_embed("BattleBot Cannot Post Here", f"Make sure BattleBot has `Send Mesages` and `Embed Links` permissions in {channel.mention}"), epehemral = True)
            return
        
        mass = self.mass_ping.values[0]
        can_everyone = user_perms.mention_everyone and bot_perms.mention_everyone
        if mass != "none" and not can_everyone:
            await interaction.response.send_message(embed = error_embed("Can't Ping", f"`@{mass}` needs the `Mention Everyone` permission for the bot and the one posting in {channel.mention}"), ephemeral = True)
            return
        
        targets = self.ping_targets.values
        roles = [t for t in targets if isinstance(t, discord.Role)]
        users = [t for t in targets if not isinstance(t, discord.Role) and not t.bot]
        
        if any(r.is_default() for r in roles):
            await interaction.response.send_message(embed = error_embed("Can't Ping", "Use the 'Mass Ping' option for `@everyone` ping"), ephemeral = True)
            return
        blocked = [r for r in roles if not (r.mentionable or can_everyone)]
        if blocked:
            names = ", ".join(f"`{r.name}`" for r in blocked)
            await interaction.send_message(embed = error_embed("Can't Ping", f"These roles can't be pinged: {names}"), ephemeral = True)
            return
        no_access = [u for u in users if isinstance(u, discord.Member) and not channel.permissions_for(u).view_channel]
        if no_access:
            names = ", ".join(u.mention for u in no_access)
            await interaction.response.send_message(embed = error_embed("Can't Ping", f"These users can't see {channel.mention}: {names}"), ephemeral = True)
            return
        
        await interaction.response.defer(ephemeral = True)
        embed = create_embed_with_footer(title = self.post_title.value or None, description = self.message.value)
        parts = ([f"@{mass}"] if mass != "none" else []) + [r.mention for r in roles] + [u.mention for u in users]
        content = " ".join(parts) or None
        mentions = discord.AllowedMentions(everyone = mass != "none", users = users, roles = roles)
        try:
            sent = await channel.send(content = content, embed = embed, allowed_mentions = mentions)
        except discord.HTTPException as e:
            await interaction.followup.send(embed = error_embed("Coudln't Post", f"Message has been rejected: {e}"), ephemeral = True)
            return
        await interaction.followup.send(
            embed = create_embed(
                title = "✅ Message Posted",
                description = f"Message has been posted in {channel.mention}: {sent.jump_url}"
            ), 
            ephemeral = True
        )
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        embed = error_embed("Something Went Wrong", "The post could not be sent")
        if interaction.response.is_done():
            await interaction.followup.send(embed = embed, ephemeral = True)
        else:
            await interaction.response.send_message(embed = embed, ephemeral = True)
        raise error
    
class OpenPostModal(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout = 300)
        self.author_id = author_id
    
    @discord.ui.button(label = "Write Post", style = discord.ButtonStyle.primary, emoji = "📝")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Only the person who ran the command can use this", ephemeral = True)
            return
        await interaction.response.send_modal(PostModal())