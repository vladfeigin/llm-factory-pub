import os
import pickle
import base64
import json
from email.mime.text import MIMEText
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
_ = load_dotenv()

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    """Authenticate and get the Gmail API service."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service

def get_current_date(service):
    """Get the current date in the format YYYY/MM/DD."""
    today = datetime.now().strftime("%Y/%m/%d")
    #return f"after:{today}"
    return "the current date (today) is: " + today
    

def list_messages(service, user_id='me', max_results=10, query=None):
    """List all messages in the user's mailbox that match the query and output as JSON.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value 'me' can be used to indicate the authenticated user.
        max_results: Maximum number of messages to return.
        query: String used to filter the messages listed.
        
    Returns:
        None
    """
    try:
        results = service.users().messages().list(userId=user_id, maxResults=max_results, q=query).execute()
        messages = results.get('messages', [])
        
        message_list = []
        for message in messages:
            msg = service.users().messages().get(userId=user_id, id=message['id']).execute()
            headers = msg['payload']['headers']
            subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), None)
            sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), None)
            body = get_message_body(msg)
            
            message_list.append({
                "sender": sender,
                "subject": subject,
                "body": body
            })
        #print(json.dumps(message_list, indent=2))
        json_str = [json.dumps(item) for item in message_list]
        emails_text = '|'.join(json_str)
        return emails_text
            
    except Exception as error:
        print(f"An error occurred: {error}")

def get_message_body(message):
    """Get the body of the email message."""
    if 'parts' in message['payload']:
        parts = message['payload']['parts']
        for part in parts:
            if part['mimeType'] == 'text/plain':
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                return clean_body(body)
            elif part['mimeType'] == 'text/html':
                html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                text_content = BeautifulSoup(html_content, 'html.parser').get_text()
                return clean_body(text_content)
    else:
        body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        if message['payload']['mimeType'] == 'text/html':
            text_content = BeautifulSoup(body, 'html.parser').get_text()
            return clean_body(text_content)
        else:
            return clean_body(body)
    return None

def clean_body(body):
    """Clean the email body by removing unwanted characters."""
    # Replace unwanted characters with a space
    unwanted_chars = ['\u200c', '\u00a0', '\n', '\r', '\t']
    for char in unwanted_chars:
        body = body.replace(char, ' ')
    return body.strip()


def delete_message(service, user_id, msg_id):
    """Delete an email message."""
    try:
        service.users().messages().delete(userId=user_id, id=msg_id).execute()
        print(f'Message with ID: {msg_id} deleted successfully.')
    except Exception as error:
        print(f'An error occurred: {error}')


def classify_and_summarize_email(service, category, summary, sender_email):
    """Classifies the email to one of the following categories: CONCERN, QUESTION, RESPONSE IS AWAITED, NEGATIVE SENTIMENT. 
    Summarizes the email and returns:  category, summary and the sender email."""
    print (f"Email from: {sender_email}")
    print (f"Category: {category}")
    print (f"Summary: {summary}")
    return f'{{"email_category":"{category}" , "email_summary":"{summary}", "sender_email": "{sender_email}"}}' 

def sentiment_analysis_email(service, sentiment):
    """ Classifies the email to one of the following categories: POSITIVE, NEGATIVE, NEUTRAL. """
    print (f"Sentiment: {sentiment}")
    return sentiment

def create_message(sender, to, subject, message_text):
    """Create a message for an email."""
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

def send_email(service, user_id, message):
    """Send an email message."""
    subject = "Important. Attention is required!"
    formatted_message = create_message(os.getenv("SENDER"),os.getenv("RECIPIENT"), subject, message)
    
    try:
        sent_message = (service.users().messages().send(userId=user_id, body=formatted_message).execute())
        print(f'Message Id: {sent_message["id"]}')
        return "The notification email has been sent successfully."
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


if __name__ == '__main__':
    # Initialize the Gmail service once
    service = get_gmail_service()
    
    # Get today's date in the format YYYY/MM/DD
    today = datetime.now().strftime("%Y/%m/%d")
    query = f"after:{today}"

    # List messages from the latest day and output as JSON
    list_messages(service, max_results=10, query=query)
    
    # Send an email
    sender = 'your-email@gmail.com'
    to = 'recipient-email@gmail.com'
    subject = 'Test Email'
    message_text = 'This is a test email from Gmail API.'
    message = create_message(sender, to, subject, message_text)
    #send_message(service, 'me', message)
    
    # Delete an email (replace 'your-message-id' with an actual message ID)
    #delete_message(service, 'me', 'your-message-id')