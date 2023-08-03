import asyncio
from flask import current_app
from app.utils.singleton import Singleton

from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody

scopes = ['https://graph.microsoft.com/.default']

class SenderMailNotDefined(Exception):
    pass

class GraphClient(Singleton):
    _client = None
    def __init__(self):
        if self._client is None:
            self._client: GraphServiceClient = GraphServiceClient(
                credentials=ClientSecretCredential(
                    tenant_id='50e8e35a-251b-49e7-acf6-c993d8501741',
                    client_id=current_app.config["GRAPH_APP_ID"],
                    client_secret=current_app.config["GRAPH_APP_SECRET"],
                ),
                scopes=scopes
            )

    def _generate_email_message(self, subject, recipients, text_body, html_body) -> Message:
        return Message(
            subject=subject,
            body=ItemBody(
                content_type=BodyType.Html if html_body else BodyType.Text,
                content=html_body if html_body else text_body
            ),
            to_recipients=[Recipient(email_address=EmailAddress(address=email)) for email in recipients]   
        )


    def _send_email_message(self, message: Message) -> None:
        if not (sender := current_app.config.get("MAIL_USERNAME")):
            raise SenderMailNotDefined

        mail_body = SendMailPostRequestBody(message=message)
        asyncio.get_event_loop().run_until_complete(
            self._client.users.by_user_id(sender).send_mail.post(mail_body)
        )
    
    def send_email(self, subject, recipients, text_body, html_body):
        self._send_email_message(
            self._generate_email_message(
                subject, recipients, text_body, html_body 
            )
        )