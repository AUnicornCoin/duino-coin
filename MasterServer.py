#!/usr/bin/env python3
#############################################
# Duino-Coin Master Server Remastered (v1.8)
# https://github.com/revoxhere/duino-coin
# Distributed under MIT license
# © Duino-Coin Community 2019-2020
#############################################
import requests, smtplib, ssl, socket, re, math, random, hashlib, datetime, threading, requests, smtplib, ssl, sqlite3, bcrypt, time, os.path, json
from _thread import *
from shutil import copyfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

host = "" # Server will use this as hostname to bind to (localhost on Windows, 0.0.0.0 on Linux in most cases)
port = 2811 # Server will listen on this port - 2811 for official Duino-Coin server (14808 for old one)
serverVersion = 1.8 # Server version which will be sent to the clients
diff_incrase_per = 2000 # Difficulty will increase every x blocks (official server uses 5k)
duco_email = "mail" # E-mail and password to send registration mail from
duco_password = "pass"
# Registration email - text version
text = """\
Hi there!
Your e-mail address has been successfully verified and you are now registered on the Duino-Coin network!
We hope you'll have a great time using Duino-Coin.
If you have any difficulties there are a lot of guides on our website: https://duinocoin.com/getting-started
You can also join our Discord server: https://discord.gg/kvBkccy to chat, take part in giveaways, trade and get help from other Duino-Coin users.
Happy mining!
Duino-Coin Team"""
# Registration email - HTML version
html = """\
<html>
  <body>
    <img src="https://github.com/revoxhere/duino-coin/raw/master/Resources/ducobanner.png?raw=true" width="360px" height="auto"><br>
    <h3>Hi there!</h3>
    <h4>Your e-mail address has been successfully verified and you are now registered on the Duino-Coin network!</h4>
    <p>We hope you'll have a great time using Duino-Coin.<br>If you have any difficulties there are a lot of <a href="https://duinocoin.com/getting-started">guides on our website</a>.<br>
       You can also join our <a href="https://discord.gg/kvBkccy">Discord server</a> to chat, take part in giveaways, trade and get help from other Duino-Coin users.<br><br>
       Happy mining!<br>
       <italic>Duino-Coin Team</italic>
    </p>
  </body>
</html>
"""
connectedUsers = 0
minerapi = {}
database = 'crypto_database.db' # User data database location
if not os.path.isfile(database): # Create it if it doesn't exist
    with sqlite3.connect(database) as conn:
        datab = conn.cursor()
        datab.execute('''CREATE TABLE IF NOT EXISTS Users(username TEXT, password TEXT, email TEXT, balance REAL)''')
blockchain = 'duino_blockchain.db' # Blockchain database location
if not os.path.isfile(blockchain): # Create it if it doesn't exist
    with sqlite3.connect(blockchain) as blockconn:
        try:
            with open("config/lastblock", "r+") as lastblockfile:
                lastBlockHash = lastblockfile.readline() # If old database is found, read lastBlockHash from it
        except:
            lastBlockHash = "ba29a15896fd2d792d5c4b60668bf2b9feebc51d" # First block - SHA1 of "duino-coin"
        try:
            with open("config/blocks", "r+") as blockfile:
                blocks = blockfile.readline() # If old database is found, read mined blocks amount from it
        except:
            blocks = 1 # Start from 1
        blockdatab = blockconn.cursor()
        blockdatab.execute('''CREATE TABLE IF NOT EXISTS Server(blocks REAL, lastBlockHash TEXT)''')
        blockdatab.execute("INSERT INTO Server(blocks, lastBlockHash) VALUES(?, ?)", (blocks, lastBlockHash))
        blockconn.commit()
def createBackup():
    if not os.path.isdir('backups/'):
        os.mkdir('backups/')
    while True:
        today = datetime.date.today()
        if not os.path.isdir('backups/'+str(today)+'/'):
            os.mkdir('backups/'+str(today))
            copyfile(blockchain, "backups/"+str(today)+"/"+blockchain)
            copyfile(database, "backups/"+str(today)+"/"+database)
            with open("prices.txt", "a") as pricesfile:
                pricesfile.write("," + str(round(getDucoPrice(), 4)).rstrip("\n"))
        time.sleep(3600*6) # Run every 6h
