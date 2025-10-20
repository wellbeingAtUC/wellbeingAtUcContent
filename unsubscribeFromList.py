from config.sheetsConfig import unsub, unsubArchive, contacts
import datetime

##Get all of the entries in the unsubscribe logs
unsubLogs = unsub.get_all_records()
today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") ##Get date time from now
rowNumber = 2
##Go through the requests to remove the emails
for request in unsubLogs:
    email = request["Email Address"].lower().strip()
    emailToRemove = contacts.find(email)
    if emailToRemove is not None:
        contacts.delete_rows(emailToRemove.row)
    unsub.delete_rows(rowNumber)
    unsubArchive.append_row([today, email])
    rowNumber += 1
    
    
    
    