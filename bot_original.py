import discord
from discord.ext import commands
import sqlite3
import os
import random
from datetime import datetime, timedelta

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Database setup
def init_db():
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS noodle_stars
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT, 
                  stars INTEGER DEFAULT 0,
                  bank INTEGER DEFAULT 0,
                  last_mine TEXT,
                  gold_pickaxe INTEGER DEFAULT 0,
                  helmet INTEGER DEFAULT 0,
                  sword INTEGER DEFAULT 0,
                  raw_potato INTEGER DEFAULT 0,
                  golden_mushroom INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def get_user_stars(user_id, username):
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    c.execute('SELECT stars, last_mine, bank FROM noodle_stars WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    
    if result is None:
        c.execute('INSERT INTO noodle_stars (user_id, username, stars, bank, last_mine, gold_pickaxe, helmet, sword, raw_potato, golden_mushroom) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                  (user_id, username, 0, 0, None, 0, 0, 0, 0, 0))
        conn.commit()
        conn.close()
        return 0
    
    conn.close()
    return result[0]

def get_user_inventory(user_id):
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    c.execute('SELECT gold_pickaxe, helmet, sword, raw_potato, golden_mushroom FROM noodle_stars WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result is None:
        return {'gold_pickaxe': 0, 'helmet': 0, 'sword': 0, 'raw_potato': 0, 'golden_mushroom': 0}
    
    return {'gold_pickaxe': result[0], 'helmet': result[1], 'sword': result[2], 'raw_potato': result[3], 'golden_mushroom': result[4]}

def update_user_inventory(user_id, item, amount):
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    c.execute(f'UPDATE noodle_stars SET {item} = ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def clear_user_inventory(user_id):
    """Remove all items from user's inventory except gold pickaxe"""
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    c.execute('UPDATE noodle_stars SET helmet = 0, sword = 0, raw_potato = 0, golden_mushroom = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_user_bank(user_id):
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    c.execute('SELECT bank FROM noodle_stars WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result is None:
        return 0
    
    return result[0]

def update_user_stars(user_id, username, stars):
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO noodle_stars (user_id, username, stars, bank, last_mine) 
                 VALUES (?, ?, ?, 
                         COALESCE((SELECT bank FROM noodle_stars WHERE user_id = ?), 0),
                         (SELECT last_mine FROM noodle_stars WHERE user_id = ?))''', 
              (user_id, username, stars, user_id, user_id))
    conn.commit()
    conn.close()

def update_user_bank(user_id, username, bank):
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO noodle_stars (user_id, username, stars, bank, last_mine) 
                 VALUES (?, ?, 
                         COALESCE((SELECT stars FROM noodle_stars WHERE user_id = ?), 0),
                         ?,
                         (SELECT last_mine FROM noodle_stars WHERE user_id = ?))''', 
              (user_id, username, user_id, bank, user_id))
    conn.commit()
    conn.close()

def update_username(user_id, username):
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    c.execute('UPDATE noodle_stars SET username = ? WHERE user_id = ?', (username, user_id))
    conn.commit()
    conn.close()

def get_last_mine(user_id):
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    c.execute('SELECT last_mine FROM noodle_stars WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result is None or result[0] is None:
        return None
    
    return datetime.fromisoformat(result[0])

def update_last_mine(user_id):
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('UPDATE noodle_stars SET last_mine = ? WHERE user_id = ?', (now, user_id))
    conn.commit()
    conn.close()

# Check if user has moderator permissions
def is_moderator():
    async def predicate(ctx):
        return ctx.author.guild_permissions.moderate_members
    return commands.check(predicate)

@bot.event
async def on_ready():
    init_db()
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready to track noodle stars!')

@bot.command(name='addstar')
@is_moderator()
async def add_star(ctx, member: discord.Member, amount: int = 1):
    """Add noodle stars to a user (Moderator only)"""
    current_stars = get_user_stars(member.id, str(member))
    new_stars = current_stars + amount
    update_user_stars(member.id, str(member), new_stars)
    update_username(member.id, str(member))
    
    await ctx.send(f'⭐ Added {amount} noodle star(s) to {member.mention}! '
                   f'They now have **{new_stars}** noodle stars!')

@bot.command(name='removestar')
@is_moderator()
async def remove_star(ctx, member: discord.Member, amount: int = 1):
    """Remove noodle stars from a user (Moderator only)"""
    current_stars = get_user_stars(member.id, str(member))
    new_stars = current_stars - amount
    update_user_stars(member.id, str(member), new_stars)
    update_username(member.id, str(member))
    
    await ctx.send(f'📉 Removed {amount} noodle star(s) from {member.mention}! '
                   f'They now have **{new_stars}** noodle stars!')

@bot.command(name='stars')
async def check_stars(ctx, member: discord.Member = None):
    """Check noodle stars for a user"""
    if member is None:
        member = ctx.author
    
    stars = get_user_stars(member.id, str(member))
    bank = get_user_bank(member.id)
    total = stars + bank
    update_username(member.id, str(member))
    
    await ctx.send(f'⭐ {member.mention}\'s Noodle Stars:\n'
                   f'💰 Wallet: **{stars}** stars\n'
                   f'🏦 Bank: **{bank}** stars\n'
                   f'📊 Total: **{total}** stars')

@bot.command(name='topstars')
async def top_stars(ctx):
    """Show top 10 users with the most noodle stars"""
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    c.execute('SELECT username, stars FROM noodle_stars ORDER BY stars DESC LIMIT 10')
    results = c.fetchall()
    conn.close()
    
    if not results:
        await ctx.send('No noodle stars have been awarded yet!')
        return
    
    embed = discord.Embed(title='🌟 Top 10 Good Noodles 🌟', color=discord.Color.gold())
    
    for i, (username, stars) in enumerate(results, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
        embed.add_field(name=f'{medal} {username}', value=f'{stars} stars', inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='bottomstars')
async def bottom_stars(ctx):
    """Show bottom 10 users with the least noodle stars"""
    conn = sqlite3.connect('noodle_stars.db')
    c = conn.cursor()
    c.execute('SELECT username, stars FROM noodle_stars ORDER BY stars ASC LIMIT 10')
    results = c.fetchall()
    conn.close()
    
    if not results:
        await ctx.send('No noodle stars have been awarded yet!')
        return
    
    embed = discord.Embed(title='📉 Bottom 10 Noodles 📉', color=discord.Color.red())
    
    for i, (username, stars) in enumerate(results, 1):
        embed.add_field(name=f'{i}. {username}', value=f'{stars} stars', inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='gamble')
async def gamble(ctx, amount: int = None):
    """Gamble your noodle stars for a chance to win more!"""
    user_id = ctx.author.id
    username = str(ctx.author)
    current_stars = get_user_stars(user_id, username)
    
    # Check if amount was provided
    if amount is None:
        await ctx.send(f'❌ {ctx.author.mention}, please specify how many stars to gamble! '
                       f'Usage: `!gamble <amount>`')
        return
    
    # Check if amount is valid
    if amount <= 0:
        await ctx.send(f'❌ {ctx.author.mention}, you must gamble at least 1 noodle star!')
        return
    
    # Check if user has enough stars to gamble
    if current_stars <= 0:
        await ctx.send(f'❌ {ctx.author.mention}, you need at least 1 noodle star to gamble! '
                       f'Current balance: **{current_stars}** stars')
        return
    
    # Check if user has enough stars for the bet
    if amount > current_stars:
        await ctx.send(f'❌ {ctx.author.mention}, you only have **{current_stars}** stars! '
                       f'You can\'t gamble **{amount}** stars!')
        return
    
    # Select random modifier with weighted probabilities
    # 1% chance for 5x, equal chances for the rest
    rand = random.random()
    if rand < 0.01:  # 1% chance
        modifier = 5
    elif rand < 0.34:  # 33% chance
        modifier = 1.25
    elif rand < 0.67:  # 33% chance
        modifier = 1.5
    else:  # 33% chance
        modifier = 2
    
    # Roll a number between 1 and 7
    roll = random.randint(1, 7)
    
    # Check if they won (rolled a 7)
    if roll == 7:
        winnings = int(amount * modifier)
        new_stars = current_stars + winnings
        update_user_stars(user_id, username, new_stars)
        
        await ctx.send(f'🎰 {ctx.author.mention} gambled **{amount}** stars and rolled a **{roll}**! 🎉\n'
                       f'**YOU WIN!** Multiplier: **{modifier}x**\n'
                       f'You won **{winnings}** noodle stars!\n'
                       f'New balance: **{new_stars}** stars! ⭐')
    else:
        new_stars = current_stars - amount
        update_user_stars(user_id, username, new_stars)
        
        await ctx.send(f'🎰 {ctx.author.mention} gambled **{amount}** stars and rolled a **{roll}**... 💔\n'
                       f'**YOU LOSE!** You needed a 7!\n'
                       f'You lost **{amount}** noodle stars!\n'
                       f'New balance: **{new_stars}** stars! 😢')

@bot.command(name='coinflip')
async def coinflip(ctx, amount: int = None, choice: str = None):
    """Flip a coin and bet on heads or tails!"""
    user_id = ctx.author.id
    username = str(ctx.author)
    current_stars = get_user_stars(user_id, username)
    
    # Check if amount and choice were provided
    if amount is None or choice is None:
        await ctx.send(f'❌ {ctx.author.mention}, please specify an amount and choice! '
                       f'Usage: `!coinflip <amount> <heads/tails>`')
        return
    
    # Normalize choice
    choice = choice.lower()
    if choice not in ['heads', 'tails', 'h', 't']:
        await ctx.send(f'❌ {ctx.author.mention}, please choose either `heads` or `tails`!')
        return
    
    # Normalize h/t to full words
    if choice == 'h':
        choice = 'heads'
    elif choice == 't':
        choice = 'tails'
    
    # Check if amount is valid
    if amount <= 0:
        await ctx.send(f'❌ {ctx.author.mention}, you must bet at least 1 noodle star!')
        return
    
    # Check if user has enough stars
    if current_stars <= 0:
        await ctx.send(f'❌ {ctx.author.mention}, you need at least 1 noodle star to play! '
                       f'Current balance: **{current_stars}** stars')
        return
    
    if amount > current_stars:
        await ctx.send(f'❌ {ctx.author.mention}, you only have **{current_stars}** stars! '
                       f'You can\'t bet **{amount}** stars!')
        return
    
    # Flip the coin
    result = random.choice(['heads', 'tails'])
    coin_emoji = '🪙'
    
    # Check if they won
    if result == choice:
        winnings = int(amount * 1.9)
        new_stars = current_stars + winnings
        update_user_stars(user_id, username, new_stars)
        
        await ctx.send(f'{coin_emoji} {ctx.author.mention} bet **{amount}** stars on **{choice}**!\n'
                       f'The coin landed on... **{result.upper()}**! 🎉\n'
                       f'**YOU WIN!** You won **{winnings}** noodle stars!\n'
                       f'New balance: **{new_stars}** stars! ⭐')
    else:
        new_stars = current_stars - amount
        update_user_stars(user_id, username, new_stars)
        
        await ctx.send(f'{coin_emoji} {ctx.author.mention} bet **{amount}** stars on **{choice}**!\n'
                       f'The coin landed on... **{result.upper()}**! 💔\n'
                       f'**YOU LOSE!** You lost **{amount}** noodle stars!\n'
                       f'New balance: **{new_stars}** stars! 😢')

@bot.command(name='duel')
async def duel(ctx, opponent: discord.Member = None, amount: int = None):
    """Challenge another user to a dice duel!"""
    challenger_id = ctx.author.id
    challenger_name = str(ctx.author)
    
    # Check if opponent and amount were provided
    if opponent is None or amount is None:
        await ctx.send(f'❌ {ctx.author.mention}, please specify an opponent and amount! '
                       f'Usage: `!duel @user <amount>`')
        return
    
    # Check if trying to duel themselves
    if opponent.id == challenger_id:
        await ctx.send(f'❌ {ctx.author.mention}, you can\'t duel yourself!')
        return
    
    # Check if trying to duel a bot
    if opponent.bot:
        await ctx.send(f'❌ {ctx.author.mention}, you can\'t duel a bot!')
        return
    
    # Check if amount is valid
    if amount <= 0:
        await ctx.send(f'❌ {ctx.author.mention}, you must bet at least 1 noodle star!')
        return
    
    # Get both users' stars
    challenger_stars = get_user_stars(challenger_id, challenger_name)
    opponent_stars = get_user_stars(opponent.id, str(opponent))
    
    # Check if challenger has enough stars
    if challenger_stars <= 0:
        await ctx.send(f'❌ {ctx.author.mention}, you need at least 1 noodle star to duel! '
                       f'Current balance: **{challenger_stars}** stars')
        return
    
    if amount > challenger_stars:
        await ctx.send(f'❌ {ctx.author.mention}, you only have **{challenger_stars}** stars! '
                       f'You can\'t bet **{amount}** stars!')
        return
    
    # Check if opponent has enough stars
    if opponent_stars <= 0:
        await ctx.send(f'❌ {opponent.mention} doesn\'t have any noodle stars to duel with! '
                       f'Their balance: **{opponent_stars}** stars')
        return
    
    if amount > opponent_stars:
        await ctx.send(f'❌ {opponent.mention} only has **{opponent_stars}** stars! '
                       f'They can\'t match a bet of **{amount}** stars!')
        return
    
    # Roll the dice!
    challenger_roll = random.randint(1, 20)
    opponent_roll = random.randint(1, 20)
    
    await ctx.send(f'⚔️ **DICE DUEL!** ⚔️\n'
                   f'{ctx.author.mention} challenges {opponent.mention} to a duel for **{amount}** stars!\n\n'
                   f'🎲 Rolling...')
    
    # Check for tie
    while challenger_roll == opponent_roll:
        await ctx.send(f'**TIE!** Both rolled **{challenger_roll}**! Re-rolling... 🎲')
        challenger_roll = random.randint(1, 20)
        opponent_roll = random.randint(1, 20)
    
    # Determine winner
    if challenger_roll > opponent_roll:
        winner = ctx.author
        loser = opponent
        winner_roll = challenger_roll
        loser_roll = opponent_roll
        new_challenger_stars = challenger_stars + amount
        new_opponent_stars = opponent_stars - amount
        update_user_stars(challenger_id, challenger_name, new_challenger_stars)
        update_user_stars(opponent.id, str(opponent), new_opponent_stars)
    else:
        winner = opponent
        loser = ctx.author
        winner_roll = opponent_roll
        loser_roll = challenger_roll
        new_challenger_stars = challenger_stars - amount
        new_opponent_stars = opponent_stars + amount
        update_user_stars(challenger_id, challenger_name, new_challenger_stars)
        update_user_stars(opponent.id, str(opponent), new_opponent_stars)
    
    await ctx.send(f'🎲 {ctx.author.mention} rolled **{challenger_roll}**\n'
                   f'🎲 {opponent.mention} rolled **{opponent_roll}**\n\n'
                   f'🏆 **{winner.mention} WINS!** 🏆\n'
                   f'{winner.mention} won **{amount}** noodle stars from {loser.mention}!\n\n'
                   f'{ctx.author.mention}\'s balance: **{new_challenger_stars}** stars\n'
                   f'{opponent.mention}\'s balance: **{new_opponent_stars}** stars')

@bot.command(name='mine')
async def mine(ctx, use_item: str = None):
    """Mine for minerals to earn noodle stars!"""
    user_id = ctx.author.id
    username = str(ctx.author)
    
    # Get user inventory
    inventory = get_user_inventory(user_id)
    
    # Check if user wants to use golden mushroom
    using_mushroom = False
    if use_item and use_item.lower() in ['mushroom', 'golden mushroom', 'goldenmushroom']:
        if inventory['golden_mushroom'] <= 0:
            await ctx.send(f'❌ {ctx.author.mention}, you don\'t have any golden mushrooms!')
            return
        using_mushroom = True
        # Remove mushroom from inventory
        update_user_inventory(user_id, 'golden_mushroom', inventory['golden_mushroom'] - 1)
    
    # Get user's last mine time
    last_claim = get_last_mine(user_id)
    now = datetime.now()
    
    # Check cooldown (skip if using mushroom)
    if not using_mushroom and last_claim is not None:
        time_since_claim = now - last_claim
        
        # Check if user wants to use raw potato
        if use_item and use_item.lower() in ['potato', 'raw potato', 'rawpotato']:
            if inventory['raw_potato'] <= 0:
                await ctx.send(f'❌ {ctx.author.mention}, you don\'t have any raw potatoes!')
                return
            # Use potato - reduces cooldown to 5 minutes
            if time_since_claim < timedelta(minutes=5):
                time_remaining = timedelta(minutes=5) - time_since_claim
                minutes = int(time_remaining.total_seconds() // 60)
                seconds = int(time_remaining.total_seconds() % 60)
                await ctx.send(f'⏰ {ctx.author.mention}, even with a raw potato, you need to wait!\n'
                              f'Come back in **{minutes}m {seconds}s** to mine again!')
                return
            # Remove potato from inventory
            update_user_inventory(user_id, 'raw_potato', inventory['raw_potato'] - 1)
        else:
            # Normal 30 minute cooldown
            if time_since_claim < timedelta(minutes=30):
                time_remaining = timedelta(minutes=30) - time_since_claim
                minutes = int(time_remaining.total_seconds() // 60)
                seconds = int(time_remaining.total_seconds() % 60)
                
                await ctx.send(f'⛏️ {ctx.author.mention}, you\'re too tired to mine right now!\n'
                              f'Come back in **{minutes}m {seconds}s** to mine again!\n'
                              f'💡 *Use `!mine potato` to reduce cooldown or `!mine mushroom` to mine instantly!*')
                return
    
    has_gold_pickaxe = inventory['gold_pickaxe'] > 0
    has_helmet = inventory['helmet'] > 0
    has_sword = inventory['sword'] > 0
    
    # Define minerals with their rarity and rewards
    if has_gold_pickaxe:
        # Better odds with gold pickaxe
        minerals = [
            {'name': 'Stone', 'emoji': '🪨', 'stars': 5, 'weight': 30},
            {'name': 'Coal', 'emoji': '⚫', 'stars': 10, 'weight': 25},
            {'name': 'Iron', 'emoji': '⚙️', 'stars': 20, 'weight': 20},
            {'name': 'Gold', 'emoji': '🟡', 'stars': 40, 'weight': 15},
            {'name': 'Diamond', 'emoji': '💎', 'stars': 100, 'weight': 10}
        ]
    else:
        # Normal odds
        minerals = [
            {'name': 'Stone', 'emoji': '🪨', 'stars': 5, 'weight': 40},
            {'name': 'Coal', 'emoji': '⚫', 'stars': 10, 'weight': 30},
            {'name': 'Iron', 'emoji': '⚙️', 'stars': 20, 'weight': 15},
            {'name': 'Gold', 'emoji': '🟡', 'stars': 40, 'weight': 10},
            {'name': 'Diamond', 'emoji': '💎', 'stars': 100, 'weight': 5}
        ]
    
    # Select random mineral based on weights
    mineral = random.choices(minerals, weights=[m['weight'] for m in minerals])[0]
    
    # Give reward
    reward = mineral['stars']
    current_stars = get_user_stars(user_id, username)
    new_stars = current_stars + reward
    
    # Update stars and last mine time
    update_user_stars(user_id, username, new_stars)
    update_last_mine(user_id)
    
    # Create message based on rarity
    if mineral['name'] == 'Diamond':
        message = f'🎉 **JACKPOT!** 🎉'
    elif mineral['name'] == 'Gold':
        message = f'✨ **RARE FIND!** ✨'
    else:
        message = f'⛏️ **Mining...**'
    
    result_message = f'{message}\n{ctx.author.mention} mined {mineral["emoji"]} **{mineral["name"]}**!\nYou earned **{reward}** noodle stars! ⭐'
    
    # 10% chance of disaster (mine collapse or goblin attack)
    disaster_roll = random.random()
    if disaster_roll < 0.10:
        # Randomly choose between mine collapse and goblin attack
        disaster_type = random.choice(['collapse', 'goblin'])
        
        if disaster_type == 'collapse':
            if has_helmet:
                # Protected by helmet
                result_message += f'\n\n💥 **MINE COLLAPSE!** 💥\n🪖 Your helmet protected you from the collapse!\n*Your helmet was destroyed in the process.*'
                # Remove helmet from inventory
                update_user_inventory(user_id, 'helmet', 0)
            else:
                # Not protected - lose half of wallet stars and ALL items
                stars_lost = new_stars // 2
                new_stars = new_stars - stars_lost
                update_user_stars(user_id, username, new_stars)
                clear_user_inventory(user_id)
                result_message += f'\n\n💥 **MINE COLLAPSE!** 💥\nYou were caught in the collapse and lost **{stars_lost}** stars! 😱\n💀 **All your items were destroyed!**\n💡 *Buy a helmet from the !store to protect yourself!*'
        
        else:  # goblin attack
            if has_sword:
                # Protected by sword
                result_message += f'\n\n👹 **GOBLIN ATTACK!** 👹\n⚔️ You fought off the goblin with your sword!\n*Your sword broke in the battle.*'
                # Remove sword from inventory
                update_user_inventory(user_id, 'sword', 0)
            else:
                # Not protected - lose 75% of wallet stars and ALL items
                stars_lost = int(new_stars * 0.75)
                new_stars = new_stars - stars_lost
                update_user_stars(user_id, username, new_stars)
                clear_user_inventory(user_id)
                result_message += f'\n\n👹 **GOBLIN ATTACK!** 👹\nThe goblin stole **{stars_lost}** stars from you! 😱\n💀 **The goblin destroyed all your items!**\n💡 *Buy a sword from the !store to protect yourself!*'
    
    result_message += f'\nNew balance: **{new_stars}** stars!'
    await ctx.send(result_message)

@bot.command(name='deposit')
async def deposit(ctx, amount: str = None):
    """Deposit noodle stars into your bank for safekeeping"""
    user_id = ctx.author.id
    username = str(ctx.author)
    
    if amount is None:
        await ctx.send(f'❌ {ctx.author.mention}, please specify an amount to deposit! '
                       f'Usage: `!deposit <amount>` or `!deposit all`')
        return
    
    current_stars = get_user_stars(user_id, username)
    current_bank = get_user_bank(user_id)
    
    # Handle "all" keyword
    if amount.lower() == 'all':
        if current_stars <= 0:
            await ctx.send(f'❌ {ctx.author.mention}, you don\'t have any stars to deposit!')
            return
        deposit_amount = current_stars
    else:
        try:
            deposit_amount = int(amount)
        except ValueError:
            await ctx.send(f'❌ {ctx.author.mention}, please enter a valid number or "all"!')
            return
        
        if deposit_amount <= 0:
            await ctx.send(f'❌ {ctx.author.mention}, you must deposit at least 1 star!')
            return
        
        if deposit_amount > current_stars:
            await ctx.send(f'❌ {ctx.author.mention}, you only have **{current_stars}** stars in your wallet!')
            return
    
    # Update balances
    new_stars = current_stars - deposit_amount
    new_bank = current_bank + deposit_amount
    
    update_user_stars(user_id, username, new_stars)
    update_user_bank(user_id, username, new_bank)
    
    await ctx.send(f'🏦 {ctx.author.mention} deposited **{deposit_amount}** stars into the bank!\n'
                   f'💰 Wallet: **{new_stars}** stars\n'
                   f'🏦 Bank: **{new_bank}** stars\n'
                   f'📊 Total: **{new_stars + new_bank}** stars')

@bot.command(name='withdraw')
async def withdraw(ctx, amount: str = None):
    """Withdraw noodle stars from your bank"""
    user_id = ctx.author.id
    username = str(ctx.author)
    
    if amount is None:
        await ctx.send(f'❌ {ctx.author.mention}, please specify an amount to withdraw! '
                       f'Usage: `!withdraw <amount>` or `!withdraw all`')
        return
    
    current_stars = get_user_stars(user_id, username)
    current_bank = get_user_bank(user_id)
    
    # Handle "all" keyword
    if amount.lower() == 'all':
        if current_bank <= 0:
            await ctx.send(f'❌ {ctx.author.mention}, you don\'t have any stars in the bank!')
            return
        withdraw_amount = current_bank
    else:
        try:
            withdraw_amount = int(amount)
        except ValueError:
            await ctx.send(f'❌ {ctx.author.mention}, please enter a valid number or "all"!')
            return
        
        if withdraw_amount <= 0:
            await ctx.send(f'❌ {ctx.author.mention}, you must withdraw at least 1 star!')
            return
        
        if withdraw_amount > current_bank:
            await ctx.send(f'❌ {ctx.author.mention}, you only have **{current_bank}** stars in the bank!')
            return
    
    # Update balances
    new_stars = current_stars + withdraw_amount
    new_bank = current_bank - withdraw_amount
    
    update_user_stars(user_id, username, new_stars)
    update_user_bank(user_id, username, new_bank)
    
    await ctx.send(f'🏦 {ctx.author.mention} withdrew **{withdraw_amount}** stars from the bank!\n'
                   f'💰 Wallet: **{new_stars}** stars\n'
                   f'🏦 Bank: **{new_bank}** stars\n'
                   f'📊 Total: **{new_stars + new_bank}** stars')

@bot.command(name='store')
async def store(ctx):
    """View items available for purchase"""
    embed = discord.Embed(title='🏪 Noodle Star Store', color=discord.Color.gold())
    embed.description = 'Use `!buy <item>` to purchase items!'
    
    embed.add_field(
        name='⛏️ Gold Pickaxe - 500 stars',
        value='Permanently increases your mining luck! Find rare minerals more often.',
        inline=False
    )
    embed.add_field(
        name='🪖 Mining Helmet - 100 stars',
        value='Protects you from one mine collapse. Single use.',
        inline=False
    )
    embed.add_field(
        name='⚔️ Sword - 300 stars',
        value='Protects you from one goblin attack. Single use.',
        inline=False
    )
    embed.add_field(
        name='🥔 Raw Potato - 2 stars',
        value='Reduces mining cooldown to 5 minutes. Single use. Use: `!mine potato`',
        inline=False
    )
    embed.add_field(
        name='🍄 Golden Mushroom - 25 stars',
        value='Mine instantly with no cooldown! Single use. Use: `!mine mushroom`',
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='buy')
async def buy(ctx, *, item_name: str = None):
    """Buy an item from the store"""
    user_id = ctx.author.id
    username = str(ctx.author)
    
    if item_name is None:
        await ctx.send(f'❌ {ctx.author.mention}, please specify an item to buy! Use `!store` to see available items.')
        return
    
    # Normalize item name
    item_name = item_name.lower().strip()
    
    # Define store items
    items = {
        'gold pickaxe': {'price': 500, 'db_name': 'gold_pickaxe', 'emoji': '⛏️', 'display': 'Gold Pickaxe'},
        'pickaxe': {'price': 500, 'db_name': 'gold_pickaxe', 'emoji': '⛏️', 'display': 'Gold Pickaxe'},
        'helmet': {'price': 100, 'db_name': 'helmet', 'emoji': '🪖', 'display': 'Mining Helmet'},
        'mining helmet': {'price': 100, 'db_name': 'helmet', 'emoji': '🪖', 'display': 'Mining Helmet'},
        'sword': {'price': 300, 'db_name': 'sword', 'emoji': '⚔️', 'display': 'Sword'},
        'raw potato': {'price': 2, 'db_name': 'raw_potato', 'emoji': '🥔', 'display': 'Raw Potato'},
        'potato': {'price': 2, 'db_name': 'raw_potato', 'emoji': '🥔', 'display': 'Raw Potato'},
        'golden mushroom': {'price': 25, 'db_name': 'golden_mushroom', 'emoji': '🍄', 'display': 'Golden Mushroom'},
        'mushroom': {'price': 25, 'db_name': 'golden_mushroom', 'emoji': '🍄', 'display': 'Golden Mushroom'}
    }
    
    if item_name not in items:
        await ctx.send(f'❌ {ctx.author.mention}, that item doesn\'t exist! Use `!store` to see available items.')
        return
    
    item = items[item_name]
    current_stars = get_user_stars(user_id, username)
    inventory = get_user_inventory(user_id)
    
    # Check if user has enough stars
    if current_stars < item['price']:
        await ctx.send(f'❌ {ctx.author.mention}, you need **{item["price"]}** stars to buy {item["emoji"]} **{item["display"]}**!\n'
                       f'You only have **{current_stars}** stars.')
        return
    
    # Check if user already has gold pickaxe (permanent item)
    if item['db_name'] == 'gold_pickaxe' and inventory['gold_pickaxe'] > 0:
        await ctx.send(f'❌ {ctx.author.mention}, you already own a {item["emoji"]} **{item["display"]}**!')
        return
    
    # Deduct stars
    new_stars = current_stars - item['price']
    update_user_stars(user_id, username, new_stars)
    
    # Add item to inventory
    current_amount = inventory[item['db_name']]
    update_user_inventory(user_id, item['db_name'], current_amount + 1)
    
    await ctx.send(f'✅ {ctx.author.mention} purchased {item["emoji"]} **{item["display"]}** for **{item["price"]}** stars!\n'
                   f'New balance: **{new_stars}** stars')

@bot.command(name='inventory')
async def inventory(ctx, member: discord.Member = None):
    """Check your inventory"""
    if member is None:
        member = ctx.author
    
    user_id = member.id
    inventory = get_user_inventory(user_id)
    
    embed = discord.Embed(title=f'🎒 {member.display_name}\'s Inventory', color=discord.Color.blue())
    
    items_list = []
    
    if inventory['gold_pickaxe'] > 0:
        items_list.append('⛏️ **Gold Pickaxe** (Permanent)')
    
    if inventory['helmet'] > 0:
        items_list.append(f'🪖 **Mining Helmet** x{inventory["helmet"]}')
    
    if inventory['sword'] > 0:
        items_list.append(f'⚔️ **Sword** x{inventory["sword"]}')
    
    if inventory['raw_potato'] > 0:
        items_list.append(f'🥔 **Raw Potato** x{inventory["raw_potato"]}')
    
    if inventory['golden_mushroom'] > 0:
        items_list.append(f'🍄 **Golden Mushroom** x{inventory["golden_mushroom"]}')
    
    if items_list:
        embed.description = '\n'.join(items_list)
    else:
        embed.description = '*Empty - Visit the !store to buy items!*'
    
    await ctx.send(embed=embed)

# Error handling for permission errors
@add_star.error
@remove_star.error
async def mod_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send('❌ You need moderator permissions to use this command!')

# Run the bot
if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print('Error: DISCORD_BOT_TOKEN environment variable not set!')
        print('Please set your bot token as an environment variable.')
    else:
        bot.run(TOKEN)
