# UNO CARDS:
# colors: Blue, Green, Red, Yellow
# 0: 1x each color -> 4 cards
# 1-9: 2x each color -> 72 cards
# Skip: 2x each color -> 8 cards
# Reverse: 2x each color -> 8 cards
# Draw Two: 2x each color -> 8 cards
# Wild: 4 cards
# Wild Draw Four:  4 cards

# DM message:
#   chat:
#       @player1: message1
#       @player2: message2
#            ...
#   Top card: yellow 1
#   Turn: @player
#   Your cards:
#       A: blue 1
#       B: green 1
#       C: red 1
#       D: yellow 1
#       E: special 1
#       F: special 2
#          ...
import asyncio
from string import ascii_lowercase

import discord

from Other.variables import *
from Minigames.multiplayer_minigame import MultiMiniGame

class Card:
    def __init__(self, color, value):
        self.color = color
        self.value = value


class UnoDeck:
    def __init__(self):
        self.cards = list()
        self.draw_pile = list()
        self.discard_pile = list()
        for color in Variables.colors_uno.keys():
            self.cards.append(Card(color, 0))
            self.cards.append(Card("White", "Wild"))
            self.cards.append(Card("White", "Wild Draw 4"))
        for j in range(2):
            for i in range(1,10):
                for color in Variables.colors_uno.keys():
                    self.cards.append(Card(color, i))
            for color in Variables.colors_uno.keys():
                self.cards.append(Card(color, "Skip"))
                self.cards.append(Card(color, "Reverse"))
                self.cards.append(Card(color, "Draw 2"))
        self.draw_pile = self.cards
        random.shuffle(self.draw_pile)
        self.discard_pile.insert(0, self.draw_pile.pop())

    def reshuffle(self):
        self.draw_pile = self.discard_pile
        self.discard_pile = self.discard_pile[0]

    def draw(self):
        if len(self.draw_pile) == 0:
            self.reshuffle()
            self.draw()
        return self.draw_pile.pop()


class Player:
    def __init__(self, player, uno):
        self.uno = uno
        self.hand = list()
        self.player = player
        self.name = self.player.name
        self.chat_dm = None
        self.game_dm = None
        self.page = 1
        self.page_max = 1
        self.has_uno = False
        self.said_uno = False
        self.draw_two = False
        self.skipped = False
        self.choosing_color = False
        self.took_card = False

    async def send_dm(self, game, chat):
        channel = await self.player.create_dm()
        self.chat_dm = await channel.send("updating chat...")
        self.game_dm = await channel.send("updating game...")
        for i in range(len(self.hand)):
            if self.choosing_color:
                if self.hand[i].color == "White":
                    game += "        {0} {1}\n".format(Variables.white["White"],
                                                       self.hand[i].value)
                else:
                    game += "        {0} {1}\n".format(Variables.colors_uno[self.hand[i].color],
                                                       self.hand[i].value)
            elif self.uno.is_valid_move(self.hand[i]):
                if self.hand[i].color == "White":
                    game += "{0}  {1} {2}\n".format(Variables.DICT_ALFABET[ascii_lowercase[i]],
                                                    Variables.white["White"],
                                                    self.hand[i].value)
                else:
                    game += "{0}  {1} {2}\n".format(Variables.DICT_ALFABET[ascii_lowercase[i]],
                                                    Variables.colors_uno[self.hand[i].color],
                                                    self.hand[i].value)
                await self.game_dm.add_reaction(Variables.DICT_ALFABET[ascii_lowercase[i]])
            else:
                try:
                    game += "        {0} {1}\n".format(Variables.colors_uno[self.hand[i].color],
                                                       self.hand[i].value)
                except:
                    game += "        {0} {1}\n".format(Variables.white["White"],
                                                       self.hand[i].value)
        if self.choosing_color:
            for color in Variables.colors_uno.values():
                await self.game_dm.add_reaction(color)
        elif self.draw_two:
            await self.game_dm.add_reaction(Variables.INC_EMOJI2)  # you took the cards you should take (from draw two cards...)
        elif self.took_card:
            await self.game_dm.add_reaction(Variables.FORWARD_EMOJI)  # you took one card, and turn to next player
        else:
            await self.game_dm.add_reaction(Variables.STOP_EMOJI)  # take one card

        await self.game_dm.edit(content=game)
        await self.chat_dm.edit(content=chat)

    async def edit_game_dm(self, game):
        for i in range(len(self.hand)):
            if self.hand[i].color == "White":
                game += "        {0} {1}\n".format(Variables.white["White"], self.hand[i].value)
            else:
                game += "        {0} {1}\n".format(Variables.colors_uno[self.hand[i].color], self.hand[i].value)
        await self.game_dm.edit(content=game)

    async def update_chat(self, chat):
        if self.chat_dm is None:
            channel = await self.player.create_dm()
            self.chat_dm = await channel.send(chat)
        else:
            await self.chat_dm.edit(content=chat)

    def draw(self, card):
        self.hand.append(card)

    def check_uno(self):
        if len(self.hand) == 1:
            self.has_uno = True
            return
        self.has_uno = False
        self.said_uno = False
        return

    async def game_finished(self, winner):
        channel = await self.player.create_dm()
        if winner == self.player.name:
            content = "Congratulations! You won the game!"
        else:
            content = "{0} won the game!".format(winner)
        self.chat_dm = await channel.send(content)

    def has_won(self):
        if len(self.hand) == 0:
            return True
        return False


