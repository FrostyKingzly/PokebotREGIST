"""Registration Cog - Handles /register command and new trainer setup"""

import discord
from discord import app_commands
from discord.ext import commands

from ui.embeds import EmbedBuilder
from ui.buttons import RegistrationView, SocialStatsView, ConfirmationView


class RegistrationModal(discord.ui.Modal, title="Trainer Registration"):
    """Modal for collecting basic trainer info"""

    trainer_name = discord.ui.TextInput(
        label="Name",
        placeholder="Enter your first name...",
        required=True,
        max_length=20,
    )

    age = discord.ui.TextInput(
        label="Age",
        placeholder="How old are you?",
        required=True,
        max_length=3,
    )

    home_region = discord.ui.TextInput(
        label="Home Region",
        placeholder="Kanto, Johto, Hoenn, Sinnoh, Unova, Kalos, Alola, Galar, or Paldea",
        required=True,
        max_length=20,
    )

    bio = discord.ui.TextInput(
        label="Tell us a little about yourself (optional)",
        placeholder="Write a small blurb about your trainer...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=250,
    )

    avatar_url = discord.ui.TextInput(
        label="Character Photo URL (optional)",
        placeholder="Paste a link to an image of your character...",
        required=False,
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        interaction.client.temp_registration_data = {
            "user_id": interaction.user.id,
            "trainer_name": self.trainer_name.value.strip(),
            "age": self.age.value.strip(),
            "home_region": self.home_region.value.strip(),
            "bio": self.bio.value.strip() if self.bio.value else None,
            "avatar_url": self.avatar_url.value.strip() if self.avatar_url.value else None,
        }

        await interaction.response.defer(ephemeral=True)

        await interaction.followup.send(
            "✅ Perfect! Now let’s set up your social stats…",
            ephemeral=True,
        )

        await self.start_social_stats_selection(interaction)

    async def start_social_stats_selection(self, interaction: discord.Interaction):
        """Start social stats selection"""
        embed = discord.Embed(
            title="✨ Choose Your Social Stats",
            description=(
                "Every trainer has 5 social stats:\n\n"
                "**Heart** - Empathy & compassion\n"
                "**Insight** - Perception & intellect\n"
                "**Charisma** - Confidence & influence\n"
                "**Fortitude** - Physical grit & stamina\n"
                "**Will** - Determination & inner strength\n\n"
                "Choose one **Boon** (Rank 2) and one **Bane** (Rank 0).\n"
                "The other three will start at Rank 1."
            ),
            color=discord.Color.blue(),
        )

        view = SocialStatsView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        await view.wait()

        if view.boon_stat and view.bane_stat:
            data = interaction.client.temp_registration_data
            data["boon_stat"] = view.boon_stat
            data["bane_stat"] = view.bane_stat
            await self.show_registration_summary(interaction)

    async def show_registration_summary(self, interaction: discord.Interaction):
        """Show final summary and confirmation"""
        data = interaction.client.temp_registration_data

        description = (
            "\"Does this look right?\" "
            "The clerk slips you a shiny new ID with your information."
        )

        embed = discord.Embed(
            title="📋 Registration Summary",
            description=description,
            color=discord.Color.blurple(),
        )

        embed.add_field(
            name="🏷️ Name",
            value=data.get("trainer_name", "—"),
            inline=True,
        )
        embed.add_field(
            name="🎂 Age",
            value=data.get("age", "—"),
            inline=True,
        )
        embed.add_field(
            name="🌍 Home Region",
            value=data.get("home_region", "—"),
            inline=True,
        )

        bio = data.get("bio")
        if bio:
            embed.add_field(
                name="📝 About You",
                value=bio,
                inline=False,
            )

        boon = data["boon_stat"]
        bane = data["bane_stat"]
        stats_summary = f"Boon: **{boon.title()}** | Bane: **{bane.title()}**"

        embed.add_field(
            name="📊 Social Stats",
            value=stats_summary,
            inline=False,
        )

        if data.get("avatar_url"):
            embed.set_thumbnail(url=data["avatar_url"])

        embed.set_footer(text="Click ✅ to confirm or ❌ to cancel.")

        view = ConfirmationView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        await view.wait()

        if view.value:
            await self.complete_registration(interaction)
        else:
            await interaction.followup.send(
                "❌ Registration cancelled. Use `/register` to start over.",
                ephemeral=True,
            )

    async def complete_registration(self, interaction: discord.Interaction):
        """Complete registration and create trainer profile"""
        data = interaction.client.temp_registration_data

        success = interaction.client.player_manager.create_player(
            discord_user_id=data["user_id"],
            trainer_name=data["trainer_name"],
            avatar_url=data.get("avatar_url"),
            boon_stat=data["boon_stat"],
            bane_stat=data["bane_stat"],
            age=data.get("age"),
            home_region=data.get("home_region"),
            bio=data.get("bio"),
        )

        if not success:
            embed = EmbedBuilder.error(
                "Registration Failed",
                "You already have a trainer profile! Use `/menu` to continue your journey.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        description = (
            "You’ve just taken your very first steps into the beautiful city of dreams.\n\n"
            f"Welcome to Reverie City, **{data['trainer_name']}**! ✨\n\n"
            "Alright, looks like you’re all set! Enjoy your stay, and may all your dreams come true in Reverie!"
        )

        embed = discord.Embed(
            title="🎉 Registration Complete!",
            description=description,
            color=discord.Color.gold(),
        )

        if data.get("avatar_url"):
            embed.set_thumbnail(url=data["avatar_url"])

        await interaction.followup.send(embed=embed, ephemeral=False)

        if hasattr(interaction.client, "temp_registration_data"):
            del interaction.client.temp_registration_data


class RegistrationCog(commands.Cog):
    """Handles trainer registration"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="register",
        description="Create your trainer profile and begin your journey",
    )
    async def register(self, interaction: discord.Interaction):
        """Register as a new trainer"""
        await interaction.response.defer(ephemeral=True)

        if self.bot.player_manager.player_exists(interaction.user.id):
            embed = EmbedBuilder.error(
                "Already Registered",
                "You already have a trainer profile! Use `/menu` to continue your journey.",
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        description = (
            "You’ve just taken your very first steps into the beautiful city of dreams.\n\n"
            "You step up to the counter at the registration center, and the clerk smiles at you.\n\n"
            "\"Welcome to Reverie City! We’re so happy to have you! I’m sure you’re looking forward to seeing the sights!\"\n\n"
            "\"Let's get started on registering your ID!\""
        )

        embed = discord.Embed(
            title="🌆 Welcome to Reverie City!",
            description=description,
            color=discord.Color.green(),
        )
        embed.set_footer(text="Press the button below to begin registering your ID.")

        view = RegistrationView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    """Setup function for loading the cog"""
    await bot.add_cog(RegistrationCog(bot))
