import json
import boto3
from botocore.exceptions import ClientError
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SES client
ses_client = boto3.client('ses', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

def lambda_handler(event, context):
    """
    Lambda function to send cold emails via Amazon SES
    """
    try:
        # Parse input
        body = json.loads(event.get('body', '{}'))
        
        recipient_email = body.get('recipient_email')
        subject = body.get('subject')
        email_body = body.get('email_body')
        sender_email = body.get('sender_email', os.environ.get('SES_FROM_EMAIL'))
        
        # Validate required fields
        if not all([recipient_email, subject, email_body, sender_email]):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required fields: recipient_email, subject, email_body'
                })
            }
        
        # Send email
        response = send_email(sender_email, recipient_email, subject, email_body)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Email sent successfully',
                'message_id': response.get('MessageId'),
                'recipient': recipient_email
            })
        }
        
    except ClientError as e:
        logger.error(f"SES error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Email service error: {str(e)}'})
        }
    except Exception as e:
        logger.error(f"Error in send_cold_email: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }

def send_email(sender, recipient, subject, body_text):
    """
    Send email using Amazon SES
    """
    try:
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [recipient],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': 'UTF-8',
                        'Data': body_text,
                    },
                },
                'Subject': {
                    'Charset': 'UTF-8',
                    'Data': subject,
                },
            },
            Source=sender,
            ReplyToAddresses=[
                os.environ.get('SES_REPLY_TO_EMAIL', sender)
            ]
        )
        return response
    except ClientError as e:
        logger.error(f"Failed to send email: {e.response['Error']['Message']}")
        raise