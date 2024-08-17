import discord
import json
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)


# Вызов значений из json файла
with open("info.json", encoding="UTF-8") as my_file:
    info_json = my_file.read()
info = json.loads(info_json)
balance = info["balance"]
balance_channel_id = info["balance_channel_id"]
auto_channel_id = info["auto_channel_id"]
cars = info.get("cars", ["Vapid Predator[2762]", "Vapid Predator[2968]"])
taken_cars = info.get("taken_cars", {})
token = info["token"]


# Обновление файла json
def updatejson():
    info["balance"] = balance
    info["cars"] = cars
    info["taken_cars"] = taken_cars
    info__json = json.dumps(info)
    with open("info.json", "w", encoding="UTF-8") as my__file:
        my__file.write(info__json)


# Запуск бота ответ в консоль
@bot.event
async def on_ready():
    print(f'{bot.user.name} начал заниматься ебаторией.')
    await bot.tree.sync()  # Синхронизация слэш-команд
    channel = bot.get_channel(auto_channel_id)
    await send_car_menu(channel)


# Для проверки на права админа
def is_admin():
    async def predicate(interaction):
        return interaction.user.guild_permissions.administrator
    return app_commands.check(predicate)


# Проверка нужного канала для баланса
def in_allowed_channel_balance():
    async def predicate(interaction):
        return interaction.channel.id == balance_channel_id
    return app_commands.check(predicate)


# Проверка нужного канала для машин
def in_allowed_channel_auto():
    async def predicate(interaction):
        return interaction.channel.id == auto_channel_id
    return app_commands.check(predicate)


# Установить баланс
@bot.tree.command(name="setbalance", description="Установить баланс.")
@is_admin()
@in_allowed_channel_balance()
async def setbalance(interaction: discord.Interaction, amount: int):
    global balance
    balance = amount
    updatejson()
    embed = discord.Embed(title="Баланс установлен",
                          description=f'{interaction.user.mention} установил баланс на {balance}$.',
                          color=discord.Color.purple())
    await interaction.response.send_message(embed=embed)


# Проверить баланс
@bot.tree.command(name="checkbalance", description="Проверить баланс.")
@in_allowed_channel_balance()
async def checkbalance(interaction: discord.Interaction):
    global balance
    embed = discord.Embed(title=f"Баланс организации: {balance}$",
                          description=f'{interaction.user.mention} проверил баланс.',
                          color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)


# Добавить средства
@bot.tree.command(name="addbalance", description="Добавить средства к балансу.")
@in_allowed_channel_balance()
async def addbalance(interaction: discord.Interaction, amount: int, reason: str = "Нет причины"):
    global balance
    balance += amount
    updatejson()
    embed = discord.Embed(title='Пополнили баланс организации',
                          description=f'{interaction.user.mention} пополнил баланс на {amount}$. \n'
                                      f'После пополнения баланс организации составляет: {balance}$. \n'
                                      f'Причина: {reason}',
                          color=discord.Color.green())
    await interaction.response.send_message(embed=embed)


# Снять средства с баланса
@bot.tree.command(name="removebalance", description="Снять средства с баланса.")
@in_allowed_channel_balance()
async def removebalance(interaction: discord.Interaction, amount: int, reason: str = "Нет причины"):
    global balance
    if amount > balance:
        embed = discord.Embed(title='Недостаточно средств на балансе',
                              description=f'Текущий баланс: {balance}$.',
                              color=discord.Color.red())
        await interaction.response.send_message(embed=embed)
    else:
        balance -= amount
        updatejson()
        embed = discord.Embed(title='Сняли со счёта организации',
                              description=f'{interaction.user.mention} снял со счёта {amount}$. \n'
                                          f'После снятия баланс организации составляет: {balance}$. \n'
                                          f'Причина: {reason}',
                              color=discord.Color.yellow())
        await interaction.response.send_message(embed=embed)


# Добавление и удаление машин в списке
@bot.tree.command(name='add_car')
@is_admin()
@in_allowed_channel_auto()
async def add_car(interaction: discord.Interaction, car_name: str):
    if car_name not in cars:
        cars.append(car_name)
        updatejson()
        await interaction.response.send_message(f"Автомобиль {car_name} добавлен в список.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Автомобиль {car_name} уже существует.", ephemeral=True)


@bot.tree.command(name='remove_car')
@is_admin()
@in_allowed_channel_auto()
async def remove_car(interaction: discord.Interaction, car_name: str):
    global taken_cars
    if car_name in cars:
        cars.remove(car_name)
        taken_cars = {user: car for user, car in taken_cars.items() if car != car_name}
        updatejson()
        await interaction.response.send_message(f"Автомобиль {car_name} удален из списка.", ephemeral=True)
    else:
        await interaction.response.send_message(f"Автомобиль {car_name} не найден.", ephemeral=True)


# Кнопка "Взять авто"
class TakeCarButton(Button):
    def __init__(self):
        super().__init__(label="Взять авто", style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        available_cars = [car for car in cars if car not in taken_cars.values()]
        if available_cars:
            select = Select(placeholder="Выберите автомобиль", options=[
                discord.SelectOption(label=car) for car in available_cars
            ])

            async def select_callback(select_interaction: discord.Interaction):
                chosen_car = select_interaction.data['values'][0]
                taken_cars[select_interaction.user.id] = chosen_car
                updatejson()
                await select_interaction.response.send_message(f"Вы взяли {chosen_car}.", ephemeral=True)

            select.callback = select_callback
            view = View()
            view.add_item(select)
            await interaction.response.send_message("Выберите доступный автомобиль:", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("Нет доступных автомобилей.", ephemeral=True)


# Кнопка "Вернуть авто"
class ReturnCarButton(Button):
    def __init__(self):
        super().__init__(label="Вернуть авто", style=discord.ButtonStyle.red)

    async def callback(self, interaction: discord.Interaction):
        global taken_cars  # Используем глобальную переменную
        if interaction.user.id in taken_cars:
            returned_car = taken_cars.pop(interaction.user.id)
            updatejson()
            await interaction.response.send_message(f"Вы вернули {returned_car}.", ephemeral=True)
        else:
            await interaction.response.send_message("Вы не брали автомобиль.", ephemeral=True)


# Кнопка "Показать состояние автомобилей"
class ShowStatusButton(Button):
    def __init__(self):
        super().__init__(label="Показать состояние автомобилей", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        status_message = "Состояние автомобилей:\n"
        for car in cars:
            owner = next((user for user, taken_car in taken_cars.items() if taken_car == car), "✅ Доступен")
            owner_name = f"❌ <@{owner}>" if owner != "✅ Доступен" else owner
            status_message += f"🚗 {car}: {owner_name}\n"

        await interaction.response.send_message(status_message, ephemeral=True)


# Создание меню с кнопками
async def send_car_menu(channel):
    view = View(timeout=None)
    view.add_item(TakeCarButton())
    view.add_item(ReturnCarButton())
    view.add_item(ShowStatusButton())
    await channel.send("## Управление автомобилями", view=view)


bot.run(token)
