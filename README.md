# Instructions

Coming soon. You can probably figure it out for now, the sql file is for MySQL so you will need that on your server. You will also need a full node of Garlicoin, and the cli program as that's what we use for deposits and withdrawals. While this is for Garlicoin it could very easily be used for other cryptos.

Note the config is in config.json, you will need this information before you can use the bot.

Also note you will need to run the python programs in some kind of loop, I have cron jobs to run them every 15 seconds like this:  
&ast; &ast; &ast; &ast; &ast; ( python3 /opt/scripts/grlctips/deposit.py ) > /dev/null 2>&1  
&ast; &ast; &ast; &ast; &ast; ( python3 /opt/scripts/grlctips/withdraw.py ) > /dev/null 2>&1  
&ast; &ast; &ast; &ast; &ast; ( python3 /opt/scripts/grlctips/tipbot.py ) > /dev/null 2>&1  
&ast; &ast; &ast; &ast; &ast; ( sleep 15 ; python3 /opt/scripts/grlctips/deposit.py ) > /dev/null 2>&1  
&ast; &ast; &ast; &ast; &ast; ( sleep 15 ; python3 /opt/scripts/grlctips/withdraw.py ) > /dev/null 2>&1  
&ast; &ast; &ast; &ast; &ast; ( sleep 15 ; python3 /opt/scripts/grlctips/tipbot.py ) > /dev/null 2>&1  
&ast; &ast; &ast; &ast; &ast; ( sleep 30 ; python3 /opt/scripts/grlctips/deposit.py ) > /dev/null 2>&1  
&ast; &ast; &ast; &ast; &ast; ( sleep 30 ; python3 /opt/scripts/grlctips/withdraw.py ) > /dev/null 2>&1  
&ast; &ast; &ast; &ast; &ast; ( sleep 30 ; python3 /opt/scripts/grlctips/tipbot.py ) > /dev/null 2>&1  
&ast; &ast; &ast; &ast; &ast; ( sleep 45 ; python3 /opt/scripts/grlctips/deposit.py ) > /dev/null 2>&1  
&ast; &ast; &ast; &ast; &ast; ( sleep 45 ; python3 /opt/scripts/grlctips/withdraw.py ) > /dev/null 2>&1  
&ast; &ast; &ast; &ast; &ast; ( sleep 45 ; python3 /opt/scripts/grlctips/tipbot.py ) > /dev/null 2>&1

# Testing

Happy to accept pull requests, especially people good with automated testing. It took me hours to manually test this, hours!