def getDucoPrice():
    coingecko = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=magi&vs_currencies=usd", data=None)
    if coingecko.status_code == 200:
        geckocontent = coingecko.content.decode()
        geckocontentjson = json.loads(geckocontent)
        xmgusd = float(geckocontentjson["magi"]["usd"])
    else:
        xmgusd = .015
    ducousdLong = float(xmgusd) * 3.5 * random.randint(97,103) / 100
    ducoPrice = round(float(ducousdLong) / 10, 8) * 0.8
    return ducoPrice
def getRegisteredUsers():
    with sqlite3.connect(database) as conn:
        datab = conn.cursor()
        datab.execute("SELECT COUNT(username) FROM Users")
        registeredUsers = datab.fetchone()[0]
    return registeredUsers
def getMinedDuco():
    with sqlite3.connect(database) as conn:
        datab = conn.cursor()
        datab.execute("SELECT SUM(balance) FROM Users")
        allMinedDuco = datab.fetchone()[0]
    return allMinedDuco
def getLeaders():
    leadersdata = []
    with sqlite3.connect(database) as conn:
        datab = conn.cursor()
        datab.execute("SELECT * FROM Users ORDER BY balance DESC")
        for row in datab.fetchall():
            leadersdata.append(f"{round((row[3]), 4)} DUCO - {row[0]}")
    return(leadersdata[:10])
def API():
    while True:
        with sqlite3.connect(blockchain) as blockconn:
            blockdatab = blockconn.cursor()
            blockdatab.execute("SELECT blocks FROM Server") # Read amount of mined blocks
            blocks = int(blockdatab.fetchone()[0])
            blockdatab.execute("SELECT lastBlockHash FROM Server") # Read lastblock's hash
            lastBlockHash = str(blockdatab.fetchone()[0])
            diff = math.ceil(blocks / diff_incrase_per) # Calculate difficulty
        now = datetime.datetime.now()
        minerList = []
        usernameMinerCounter = {}
        serverHashrate = 0
        hashrate = 0
        for x in minerapi: 
            lista = list(minerapi[x]) # Convert list to strings
            hashrate = lista[1]
            serverHashrate += float(hashrate) # Add user hashrate to the server hashrate
        formattedMinerApi = { # Prepare server API data
                "Server version":        float(serverVersion),
                "Active connections":    int(connectedUsers),
                "Last update":           str(now.strftime("%d/%m/%Y %H:%M (UTC)")),
                "Pool hashrate": str(round(serverHashrate/1000, 2))+" kH/s",
                "Duco price":            float(getDucoPrice()), # Call getDucoPrice function
                "Registered users":      int(getRegisteredUsers()), # Call getRegisteredUsers function
                "All-time mined DUCO":   float(getMinedDuco()), # Call getMinedDuco function
                "Current difficulty":    int(diff),
                "Mined blocks":          int(blocks),
                "Full last block hash":  str(lastBlockHash),
                "Last block hash":       str(lastBlockHash)[:10]+"...",
                "Top 10 richest miners": getLeaders(), # Call getLeaders function
                "Active workers":        usernameMinerCounter,
                "Miners": {}}
        for x in minerapi: # Get data from every miner  
            lista = list(minerapi[x]) # Convert list to strings
            user = lista[0]
            hashrate = lista[1]
            sharetime = lista[2]
            diff = lista[3]
            isEstimated = lista[4]
            minerUsed = lista[5]
            formattedMinerApi["Miners"][x] = { # Format data
                "User":          str(user),
                "Hashrate":      float(hashrate),
                "Is estimated":  str(isEstimated),
                "Sharetime":     float(sharetime),
                "Diff":          int(diff),
                "Software":      str(minerUsed)}
            serverHashrate += float(hashrate) # Add user hashrate to the server hashrate
        for thread in formattedMinerApi["Miners"]:
            minerList.append(formattedMinerApi["Miners"][thread]["User"]) # Append miners to formattedMinerApi["Miners"][id of thread]
        for i in minerList:
            usernameMinerCounter[i]=minerList.count(i) # Count miners for every username
        with open('api.json', 'w') as outfile: # Write JSON to file
            json.dump(formattedMinerApi, outfile, indent=4,ensure_ascii=False)
        time.sleep(5)

