import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Select
from dotenv import load_dotenv
import os
import json


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)
config_path = "info.json"


def read(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)


def write(data, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)


def get_config_value(key):
    file_data = read(config_path)
    data = file_data.get(key)
    return data


def edit_config(key, value):
    file_data = read(config_path)
    file_data[key] = value
    write(file_data, config_path)
    return file_data


def is_admin():
    async def predicate(interaction):
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)


def in_allowed_channel_balance():
    balance_channel_id = get_config_value("balance_channel_id")

    async def predicate(interaction):
        return interaction.channel.id == balance_channel_id
    return app_commands.check(predicate)


def in_allowed_channel_auto():
    auto_channel_id = get_config_value("auto_channel_id")

    async def predicate(interaction):
        return interaction.channel.id == auto_channel_id
    return app_commands.check(predicate)


async def send_car_menu(channel):
    view = View(timeout=None)
    view.add_item(TakeCarButton())
    view.add_item(ReturnCarButton())
    view.add_item(ShowStatusButton())
    await channel.send("## Управление автомобилями", view=view)


@bot.tree.command(name="setbalance", description="Установить баланс.")
@is_admin()
@in_allowed_channel_balance()
async def setbalance(interaction: discord.Interaction, amount: int):
    balance = get_config_value("balance")
    balance += amount
    edit_config("balance", balance)

    embed = discord.Embed(title="Баланс установлен",
                          description=f'{interaction.user.mention} установил баланс на {balance}$.',
                          color=discord.Color.purple())
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="checkbalance", description="Проверить баланс.")
@in_allowed_channel_balance()
async def checkbalance(interaction: discord.Interaction):
    balance = get_config_value("balance")
    embed = discord.Embed(title=f"Баланс организации: {balance}$",
                          description=f'{interaction.user.mention} проверил баланс.',
                          color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="addbalance", description="Добавить средства к балансу.")
@in_allowed_channel_balance()
async def addbalance(interaction: discord.Interaction, amount: int, reason: str = "Нет причины"):
    balance = get_config_value("balance")
    balance += amount
    edit_config("balance", balance)

    embed = discord.Embed(title='Пополнили баланс организации',
                          description=f'{interaction.user.mention} пополнил баланс на {amount}$. \n'
                                      f'После пополнения баланс организации составляет: {balance}$. \n'
                                      f'Причина: {reason}',
                          color=discord.Color.green())

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="removebalance", description="Снять средства с баланса.")
@in_allowed_channel_balance()
async def removebalance(interaction: discord.Interaction, amount: int, reason: str = "Нет причины"):
    balance = get_config_value("balance")
    if amount > balance:
        embed = discord.Embed(title='Недостаточно средств на балансе',
                              description=f'Текущий баланс: {balance}$.',
                              color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
    else:
        balance -= amount
        edit_config("balance", balance)
        embed = discord.Embed(title='Сняли со счёта организации',
                              description=f'{interaction.user.mention} снял со счёта {amount}$. \n'
                                          f'После снятия баланс организации составляет: {balance}$. \n'
                                          f'Причина: {reason}',
                              color=discord.Color.yellow())
        await interaction.response.send_message(embed=embed)


@bot.tree.command(name='add_car')
@is_admin()
@in_allowed_channel_auto()
async def add_car(interaction: discord.Interaction, car_name: str):
    cars = get_config_value("cars")
    if car_name not in cars:
        cars.append(car_name)
        edit_config("cars", cars)
        await interaction.response.send_message(f"Автомобиль {car_name} добавлен в список.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Автомобиль {car_name} уже существует.", ephemeral=True)


@bot.tree.command(name='remove_car')
@is_admin()
@in_allowed_channel_auto()
async def remove_car(interaction: discord.Interaction, car_name: str):
    taken_cars = get_config_value("taken_cars")
    cars = get_config_value("cars")

    if car_name in cars:
        cars.remove(car_name)
        taken_cars = {user: car for user, car in taken_cars.items() if car != car_name}

        edit_config("cars", cars)
        edit_config("taken_cars", taken_cars)

        await interaction.response.send_message(f"Автомобиль {car_name} удален из списка.", ephemeral=True)

    else:
        await interaction.response.send_message(f"Автомобиль {car_name} не найден.", ephemeral=True)


class TakeCarButton(Button):
    def __init__(self):
        super().__init__(label="Взять авто", style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        cars = get_config_value("cars")
        taken_cars = get_config_value("taken_cars")
        available_cars = [car for car in cars if car not in taken_cars.values()]
        if available_cars:
            select = SelectCar(available_cars=available_cars)
            view = View()
            view.add_item(select)
            await interaction.response.send_message("Выберите доступный автомобиль:", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("Нет доступных автомобилей.", ephemeral=True)


class SelectCar(Select):
    def __init__(self, available_cars):
        super().__init__(placeholder="Выберите автомобиль", options=[
            discord.SelectOption(label=car) for car in available_cars])

    async def callback(self, interaction: discord.Interaction):
        chosen_car = self.values[0]
        taken_cars = get_config_value("taken_cars")
        taken_cars[interaction.user.id] = chosen_car
        edit_config("taken_cars", taken_cars)
        await interaction.response.send_message(f"Вы взяли {chosen_car}.", ephemeral=True)


class ReturnCarButton(Button):
    def __init__(self):
        super().__init__(label="Вернуть авто", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        taken_cars = get_config_value("taken_cars")
        user_id_key = str(interaction.user.id)  # жесткий костыль потому что json ключи могут быть только строками
        if user_id_key in taken_cars.keys():
            returned_car = taken_cars.pop(user_id_key)
            edit_config("taken_cars", taken_cars)
            await interaction.response.send_message(f"Вы вернули {returned_car}.", ephemeral=True)
        else:
            await interaction.response.send_message("Вы не брали автомобиль.", ephemeral=True)


class ShowStatusButton(Button):
    def __init__(self):
        super().__init__(label="Показать состояние автомобилей", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        status_message = "Состояние автомобилей:\n"

        cars = get_config_value("cars")
        taken_cars = get_config_value("taken_cars")
        for car in cars:
            owner = next((user for user, taken_car in taken_cars.items() if taken_car == car), "✅ Доступен")
            owner_name = f"❌ <@{owner}>" if owner != "✅ Доступен" else owner
            status_message += f"🚗 {car}: {owner_name}\n"

        await interaction.response.send_message(status_message, ephemeral=True)


@bot.event
async def on_ready():
    print(f'{bot.user.name} начал заниматься ебейшей ебаторией.')
    await bot.tree.sync()
    auto_channel_id = get_config_value("auto_channel_id")
    channel = bot.get_channel(auto_channel_id)
    await send_car_menu(channel)


if __name__ == '__main__':
    bot.run(TOKEN)
