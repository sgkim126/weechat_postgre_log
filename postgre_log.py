import psycopg2
import weechat


SCRIPT_NAME = "postgre_log"
SCRIPT_AUTHOR = "Seulgi Kim <dev@seulgik.im>"
SCRIPT_VERSION = "1.0"
SCRIPT_LICENCE = "GPL3"
SCRIPT_DESC = "Save messages in PostgreSQL"


connect = None
msg_hook = None
part_hook = None
join_hook = None


def check_table_exists():
    cursor = connect.cursor()
    try:
        query = ("SELECT *"
                 "  FROM information_schema.tables"
                 "  WHERE table_name='weechat_message'")
        cursor.execute(query)
        return cursor.rowcount == 1
    except Exception as ex:
        weechat.prnt('', "Exception in check_tabke_exists: %s" % ex.message)
        raise ex
    finally:
        cursor.close()


def create_table():
    cursor = connect.cursor()
    try:
        query = ("CREATE TABLE weechat_message ("
                 "  id SERIAL PRIMARY KEY,"
                 "  username CHAR(16) NOT NULL,"
                 "  servername VARCHAR(64) NOT NULL,"
                 "  channelname VARCHAR(50) NOT NULL,"
                 "  message VARCHAR(512) NOT NULL,"
                 "  hilight CHAR(1) NOT NULL,"
                 "  command VARCHAR(16) NOT NULL,"
                 "  time TIMESTAMP WITH TIME ZONE NOT NULL)")
        cursor.execute(query)
        connect.commit()
    except Exception as ex:
        weechat.prnt('', "Exception in create_table: %s" % ex.message)
        raise ex
    finally:
        cursor.close()


def msg_cb(command, buf, date, tags, displayed, hilight, username, msg):
    servername = weechat.buffer_get_string(buf, 'localvar_server')
    channelname = weechat.buffer_get_string(buf, 'short_name')
    insert_log(servername, channelname, username, msg, hilight, command, date)
    return weechat.WEECHAT_RC_OK


def log_cb(command, buf, date, tags, displayed, hilight, prefix, msg):
    servername = weechat.buffer_get_string(buf, 'localvar_server')
    channelname = weechat.buffer_get_string(buf, 'short_name')
    username = msg.split()[0]
    insert_log(servername, channelname, username, msg, hilight, command, date)
    return weechat.WEECHAT_RC_OK


def insert_log(servername, channelname, username, message, hilight,
               command, time):
    cursor = connect.cursor()
    try:
        query = ("INSERT INTO"
                 "  weechat_message (username, servername, channelname,"
                 "    message, hilight, command, time)"
                 "  VALUES ('%s', '%s', '%s', '%s', %s, '%s',"
                 "    to_timestamp(%s))")
        cursor.execute(query %
                       (username, servername, channelname,
                        message, hilight, command, time))
        connect.commit()
    except Exception as ex:
        weechat.prnt('', "Exception in insert_message: %s" % ex.message)
        raise ex
    finally:
        cursor.close()


def postgre_log_enable_cb(data, buffer, args):
    global connect
    global msg_hook
    global join_hook
    global part_hook
    connect = psycopg2.connect(dbname='weechat', user='weechat')

    if not check_table_exists():
        create_table()
    msh_hook = weechat.hook_print('', 'irc_privmsg', '', 1, 'msg_cb',
                                  'PRIVMSG')
    join_hook = weechat.hook_print('', 'irc_join', '', 1, 'log_cb', 'JOIN')
    part_hook = weechat.hook_print('', 'irc_part', '', 1, 'log_cb', 'PART')
    return weechat.WEECHAT_RC_OK


def postgre_log_disable_cb(data=None, buffer=None, args=None):
    global connect
    global msg_hook
    global join_hook
    global part_hook
    if connect is None:
        weechat.prnt('', "postgre_log is already disabled.")
        return weechat.WEECHAT_RC_OK
    connect.close()
    connect = None
    if msg_hook:
        weechat.unhook(msg_hook)
        msg_hook = None
    if join_hook:
        weechat.unhook(join_hook)
        join_hook = None
    if part_hook:
        weechat.unhook(part_hook)
        part_hook = None
    return weechat.WEECHAT_RC_OK


def shutdown_cb():
    return postgre_log_disable_cb()


if __name__ == '__main__':
    if weechat.register(SCRIPT_NAME, SCRIPT_AUTHOR, SCRIPT_VERSION,
                        SCRIPT_LICENCE, SCRIPT_DESC, 'shutdown_cb', ''):
        weechat.hook_command('postgre_log_enable', "Enable the postgre log.",
                             '', '', '', 'postgre_log_enable_cb', '')
        weechat.hook_command('postgre_log_disable', "Disable the postgre log.",
                             '', '', '', 'postgre_log_disable_cb', '')