def threaded(c): # Main thread for every connected user
    global connectedUsers, minerapi # These globals are used in the statistics API
    c.send(bytes(str(serverVersion), encoding="utf8")) # Send server version

    connectedUsers += 1 # Count new opened connection
    username = "" # Variables for every thread
    lastBlockHash = ""
    blocks = 0
    blockFound = False
    while True:
        try:
            data = c.recv(1024).decode() # Receive data from client
            if not data: 
                break
            else:
                data = data.split(",") # Split incoming data

            ######################################################################
            if data[0] == "REGI":
                try:
                    username = str(data[1])
                    unhashed_pass = str(data[2]).encode('utf-8')
                    email = str(data[3])
                except IndexError:
                    c.send(bytes("NO,Not enough data", encoding='utf8'))
                    break
                if re.match("^[A-Za-z0-9_-]*$", username) and len(username) < 64 and len(unhashed_pass) < 64 and len(email) < 128:
                    password = bcrypt.hashpw(unhashed_pass, bcrypt.gensalt()) # Encrypt password
                    with sqlite3.connect(database) as conn:
                        datab = conn.cursor()
                        datab.execute("SELECT COUNT(username) FROM Users WHERE username = ?",(username,))
                        if int(datab.fetchone()[0]) == 0:
                            if(re.search("^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$",email)):
                                message = MIMEMultipart("alternative")
                                message["Subject"] = "Welcome on Duino-Coin network, "+str(username)+"! " + u"\U0001F44B"
                                message["From"] = duco_email
                                message["To"] = email
                                try:
                                    with sqlite3.connect(database) as conn:
                                        datab = conn.cursor()
                                        datab.execute('''INSERT INTO Users(username, password, email, balance) VALUES(?, ?, ?, ?)''',(username, password, email, 0.0))
                                        conn.commit()
                                    c.send(bytes("OK", encoding='utf8'))
                                    try:
                                        part1 = MIMEText(text, "plain") # Turn email data into plain/html MIMEText objects
                                        part2 = MIMEText(html, "html")
                                        message.attach(part1)
                                        message.attach(part2)
                                        context = ssl.create_default_context() # Create secure connection with server and send an email
                                        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context = context) as smtpserver:
                                            smtpserver.login(duco_email, duco_password)
                                            smtpserver.sendmail(duco_email, email, message.as_string())
                                    except:
                                        print("Error sending registration email")
                                except:
                                    c.send(bytes("NO,Error registering user", encoding='utf8'))
                                    break
                            else:
                                c.send(bytes("NO,E-mail is invalid", encoding='utf8'))
                                break
                        else:
                            c.send(bytes("NO,This account already exists", encoding='utf8'))
                            break
                else:
                    c.send(bytes("NO,You have used unallowed characters or data is too long", encoding='utf8'))
                    break

            ######################################################################
            if str(data[0]) == "LOGI":
                try:
                    username = str(data[1])
                    password = str(data[2]).encode('utf-8')
                except IndexError:
                    c.send(bytes("NO,Not enough data", encoding='utf8'))
                    break
                if re.match(r'^[\w\d_()]*$', username): # Check username for unallowed characters
                    try:
                        with sqlite3.connect(database) as conn: # User exists, read his password
                            datab = conn.cursor()
                            datab.execute("SELECT * FROM Users WHERE username = ?",(username,))
                            stored_password = datab.fetchone()[1]
                        if bcrypt.checkpw(password, stored_password):
                            c.send(bytes("OK", encoding='utf8')) # Send feedback about sucessfull login
                        else: # Disconnect user which password isn't valid, close the connection
                            c.send(bytes("NO,Password is invalid", encoding='utf8'))
                            break
                    except: # Disconnect user which username doesn't exist, close the connection
                        c.send(bytes("NO,This user doesn't exist", encoding='utf8'))
                        break
                else: # User used unallowed characters, close the connection
                    c.send(bytes("NO,You have used unallowed characters", encoding='utf8'))
                    break

            ######################################################################
            if str(data[0]) == "JOB":
                if username == "":
                    try:
                        username = str(data[1])
                    except IndexError:
                        c.send(bytes("NO,Not enough data", encoding='utf8'))
                        break
                with sqlite3.connect(blockchain) as blockconn:
                    blockdatab = blockconn.cursor()
                    blockdatab.execute("SELECT blocks FROM Server") # Read amount of mined blocks
                    blocks = int(blockdatab.fetchone()[0])
                    blockdatab.execute("SELECT lastBlockHash FROM Server") # Read lastblock's hash
                    lastBlockHash = str(blockdatab.fetchone()[0])
                # Calculate difficulty and create new block hash
                try:
                    customDiff = str(data[2])
                    if str(customDiff) == "AVR":
                        diff = 300 # Use 300 - optimal diff for very low power devices like arduino
                        shareTimeRequired = 155
                    elif str(customDiff) == "ESP":
                        diff = 1500 # Use 1500 - optimal diff for low power devices like ESP
                        shareTimeRequired = 220
                    elif str(customDiff) == "MEDIUM":
                        diff = 5000 # Use 5000 - optimal diff for low power computers
                        shareTimeRequired = 170
                except IndexError:
                    diff = math.ceil(blocks / diff_incrase_per) # Use "standard" difficulty
                    shareTimeRequired = 85
                rand = random.randint(1, 100 * diff)
                newBlockHash = hashlib.sha1(str(lastBlockHash + str(rand)).encode("utf-8")).hexdigest()
                try: 
                    c.send(bytes(str(lastBlockHash) + "," + str(newBlockHash) + "," + str(diff), encoding='utf8')) # Send hashes and diff hash to the miner
                    jobsent = datetime.datetime.now()
                    response = c.recv(128).decode().split(",") # Wait until client solves hash
                    result = response[0]
                    # Kolka system - reward dependent on share submission time and rejection of very fast shares
                    resultreceived = datetime.datetime.now()
                    sharetime = resultreceived - jobsent # Time from start of hash computing to finding the result
                    sharetime = int(sharetime.microseconds / 1000) # Convert to ms
                    reward = int(int(sharetime) **2) / 750000000 # Calculate reward dependent on share submission time
                    try: # If client submitted hashrate, use it
                        hashrate = response[1]
                        hashrateEstimated = False
                    except IndexError: # If not, estimate it ourselves
                        hashrate = int(rand) / int(sharetime) * 2000000 / int(diff) # This formula gives a rough estimation of the hashrate
                        hashrateEstimated = True
                    try:
                        minerUsed = str(response[2])
                    except IndexError:
                        minerUsed = "Unknown"
                    minerapi.update({str(threading.get_ident()): [str(username), str(hashrate), str(sharetime), str(diff), str(hashrateEstimated), str(minerUsed)]})
                    if result == str(rand) and int(sharetime) > int(shareTimeRequired):
                        with sqlite3.connect(blockchain) as blockconn: # Update blocks counter and lastblock's hash
                            blocks += 1
                            blockdatab = blockconn.cursor()
                            blockdatab.execute("UPDATE Server set blocks = ? ", (blocks,))
                            blockdatab.execute("UPDATE Server set lastBlockHash = ?", (newBlockHash,))
                            blockconn.commit()
                        try:
                            with sqlite3.connect(database) as conn: # Get users balance and check if it exists
                                datab = conn.cursor()
                                datab.execute("SELECT * FROM Users WHERE username = ?", (username,))
                                balance = float(datab.fetchone()[3])
                                balance += float(reward) # Reward user
                                datab = conn.cursor()
                                datab.execute("UPDATE Users set balance = ? where username = ?", (f'{balance:.20f}', username))
                                conn.commit()
                                c.send(bytes("GOOD", encoding="utf8")) # Send feedback that result was correct
                        except:
                            c.send(bytes("INVU", encoding="utf8")) # Send feedback that this user doesn't exist
                            break

                    else: # Incorrect result received
                        with sqlite3.connect(database) as conn:
                            datab = conn.cursor()
                            datab.execute("SELECT * FROM Users WHERE username = ?", (username,))
                            balance = str(datab.fetchone()[3]) # Get miner balance
                            if float(balance) > .000005:
                                balance = float(balance) - .000005 # Subtract a small amount as penalty
                                with sqlite3.connect(database) as conn:
                                    datab = conn.cursor() # Update his the balance
                                    datab.execute("UPDATE Users set balance = ? where username = ?", (f'{balance:.20f}', username))
                                    conn.commit()
                        c.send(bytes("BAD", encoding="utf8")) # Send feedback that incorrect result was received
                except:
                    break

            ######################################################################
            if str(data[0]) == "CHGP" and str(username) != "":
                try:
                    oldPassword = data[1]
                    newPassword = data[2]
                except IndexError:
                    c.send(bytes("NO,Not enough data", encoding='utf8'))
                    break
                try:
                    oldPassword = oldPassword.encode('utf-8')
                    newPassword = newPassword.encode("utf-8")
                    newPassword_encrypted = bcrypt.hashpw(newPassword, bcrypt.gensalt())
                except:
                    c.send(bytes("NO,Bcrypt error", encoding="utf8"))
                    break
                try:
                    with sqlite3.connect(database) as conn:
                        datab = conn.cursor()
                        datab.execute("SELECT * FROM Users WHERE username = ?",(username,))
                        old_password_database = datab.fetchone()[1]
                except:
                    c.send(bytes("NO,Incorrect username", encoding="utf8"))
                    break

                if bcrypt.checkpw(oldPassword, old_password_database):
                    with sqlite3.connect(database) as conn:
                        datab = conn.cursor()
                        datab.execute("UPDATE Users set password = ? where username = ?", (newPassword_encrypted, username))
                        conn.commit()
                        try:
                            c.send(bytes("OK,Your password has been changed", encoding='utf8'))
                        except:
                            break
                else:
                    try:
                        server.send(bytes("NO,Your old password doesn't match!", encoding='utf8'))
                    except:
                        break

            ######################################################################
            if str(data[0]) == "SEND" and str(username) != "":
                try:
                    recipient = str(data[2])
                    amount = float(data[3])
                except IndexError:
                    c.send(bytes("NO,Not enough data", encoding='utf8'))
                    break
                try:
                    with sqlite3.connect(database) as conn:
                        datab = conn.cursor()
                        datab.execute("SELECT * FROM Users WHERE username = ?",(username,))
                        balance = float(datab.fetchone()[3]) # Get current balance of sender
                except:
                    c.send(bytes("NO,Can't check sender balance", encoding='utf8'))
                    break
                if str(recipient) == str(username): # Verify that the balance is higher or equal to transfered amount
                    try:
                        c.send(bytes("NO,You're sending funds to yourself", encoding='utf8'))
                    except:
                        break
                if float(balance) <= float(amount) or float(amount) <= 0:
                    try:
                        c.send(bytes("NO,Incorrect amount", encoding='utf8'))
                    except:
                        break
                elif float(balance) >= float(amount) and str(recipient) != str(username) and float(amount) >= 0:
                    try:
                        balance -= float(amount) # Remove amount from senders' balance
                        with sqlite3.connect(database) as conn:
                            datab = conn.cursor()
                            datab.execute("UPDATE Users set balance = ? where username = ?", (balance, username))
                            conn.commit()
                        with sqlite3.connect(database) as conn:
                            datab = conn.cursor()
                            datab.execute("SELECT * FROM Users WHERE username = ?",(recipient,))
                            recipientbal = float(datab.fetchone()[3]) # Get receipents' balance
                        recipientbal += float(amount)
                        with sqlite3.connect(database) as conn:
                            datab = conn.cursor() # Update receipents' balance
                            datab.execute("UPDATE Users set balance = ? where username = ?", (f'{float(recipientbal):.20f}', recipient))
                            conn.commit()
                        c.send(bytes("OK,Successfully transferred funds!", encoding='utf8'))
                    except:
                        c.send(bytes("NO,Error occured while sending funds", encoding='utf8'))
                        break

            ######################################################################
            elif str(data[0]) == "BALA" and str(username) != "":
                with sqlite3.connect(database) as conn:
                    datab = conn.cursor()
                    datab.execute("SELECT * FROM Users WHERE username = ?",(username,))
                    balance = str(datab.fetchone()[3]) # Fetch balance of user
                c.send(bytes(str(f'{float(balance):.20f}'), encoding="utf8")) # Send it as 20 digit float

        except ConnectionResetError:
            break
    #User disconnected, exiting loop
    connectedUsers -= 1 # Subtract connected miners amount
    try: # Delete miner from minerapi if it was used
        del minerapi[str(threading.get_ident())]
    except KeyError:
        pass
    c.close() # Close the connection

def Main():
    print("Duino-Coin Master Server", serverVersion, "is starting...")
    threading.Thread(target=API).start() # Create JSON API thread
    threading.Thread(target=createBackup).start() # Create Backup generator thread
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    s.bind((host, port))
    s.listen(1024)
    print("Socket binded to port", port) 
    while True:  # Loop that works until client wants to exit
        c, addr = s.accept() # establish connection with client
        print('Connection :', addr[0], ':', addr[1]) 
        start_new_thread(threaded, (c,)) # Start a new thread and return its identifier 
    s.close()
if __name__ == '__main__': 
    Main()
