from threading import Thread
from flask import current_app
from flask_mail import Message
from app import mail
import smtplib


def send_async_email(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
            current_app.logger.debug("Email sent successfully")
        except smtplib.SMTPException as e:
            current_app.logger.error(f"Failed to send email:{e}")


def send_email(subject, recipients, text_body, html_body, async_send=True):
    sender = current_app.config["MAIL_DEFAULT_SENDER"]
    if not sender:
        current_app.logger.warning("MAIL_DEFAULT_SENDER not set - using MAIL_USERNAME")
        sender = current_app.config["MAIL_USERNAME"]

    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body

    try:
        if async_send:
            Thread(
                target=send_async_email, args=(current_app._get_current_object(), msg)
            ).start()
        else:
            mail.send(msg)
            current_app.logger.debug("Email sent successfully (sync)")
            return True
    except smtplib.SMTPException as e:
        current_app.logger.error(f"Failed to send email (sync): {e}")
        return False