class Uno(MultiMiniGame):
    def __init__(self, bot, game_name, msg, players):
        super().__init__(bot, game_name, msg, players)
        self.chat = list()
        self.deck = UnoDeck()
        self.top_color = self.deck.discard_pile[0].color
        self.dms = list()

        self.players_uno_obj = list()
        self.player_ids = list()
        for player in players:
            self.players_uno_obj.append(Player(player, self))
            self.player_ids.append(player.id)
        n = random.randint(0, len(self.players_uno_obj) - 1)
        self.turn = n
        self.cards_to_draw = 0
        self.action_on_startup = False

    async def start_game(self):
        for player in self.players_uno_obj:
            channel = await player.player.create_dm()
            player.chat_dm = await channel.send(self.get_chat())
            player.game_dm = await channel.send("updating game...")
            self.dms.append(player.game_dm.id)

        for i in range(7):
            for player in self.players_uno_obj:
                player.draw(self.deck.draw())

        while self.deck.discard_pile[0].value == "Wild Draw 4":
            card = self.deck.draw()
            self.deck.discard_pile.insert(0, card)

        if self.deck.discard_pile[0].value == "Draw 2":
            self.draw_two()
        elif self.deck.discard_pile[0].value == "Reverse":
            return self.reverse_card()
        elif self.deck.discard_pile[0].value == "Wild":
            self.action_on_startup = True
            return await self.wild_card()
        elif self.deck.discard_pile[0].value == "Skip":
            self.turn = (self.turn + 1) % len(self.players_uno_obj)

        await self.update_game_dms()

    async def update_game(self, reaction, user):
        p = self.players_uno_obj[self.turn]

        if self.terminated:
            return

        if reaction.emoji == Variables.INC_EMOJI2:
            for i in range(self.cards_to_draw):
                p.draw(self.deck.draw())
            self.cards_to_draw = 0
            p.draw_two = False
        elif reaction.emoji == Variables.STOP_EMOJI:
            p.took_card = True
            p.draw(self.deck.draw())
            await self.update_game_dms()
            return

        elif p.choosing_color and reaction.emoji in Variables.colors_uno.values():
            for key, value in  Variables.colors_uno.items():
                if reaction.emoji == value:
                    self.top_color = key
                    break
            p.choosing_color = False
            if self.action_on_startup:
                self.action_on_startup = False
                await self.update_game_dms()
                return

        elif reaction.emoji in Variables.DICT_ALFABET.values():
            letter = self.get_letter_from_emoji(reaction.emoji)
            card_index = ascii_lowercase.index(letter)
            card = self.players_uno_obj[self.turn].hand[card_index]
            if self.is_valid_move(card):
                self.players_uno_obj[self.turn].hand.remove(card)
                self.deck.discard_pile.insert(0, card)
                self.top_color = card.color
                if card.value == "Reverse":
                    self.reverse_card()
                elif card.value == "Wild":
                    return await self.wild_card()
                elif card.value == "Wild Draw 4":
                    return await self.wild_draw_four_card()
                elif card.value == "Draw 2":
                    self.draw_two()
                elif card.value == "Skip":
                    self.players_uno_obj[(self.turn + 1) % len(self.players_uno_obj)].skipped = True

        p.took_card = False
        self.players_uno_obj[self.turn].check_uno()

        if self.players_uno_obj[self.turn].has_won():
            await self.game_won()
            return

        self.turn = (self.turn + 1) % len(self.players_uno_obj)
        if self.players_uno_obj[self.turn].skipped:
            self.players_uno_obj[self.turn].skipped = False
            self.turn = (self.turn + 1) % len(self.players_uno_obj)
        await self.update_game_dms()

    def get_letter_from_emoji(self, emoji):
        letter = ""
        for letter, emo in Variables.DICT_ALFABET.items():
            if emo == emoji:
                break
        return letter

    def draw_two(self):
        if self.players_uno_obj[self.turn].draw_two:
            self.players_uno_obj[self.turn].draw_two = False
        self.players_uno_obj[(self.turn + 1) % len(self.players_uno_obj)].draw_two = True
        self.cards_to_draw += 2

    def reverse_card(self):
        self.players_uno_obj.reverse()
        self.turn = len(self.players_uno_obj) - 1 - self.turn

    async def wild_card(self):
        self.players_uno_obj[self.turn].choosing_color = True
        self.players_uno_obj[self.turn].check_uno()
        if self.players_uno_obj[self.turn].has_won():
            await self.game_won()
            return
        await self.update_game_dms()

    async def wild_draw_four_card(self):
        if self.players_uno_obj[self.turn].draw_two:
            self.players_uno_obj[self.turn].draw_two = False
        self.cards_to_draw += 4
        for i in range(self.cards_to_draw):
            self.players_uno_obj[(self.turn + 1) % len(self.players_uno_obj)].draw(self.deck.draw_pile.pop())
        self.cards_to_draw = 0
        self.players_uno_obj[(self.turn + 1) % len(self.players_uno_obj)].skipped = True
        self.players_uno_obj[self.turn].choosing_color = True
        self.players_uno_obj[self.turn].check_uno()

        if self.players_uno_obj[self.turn].has_won():
            await self.game_won()
            return
        await self.update_game_dms()

    async def update_game_dms(self):
        game = self.get_board()
        chat = self.get_chat()
        for i in range(len(self.players_uno_obj)):
            if i == self.turn:
                await self.players_uno_obj[i].game_dm.delete()
                await self.players_uno_obj[i].chat_dm.delete()
                await self.players_uno_obj[i].send_dm(game, chat)
                self.dms[self.turn] = self.players_uno_obj[i].game_dm.id
            else:
                await self.players_uno_obj[i].edit_game_dm(game)

        await self.wait_for_player()

    async def game_won(self):
        self.terminated = True
        await self.update_game_dms()
        winner = self.players_uno_obj[self.turn].name
        self.index_winner = self.turn
        for player in self.players_uno_obj:
            await player.game_finished(winner)
        await self.msg.edit(content=winner + " won the uno minigame!")
        await self.end_game()

    def is_valid_move(self, card: Card):
        top_card = self.deck.discard_pile[0]
        if top_card.value == "Draw 2" and self.cards_to_draw != 0:
            if card.value == "Draw 2":
                return True
            else:
                return False
        if card.color == self.top_color or card.value == top_card.value or card.value == "Wild" or card.value == "Wild Draw 4":
            return True
        return False

    def get_board(self):
        text=  "--- UNO ---\n"
        try:
            text += "\n+ TOP CARD:   {0}  {1}".format(Variables.colors_uno[self.top_color], self.deck.discard_pile[0].value)
        except:
            text += "\n+ TOP CARD:   {0}  {1}".format(Variables.white[self.top_color], self.deck.discard_pile[0].value)
        if self.cards_to_draw != 0:
            text += "\n\n+ CARDS TO DRAW: {0}\n\n".format(self.cards_to_draw)
        else:
            text += "\n\n"
        text += "+ TURN:  "
        for i in range(len(self.players_uno_obj)):
            text += " {0} ({1}) ->".format(self.players_uno_obj[(self.turn + i) % len(self.players_uno_obj)].name, len(self.players_uno_obj[(self.turn + i) % len(self.players_uno_obj)].hand))
        text = text[:-2]
        text += "\n\n+ YOUR CARDS: \n"
        return text

    async def update_chat(self, message):
        if message.content.lower() == "uno":
            for player in self.players_uno_obj:
                if player.name == message.author.name:
                    player.said_uno = True
        if message.content.lower() == "no uno":
            for player in self.players_uno_obj:
                if player.has_uno and not player.said_uno:
                    index = self.players_uno_obj.index(player)
                    if not (self.turn + 1) % len(self.players_uno_obj) == index:
                        player.has_uno = False
                        player.draw(self.deck.draw())
                        player.draw(self.deck.draw())
        self.chat.append([message.author, message.content])
        chat = self.get_chat()
        while len(chat) > 2000:
            del self.chat[0]
            chat = self.get_chat()
        for player in self.players_uno_obj:
            await player.update_chat(chat)
        await self.wait_for_player()

    def get_chat(self):
        content = "--- CHAT ---\n"
        if len(self.chat) != 0:
            for msg in self.chat:
                content += "{0}:  {1}\n".format(msg[0].name, msg[1])
        return content

    async def wait_for_player(self):
        do_r = asyncio.create_task(self.await_reaction())
        do_m = asyncio.create_task(self.await_message())

        done, pending = await asyncio.wait([do_r, do_m], return_when=asyncio.FIRST_COMPLETED)

        for pend in pending:
            pend.cancel()

        if do_r in done:
            reaction, user = do_r.result()
            if reaction is None: return
            await self.update_game(reaction, user)
        if do_m in done:
            message = do_m.result()
            await self.update_chat(message)

    async def await_message(self):
        message = await self.bot.wait_for("message", check=lambda m: isinstance(m.channel, discord.DMChannel)
                                                                                  and m.author.id in self.player_ids)
        return message

    async def await_reaction(self):
        try:
            reaction, user = await self.bot.wait_for("reaction_add", check=lambda r, u: u.id == self.players_uno_obj[self.turn].player.id,
                                                     timeout=Variables.TIMEOUT)
            return reaction, user
        except asyncio.TimeoutError:
            await self.end_game(True)
            return None, None