#!/usr/bin/env python3
'''A script to find and react to BBH commands in comments'''
from beem import Hive
from beem.account import Account
from beem.blockchain import Blockchain
from beem.comment import Comment
import beem.instance
import os
import jinja2
import configparser
import time
import requests
import sqlite3
from datetime import date
from hiveengine.api import Api
from hiveengine.wallet import Wallet

### Global configuration

BLOCK_STATE_FILE_NAME = 'lastblock.txt'

config = configparser.ConfigParser()
config.read('bbhbot.config')

ENABLE_COMMENTS = config['Global']['ENABLE_COMMENTS'] == 'True'
ENABLE_TRANSFERS = config['HiveEngine']['ENABLE_TRANSFERS'] == 'True'

ACCOUNT_NAME = config['Global']['ACCOUNT_NAME']
ACCOUNT_POSTING_KEY = config['Global']['ACCOUNT_POSTING_KEY']
HIVE_API_NODE = config['Global']['HIVE_API_NODE']
HIVE = Hive(node=[HIVE_API_NODE], keys=[config['Global']['ACCOUNT_ACTIVE_KEY']])
HIVE.chain_params['chain_id'] = 'beeab0de00000000000000000000000000000000000000000000000000000000'
beem.instance.set_shared_blockchain_instance(HIVE)

setApi = Api(url = "https://engine.rishipanthee.com/")

ACCOUNT = Account(ACCOUNT_NAME)
TOKEN_NAME = config['HiveEngine']['TOKEN_NAME']

BOT_COMMAND_STR = config['Global']['BOT_COMMAND_STR']

SQLITE_DATABASE_FILE = 'bbhbot.db'
SQLITE_GIFTS_TABLE = 'bbh_bot_gifts'

### END Global configuration


print('Loaded configs:')
for section in config.keys():
    for key in config[section].keys():
        if '_key' in key: continue # don't log posting/active keys
        print('%s : %s = %s' % (section, key, config[section][key]))


# Markdown templates for comments
comment_fail_template = jinja2.Template(open(os.path.join('templates','comment_fail.template'),'r').read())
comment_outofstock_template = jinja2.Template(open(os.path.join('templates','comment_outofstock.template'),'r').read())
comment_success_template = jinja2.Template(open(os.path.join('templates','comment_success.template'),'r').read())
comment_daily_limit_template = jinja2.Template(open(os.path.join('templates','comment_daily_limit.template'),'r').read())

### sqlite3 database helpers

def db_create_tables():
    db_conn = sqlite3.connect(SQLITE_DATABASE_FILE)
    c = db_conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS %s(date TEXT NOT NULL, invoker TEXT NOT NULL, recipient TEXT NOT NULL, block_num INTEGER NOT NULL);" % SQLITE_GIFTS_TABLE)

    db_conn.commit()
    db_conn.close()


def db_save_gift(date, invoker, recipient, block_num):

    db_conn = sqlite3.connect(SQLITE_DATABASE_FILE)
    c = db_conn.cursor()

    c.execute('INSERT INTO %s VALUES (?,?,?,?);' % SQLITE_GIFTS_TABLE, [
        date,
        invoker,
        recipient,
        block_num
        ])
    db_conn.commit()
    db_conn.close()


def db_count_gifts(date, invoker):

    db_conn = sqlite3.connect(SQLITE_DATABASE_FILE)
    c = db_conn.cursor()

    c.execute("SELECT count(*) FROM %s WHERE date = '%s' AND invoker = '%s';" % (SQLITE_GIFTS_TABLE,date,invoker))
    row = c.fetchone()

    db_conn.commit()
    db_conn.close()

    return row[0]


def db_count_gifts_unique(date, invoker, recipient):

    db_conn = sqlite3.connect(SQLITE_DATABASE_FILE)
    c = db_conn.cursor()

    c.execute("SELECT count(*) FROM %s WHERE date = '%s' AND invoker = '%s' AND recipient = '%s';" % (SQLITE_GIFTS_TABLE,date,invoker,recipient))
    row = c.fetchone()

    db_conn.commit()
    db_conn.close()

    return row[0]


def get_account_posts(account):
    acc = Account(account)
    account_history = acc.get_account_history(-1, 5000)
    account_history = [x for x in account_history if x['type'] == 'comment' and not x['parent_author']]

    return account_history


