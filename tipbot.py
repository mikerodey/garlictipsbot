import traceback
import json
import praw
import pdb
import sys
import MySQLdb
import prawcore
from decimal import *
import subprocess
import shlex
import argparse
import random
from utils import utils
import datetime
import re
import urllib
import os

class logger():

    def logline(self,tolog):
        now = datetime.datetime.now()
        dir = os.path.dirname(__file__)
        with open(os.path.join(dir, "tipbot.log"), "a") as myfile:
            myfile.write("%s: %s\n" % (str(now),tolog))


class tipbot():

    def __init__(self):
        self.utils = utils()
        self.cursor = self.utils.get_mysql_cursor()
        self.reddit = self.utils.connect_to_reddit()
        self.logger = logger()
        self.help = """You can send the following commands to the bot by PM. Do not include the [ and ], these are only to make it easier to read for you. The links below will take you to a pre-filled PM.\n\n
* [signup](https://www.reddit.com/message/compose/?to=grlctipsbot&subject=signup&message=signup) \- Will sign you up, each account can only run this once. If someone tipped you then that will automatically sign you up so you only need to do this if nobody has previously tipped you.
* [balance](https://www.reddit.com/message/compose/?to=grlctipsbot&subject=balance&message=balance) \- Provides your current Garlicoin tips balance.
* [deposit](https://www.reddit.com/message/compose/?to=grlctipsbot&subject=deposit&message=deposit) \- Replies with an address in which you can deposit Garlicoin into to increase your tips balance.
* [withdraw \[address\] \[amount\]](https://www.reddit.com/message/compose/?to=grlctipsbot&subject=withdraw&message=withdraw%20[address]%20[amount]) \- Withdraw from your tips balance to any Garlicoin address the amount you request.
* [tip \[amount\] \[user\]](https://www.reddit.com/message/compose/?to=grlctipsbot&subject=tip&message=tip%20[amount]%20[user]) \- Tips the amount of Garlicoin you request to the user.

To tip a user publicly use /u/grlctipsbot [amount] [user] in a reply.\n\n

If you need any further assistance please PM my human, /u/wcmiker"""

    def does_user_exist(self,username):
        sql = "SELECT * FROM amounts WHERE username=%s"
        self.cursor.execute(sql, (username,))
        result = self.cursor.fetchone()
        if not result:
            return 0
        else:
            return 1

    def check_supported_coin(self,coin):
        supported = ['garlicoin']
        if coin in supported:
            return True
        else:
            return False

    def check_address(self,address):
        #Here we check the address is correct, some users like to give us LTC addresses occasionally...
        if re.search('^(G|X|M)[a-zA-Z0-9]{33}$',address):
            return True
        else:
            return False

    def modify_user_balance(self,pn,username,amt,coin='garlicoin'):
        coin = coin.lower() #Sometimes we're dealing with upper and lower case
        if amt < 0:
            self.logger.logline("%s tried to use a negative number!" % (username))
            raise Exception

        if coin == "garlicoin":
            if pn == "+":
                sql = "UPDATE amounts SET amount=amount+%s WHERE username=%s"
                self.logger.logline("%s's balance has been credited by %s" % (username,amt))
            elif pn == "-":
                sql = "UPDATE amounts SET amount=amount-%s WHERE username=%s"
                self.logger.logline("%s's balance has been deducted by %s" % (username,amt))
            else:
                self.logger.logline("modify_user_balance got strange request. Aborting")
                return 1
        else:
            self.logger.logline("modify_user_balance got strange request. Aborting")
            return 1
        self.cursor.execute(sql, (amt,username,))
        return 0

    def process_withdraw(self,author,address,amt,amtleft,coin,message):
        if amt <= amtleft:
            self.new_withdrawal_request(author,address,amt,coin)
            self.logger.logline("%s has a new withdrawal waiting. AMT: %s %s" % (author,amt,coin))
            return 0
        else:
            self.logger.logline("%s tried to withdraw more than was in their account, AMT: %s" % (author,amt))
            message.reply("Oops, you tried to withdraw more than is in your account. Please send a message with the word 'balance' to get your current balance")
            return 1


    def new_withdrawal_request(self,username,address,amount,coin):
        self.modify_user_balance("-",username,amount,coin)
        sql = "INSERT INTO withdraw (username, address, amount, confirmed, coin) VALUES (%s, %s, %s, 0, %s)"
        self.cursor.execute(sql, (username,address,amount,coin,))

    def give_user_the_tip(self,sender,receiver,addamt,bank,mention): #o.o
        if addamt >= bank+Decimal(0.01):
            try:
                self.logger.logline("%s had %s and tried to give %s. Failed due to not having enough in bank." % (sender,bank,addamt))
                self.reddit.comment(id=mention.id).reply("Sorry! You don't have enough in your account and we aren't a garlic bank! PM me with the word 'deposit' and I will send you instructions to get more delicious garlic into your account.")
                return 2
            except:
                self.logger.logline("Bot was unable to comment, perhaps rate limited?")
        else:
            self.modify_user_balance("-",sender,addamt)
            self.add_history_entry(sender,receiver,addamt,mention.id)

            if self.does_user_exist(receiver) == 1:
                self.modify_user_balance("+",receiver,addamt)
                mstr = str(receiver)+" "+str(addamt) #Probably no need for this, holdover from recode.
                try:
                    self.reddit.comment(id=mention.id).reply("Yay! You gave /u/%s Garlicoin, hopefully they can now create some tasty garlic bread. \n\n[Need help?](https://np.reddit.com/message/compose/?to=grlctipsbot&subject=help&message=help) \n\n[Garlicoin subreddit](https://np.reddit.com/r/garlicoin/)" % (mstr))
                except:
                    self.logger.logline("Reddit doesn't seem to be responding right now...died on comment for existing user.")
                    traceback.print_exc()
            else:
                self.create_account(receiver)
                self.modify_user_balance("+",receiver,addamt)
                try:
                    self.reddit.comment(id=mention.id).reply("Yay! You gave /u/%s %s garlicoin, hopefully they can now create some tasty garlic bread. If %s doesn't know what it is, they should visit the [Garlicoin subreddit](https://np.reddit.com/r/garlicoin/) \n\n[Need help?](https://np.reddit.com/message/compose/?to=grlctipsbot&subject=help&message=help)" % (receiver, addamt, receiver))
                    self.utils.send_message(receiver,'Welcome to Garlicoin',"%s gave you some Garlicoin, we have added your new found riches to an account in your name on grlctipsbot. You can get the balance by messaging this bot with the word balance on its own (in a new message, not as a reply to this one!). [Click here for a pre-filled PM for the balance command](https://www.reddit.com/message/compose/?to=grlctipsbot&subject=balance&message=balance).\n\nYou can also send tips to others or withdraw to your own garlicoin wallet, send the bot the word [help](https://www.reddit.com/message/compose/?to=grlctipsbot&subject=help&message=help) to see how to do this. If there are any issues please PM /u/wcmiker" % mention.author)
                except:
                    self.logger.logline("Reddit doesn't seem to be responding right now...died on comment & sendmsg for new user.")
                    traceback.print_exc()

    def give_user_the_tip_pm(self,sender,receiver,addamt,bank,message):
        if addamt >= bank+Decimal(0.01):
            try:
                message.reply("Sorry! You don't have enough in your account and we aren't a garlic bank! PM me with the word 'deposit' and I will send you instructions to get more delicious garlic into your account.")
                self.logger.logline("%s had %s and tried to give %s. Failed." % (sender,bank,addamt))
                return 2
            except:
                self.logger.logline("Bot was unable to comment, perhaps rate limited?")
        else:
            self.modify_user_balance("-",sender,addamt)
            self.add_history_entry(sender,receiver,addamt,message.id)

            if self.does_user_exist(receiver) == 1:
                self.modify_user_balance("+",receiver,addamt)
                mstr = str(receiver)+" "+str(addamt) #Probably no need for this, holdover from recode.
                try:
                    message.reply("Yay! You gave /u/%s Garlicoin, hopefully they can now create some tasty garlic bread." % (mstr))
                    self.utils.send_message(receiver,'Welcome to Garlicoin',"%s gave you %s Garlicoin via PM" % (message.author, addamt))
                except:
                    self.logger.logline("Reddit doesn't seem to be responding right now...died on comment for existing user.")
                    traceback.print_exc()
            else:
                self.create_account(receiver)
                self.modify_user_balance("+",receiver,addamt)
                try:
                    message.reply("Yay! You gave /u/%s %s Garlicoin, hopefully they can now create some tasty garlic bread. If %s doesn't know what it is, they should visit the [Garlicoin subreddit](https://www.reddit.com/r/garlicoin/)" % (receiver, addamt, receiver))
                    self.utils.send_message(receiver,'Welcome to Garlicoin',"%s gave you some Garlicoin, we have added your new found riches to an account in your name on grlctipsbot. You can get the balance by messaging this bot with the word balance on its own (in a new message, not as a reply to this one!). [Click here for a pre-filled PM for the balance command](https://www.reddit.com/message/compose/?to=grlctipsbot&subject=balance&message=balance).\n\nYou can also send tips to others or withdraw to your own garlicoin wallet, send the bot the word [help](https://www.reddit.com/message/compose/?to=grlctipsbot&subject=help&message=help) to see how to do this. If there are any issues please PM /u/wcmiker" % message.author)
                except:
                    self.logger.logline("Reddit doesn't seem to be responding right now...died on comment & sendmsg for new user.")
                    traceback.print_exc()

    def new_deposit(self,username,coin='garlicoin'): #If the user hasn't deposited with us before, he gets a flag created, else just do nothing because the flag is already there.
        sql = "SELECT * FROM deposits WHERE username=%s AND coin=%s"
        self.cursor.execute(sql, (username,coin,))
        if not self.cursor.rowcount:
            sql = "INSERT INTO deposits (username, amount, txs, coin) VALUES (%s, 0, 0, %s)"
            self.cursor.execute(sql, (username,coin,))
    
    def get_amount_for_user(self,username):
        sql = "SELECT * FROM amounts WHERE username=%s"
        self.cursor.execute(sql, (username,))
        return Decimal(self.cursor.fetchone()[2])

    def check_mentions(self):
        unread = []
        for mention in self.reddit.inbox.mentions(limit=25):
            if mention.new == True:
                unread.append(mention)
                try:
                    self.logger.logline("Processing mention: %s by %s" % (mention.id,mention.author)) 
                    self.process_mention(mention)
                except:
                    #self.reddit.comment(id=mention.id).reply("Oops, something went wrong. Do you have an account with the bot? If not send 'signup' to me by PM. If you do have an account I may be having issues, please try again later.")
                    traceback.print_exc()
        self.reddit.inbox.mark_read(unread)
        del unread[:] #Probably not needed after the recode, since it's a local var, but still good to clean up I suppose....
    
    def create_account(self,username):
        sql = "INSERT INTO amounts (username,amount) VALUES (%s, 0)"
        self.cursor.execute(sql, (username,))

    def add_history_entry(self,sender,receiver,amt,mention):
        sql = "INSERT INTO history (sender, recv, amount, mention) VALUES (%s, %s, %s, %s)"
        self.cursor.execute(sql, (sender,receiver,amt,mention,))

    def get_new_address(self,username,coin):
        return subprocess.check_output(shlex.split('%s/bin/%s-cli -rpcuser=%s -rpcpassword=%s getnewaddress grlctipsbot-%s' % (self.utils.config['other']['full_dir'],coin,self.utils.config['grlc']['rpcuser'],self.utils.config['grlc']['rpcpassword'],username))).decode('UTF-8').rstrip('\n')

    def process_mention(self,mention):
        #print('{}\n{}\n'.format(mention.author, mention.body))
        self.logger.logline('{}\n{}\n'.format(mention.author, mention.body))
        todo = mention.body.split()
        todo_lower = [item.lower() for item in todo]
        try:
            needle = todo_lower.index("/u/grlctipsbot") #Need to find this in multiple ways, currently tripping on u/ and capital letters.
        except:
            needle = todo_lower.index("u/grlctipsbot")
        sender = mention.author.name.replace("\\", "")
        addamt = todo[needle+1]
        receiver = todo[needle+2].replace("\\", "")

        #Ensure we don't have /u/ on receiver
        if receiver.lower().count("/u/") == 1:
            receiver = receiver.replace(receiver[:3],'')
        addamt = Decimal(addamt)

        bank = self.get_amount_for_user(sender)

        self.give_user_the_tip(sender,receiver,addamt,bank,mention) #o.o

        #Do the calculations, giving a little leeway here.
                
    def process_command(self,message,command):
        #First we check whether the user wants to signup, if so let's process that...
        command = command.lower()
        author = message.author
        self.logger.logline("%s issued command %s" % (author,command))
        userexists = self.does_user_exist(author)
        if command not in ['signup'] and not userexists:
            message.reply("Hi! This bot doesn't know who you are. Please PM the word 'signup' in a new message if you would like to start using the bot. If you think you should have a balance here please PM my human /u/wcmiker")
            return 2
        if command == "signup":
            if userexists == 0:
                self.create_account(author)
                message.reply("Hi! You have successfully signed up! You can check by sending the word balance in a new message to /u/grlctipsbot or send deposit to deposit some delicious garlic")
            else:
                message.reply("Hi. You already have an account so we cannot sign you up again. Please send the word balance in a new message to /u/grlctipsbot to find your balance")
        elif command == "balance":
            balance = self.get_amount_for_user(author)
            self.logger.logline("%s requested their balance. AMT: %s" % (author,balance))
            message.reply("Your Garlicoin balance is %s" % balance)
        elif command == "deposit":
            self.new_deposit(author)
            addy = self.get_new_address(author,"garlicoin")
            self.logger.logline("%s was assigned address %s" % (author,addy))
            message.reply("Hi! Our cooks have generated a deposit address just for you, it is: *%s* \n\nOnce you have sent some Garlicoin please be patient while it appears in your account." % (addy))
        elif command == "help":
            message.reply(self.help)
        else:
            message.reply("Sorry! I did not understand the command you gave. Please write a new PM (not reply) with help and I will reply with what I accept.")

    def process_multi_command(self,message,command):
        author = message.author
        self.logger.logline("%s issued command %s" % (author,command))
        userexists = self.does_user_exist(author)
        if userexists == 0:
            self.logger.logline("%s tried to issue command %s while not signed up" % (author,command))
            message.reply("Hi! This bot doesn't know who you are. Please PM the word 'signup' in a new message if you would like to start using the bot. If you think you should have a balance here please PM my human /u/wcmiker")
        msgsplit = message.body.split()
        msgsplit[0] = msgsplit[0].lower()
        self.logger.logline("%s issued command %s" % (author,message.body))
        if msgsplit[0] == "deposit":
            coin = msgsplit[1].lower()
            if not self.check_supported_coin(coin):
                message.reply("You tried to deposit an unsupported coin, right now we only support Garlicoin")
                raise Exception
            self.new_deposit(author,coin)
            addy = self.get_new_address(author,coin)
            self.logger.logline("%s was assigned address %s" % (author,addy))
            message.reply("Hi! Our cooks have generated a deposit address just for you, it is: *%s* \n\nOnce you have sent some %s please be patient while it appears in your account." % (addy,coin))

        if msgsplit[0] == "withdraw":
            try:
                address = msgsplit[1]
                amt = Decimal(msgsplit[2])
            except:
                message.reply("You don't seem to have sent me an amount or address, please resend in the format withdraw address amount - PM /u/wcmiker for help if you need it.")
                self.logger.logline("%s sent invalid amount" % (author))
                return 1
            try:
                if not self.check_address(address):
                    raise Exception #Objection!

                if address.startswith("G") or address.startswith("g") or address.startswith("M"): #Our favourite coin, right?
                    amtleft = self.get_amount_for_user(author)
                    self.process_withdraw(author,address,amt,amtleft,"garlicoin",message)

            except:
                message.reply("It appears you tried to send a withdrawal request, but we couldn't figure out the format. Please resend it as 'withdraw address amount' - It's also possible you gave an invalid Garlicoin address, please check it.")
                traceback.print_exc()
        elif msgsplit[0] == "tip":
            #The user wants to tip another privately, that's cool, we can do that too.
            try:
                addamt = Decimal(msgsplit[1])
                receiver = msgsplit[2]
            except:
                message.reply("Hi, the bot did not understand your request. Please send tips in the format 'tip amount user' as a new message, without the quotes.")

            #Ensure our decimal is *not* a negative number.
            if addamt < 0:
                message.reply("You tried to use a negative number, you'll make people sad if you steal their precious garlic...")
                self.logger.logline("%s tried to use a negative number!" % (author))
                return 1
        
            bank = self.get_amount_for_user(author)
            self.give_user_the_tip_pm(author,receiver,addamt,bank,message)


    def check_messages(self):
        #Alright, here's where things get a little fun/messy. 
        unread = []
        for indmessage in self.reddit.inbox.messages(limit=5):
            if indmessage.new == True:
                unread.append(indmessage)
                try:
                    command = indmessage.body
                    if not ' ' in command:
                        #If there's only one word it's an information command, eg deposit/balance/help
                        self.process_command(indmessage,command)
                    else:
                        self.process_multi_command(indmessage,command)
                except Exception as ex:
                    print("Something went wrong processing commands...skipping this one")
                    traceback.print_exc()
        self.reddit.inbox.mark_read(unread)



    def main(self):

        try:
            me = self.reddit.user.me()
        except Exception as ex:
            print("Something went wrong. Please check Reddit for details")
            traceback.print_exc()
            sys.exit()

        if me != "grlctipsbot":
            print("Not the correct user. Aborting!")

        #First we check any mentions in comments so we can do the tipping, then check the private messages of the bot.
        self.check_mentions()
        self.check_messages()
        print("Done, next round in 15")


tipobj = tipbot()
tipobj.main()
