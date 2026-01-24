# noodle-star-bot
Good noodle star discord bot that lets users earn good noodle stars and gamble them!

```
​No Category:
  addstar     Add noodle stars to a user (Moderator only)
  bottomstars Show bottom 10 users with the least noodle stars
  buy         Buy an item from the store
  coinflip    Flip a coin and bet on heads or tails!
  deposit     Deposit noodle stars into your bank for safekeeping
  duel        Challenge another user to a dice duel!
  gamble      Gamble your noodle stars for a chance to win more!
  help        Shows this message
  inventory   Check your inventory
  mine        Mine for minerals to earn noodle stars!
  removestar  Remove noodle stars from a user (Moderator only)
  stars       Check noodle stars for a user
  store       View items available for purchase
  topstars    Show top 10 users with the most noodle stars
  withdraw    Withdraw noodle stars from your bank

Type !help command for more info on a command.
You can also type !help category for more info on a category.
```

### Build
```
docker build -t noodle_bot . 
```

### Run
```
docker run -d --name noodle_bot -e DISCORD_BOT_TOKEN='' -v /$PWD/:/bot noodlebot
```