def get_account_details(account):
    acc = Account(account)
    return acc.json()


def get_block_number():

    if not os.path.exists(BLOCK_STATE_FILE_NAME):
        return None

    with open(BLOCK_STATE_FILE_NAME, 'r') as infile:
        block_num = infile.read()
        block_num = int(block_num)
        return block_num


def set_block_number(block_num):

    with open(BLOCK_STATE_FILE_NAME, 'w') as outfile:
        outfile.write('%d' % block_num)


def has_already_replied(post):

    for reply in post.get_replies():
        if reply.author == ACCOUNT_NAME:
            return True

    return False


def post_comment(parent_post, author, comment_body):
    if ENABLE_COMMENTS:
        print('Commenting!')
        parent_post.reply(body=comment_body, author=author)
        # sleep 3s before continuing
        time.sleep(3)
    else:
        print('Debug mode comment:')
        print(comment_body)


def daily_limit_reached(invoker_name, level=1):

    today = str(date.today())
    today_gift_count = db_count_gifts(today, invoker_name)

    access_level = 'AccessLevel%d' % level

    if today_gift_count >= int(config[access_level]['MAX_DAILY_GIFTS']):
        return True

    return False


def daily_limit_unique_reached(invoker_name, recipient_name, level=1):

    today = str(date.today())
    today_gift_count_unique = db_count_gifts_unique(today, invoker_name, recipient_name)

    access_level = 'AccessLevel%d' % level

    if today_gift_count_unique >= int(config[access_level]['MAX_DAILY_GIFTS_UNIQUE']):
        return True

    return False


def get_invoker_level(invoker_name):

    # check how much TOKEN the invoker has
    wallet_token_info = Wallet(invoker_name, api=setApi).get_token(TOKEN_NAME)

    try:
        invoker_balance = float(wallet_token_info['balance'])
    except:
        invoker_balance = float(0)

    # does invoker meet level 4 requirements?
    min_balance = float(config['AccessLevel4']['MIN_TOKEN_BALANCE'])

    if invoker_balance >= min_balance:
        return 4

    # does invoker meet level 3 requirements?
    min_balance = float(config['AccessLevel3']['MIN_TOKEN_BALANCE'])

    if invoker_balance >= min_balance:
        return 3

    # does invoker meet level 2 requirements?
    min_balance = float(config['AccessLevel2']['MIN_TOKEN_BALANCE'])

    if invoker_balance >= min_balance:
        return 2

    # does invoker meet level 1 requirements?
    min_balance = float(config['AccessLevel1']['MIN_TOKEN_BALANCE'])

    if invoker_balance >= min_balance:
        return 1

    else:
        return 0


def is_block_listed(name):

    return name in config['HiveEngine']['GIFT_BLOCK_LIST'].split(',')


def can_gift(invoker_name, recipient_name):

    if is_block_listed(invoker_name):
        return False

    if is_block_listed(recipient_name):
        return False

    level = get_invoker_level(invoker_name)

    if level == 0:
        return False

    if daily_limit_reached(invoker_name, level):
        return False

    if daily_limit_unique_reached(invoker_name, recipient_name, level):
        return False

    return True


# Hive Posts Stream and main process

