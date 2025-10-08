import traceback
import datetime
from config.gmailConfig import GmailClient
import logging
from config.jsonFiles import AdminEmails

adminList = ", ".join(AdminEmails.values())

class ErrorNotify(logging.Handler):
    def __init__(self, adminEmail = adminList, level=logging.ERROR):
        super().__init__(level)
        self._adminEmail = adminEmail
        self._mailer = GmailClient()

    def emit(self, record):
        try:
            ##Format the error message
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logEntry = self.format(record)

            ##Stack trace capture
            if record.exc_info:
                trace = "".join(traceback.format_exception(*record.exc_info))
            else:
                trace = "No traceback available"
            
            subject = f"Error Alert {record.levelname} in {record.name}"
            body = (
                f"An error has occurred at {timestamp}. \n\n"
                f"Logger: {record.name}\n"
                f"Level: {record.levelname} \n\n"
                f"Message: \n{logEntry}\n\n"
                f"Traceback: \n{trace}"
            )

            #Send email
            self._mailer.send_message(self._adminEmail, subject, body)
        except Exception as e:
            ##Avoid recursive logging if email fails
            print(f"Failed to send the email {e}")