def main():

    db_create_tables()

    blockchain = Blockchain(node=[HIVE_API_NODE])

    start_block = get_block_number()

    for op in blockchain.stream(opNames=['comment'], start=start_block, threading=False, thread_num=1):

        set_block_number(op['block_num'])

        # it's a comment or post

        # how are there posts with no author?
        if 'author' not in op.keys():
            continue

        author_account = op['author']
        parent_author = op['parent_author']
        reply_identifier = '@%s/%s' % (author_account,op['permlink'])

        if parent_author == ACCOUNT_NAME:
            message_body = '%s replied with: %s' % (author_account,op['body'])

        # skip comments that don't include the bot's command prefix
        if BOT_COMMAND_STR not in op['body']:
            continue
        else:
            debug_message = 'Found %s command: https://peakd.com/%s in block %s' % (BOT_COMMAND_STR, reply_identifier, op['block_num'])
            print(debug_message)

        # no self-tipping
        if author_account == parent_author:
            continue

        # bail out if the parent_author (recipient) is missing
        if not parent_author:
            continue

        # skip tips sent to the bot itself
        if parent_author == ACCOUNT_NAME:
            continue

        message_body = '%s asked to send a tip to %s' % (author_account, parent_author)

        try:
            post = Comment(reply_identifier)
        except beem.exceptions.ContentDoesNotExistsException:
            print('post not found!')
            continue

        # if we already commented on this post, skip
        if has_already_replied(post):
            print("We already replied!")
            continue

        invoker_level = get_invoker_level(author_account)

        if is_block_listed(author_account) or is_block_listed(parent_author):
            continue

        # Check if the invoker meets requirements to use the bot
        if not can_gift(author_account, parent_author):
            print('Invoker doesnt meet minimum requirements')

            min_balance = float(config['AccessLevel1']['MIN_TOKEN_BALANCE'])

            if invoker_level > 0 and daily_limit_reached(author_account,invoker_level):
                # Check if invoker has reached daily limits
                max_daily_gifts = config['AccessLevel%s' % invoker_level]['MAX_DAILY_GIFTS']

                comment_body = comment_daily_limit_template.render(token_name=TOKEN_NAME, target_account=author_account, max_daily_gifts=max_daily_gifts)
                message_body = '%s tried to send %s but reached the daily limit.' % (author_account, TOKEN_NAME)

                # disabled comments for this path to save RCs
                print(message_body)

            elif invoker_level > 0 and daily_limit_unique_reached(author_account, parent_author,invoker_level):
                # Check if daily limit for unique tips has been reached
                message_body = '%s tried to send %s but reached the daily limit.' % (author_account, TOKEN_NAME)
                print(message_body)

            else:
                # Tell the invoker how to gain access to the bot
                comment_body = comment_fail_template.render(token_name=TOKEN_NAME, target_account=author_account, min_balance=min_balance)
                message_body = '%s tried to send %s but didnt meet requirements.' % (author_account, TOKEN_NAME)

                post_comment(post, ACCOUNT_NAME, comment_body)
                print(message_body)

            continue

        # check how much TOKEN the bot has
        TOKEN_GIFT_AMOUNT = float(config['HiveEngine']['TOKEN_GIFT_AMOUNT'])
        
        bot_balance = float(Wallet(ACCOUNT_NAME, api=setApi).get_token(TOKEN_NAME)['balance'])
        if bot_balance < TOKEN_GIFT_AMOUNT:

            message_body = 'Bot wallet has run out of %s' % TOKEN_NAME
            print(message_body)

            comment_body = comment_outofstock_template.render(token_name=TOKEN_NAME)
            post_comment(post, ACCOUNT_NAME, comment_body)

            continue

        # transfer

        if ENABLE_TRANSFERS:
            print('[*] Transfering %f %s from %s to %s' % (TOKEN_GIFT_AMOUNT, TOKEN_NAME, ACCOUNT_NAME, parent_author))

            wallet = Wallet(ACCOUNT_NAME, api=setApi, blockchain_instance=HIVE)
            wallet.transfer(parent_author, TOKEN_GIFT_AMOUNT, TOKEN_NAME, memo=config['HiveEngine']['TRANSFER_MEMO'])

            today = str(date.today())
            db_save_gift(today, author_account, parent_author, op['block_num'])

            message_body = 'I sent %f %s to %s' % (TOKEN_GIFT_AMOUNT, TOKEN_NAME, parent_author)
            print(message_body)
        else:
            print('[*] Skipping transfer of %f %s from %s to %s' % (TOKEN_GIFT_AMOUNT, TOKEN_NAME, ACCOUNT_NAME, parent_author))

        # Leave a comment to nofify about the transfer
        today = str(date.today())
        today_gift_count = db_count_gifts(today, author_account)
        if invoker_level > 0:
            max_daily_gifts = config['AccessLevel%s' % invoker_level]['MAX_DAILY_GIFTS']
        else:
            max_daily_gifts = 0

        comment_body = comment_success_template.render(token_name=TOKEN_NAME, target_account=parent_author, token_amount=TOKEN_GIFT_AMOUNT, author_account=author_account,  today_gift_count=today_gift_count, max_daily_gifts=max_daily_gifts)
        post_comment(post, ACCOUNT_NAME, comment_body)

        #break

if __name__ == '__main__':

    main()
