from datetime import datetime
from lms.utils.db import db
from flask import current_app
import logging

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, server_default=db.func.current_timestamp())
    
    # Define relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    
    def __repr__(self):
        return f'<Message {self.id} from {self.sender_id} to {self.recipient_id}>'
    
    @staticmethod
    def get_conversation(user1_id, user2_id, limit=50):
        """Get the conversation between two users"""
        try:
            return Message.query.filter(
                ((Message.sender_id == user1_id) & (Message.recipient_id == user2_id)) | 
                ((Message.sender_id == user2_id) & (Message.recipient_id == user1_id))
            ).order_by(Message.created_at.desc()).limit(limit).all()
        except Exception as e:
            logging.error(f"Error getting conversation: {str(e)}")
            return []
    
    @staticmethod
    def get_conversations_for_user(user_id):
        """Get all conversations for a user with the most recent message for each conversation"""
        try:
            # First, find all users this user has either sent messages to or received messages from
            sent_to = db.session.query(Message.recipient_id).filter(Message.sender_id == user_id).distinct().all()
            received_from = db.session.query(Message.sender_id).filter(Message.recipient_id == user_id).distinct().all()
            
            # Combine and deduplicate user IDs
            sent_to_ids = [user[0] for user in sent_to]
            received_from_ids = [user[0] for user in received_from]
            contact_ids = list(set(sent_to_ids + received_from_ids))
            
            conversations = []
            for contact_id in contact_ids:
                # Get the most recent message between the two users
                latest_message = Message.query.filter(
                    ((Message.sender_id == user_id) & (Message.recipient_id == contact_id)) | 
                    ((Message.sender_id == contact_id) & (Message.recipient_id == user_id))
                ).order_by(Message.created_at.desc()).first()
                
                if latest_message:
                    conversations.append({
                        'contact_id': contact_id,
                        'latest_message': latest_message
                    })
            
            # Sort conversations by latest message timestamp
            conversations.sort(key=lambda x: x['latest_message'].created_at, reverse=True)
            return conversations
        except Exception as e:
            logging.error(f"Error getting conversations: {str(e)}")
            return []
        
    @staticmethod
    def mark_conversation_as_read(user_id, other_user_id):
        """Mark all messages from other_user to user as read"""
        try:
            unread_messages = Message.query.filter_by(sender_id=other_user_id, recipient_id=user_id, read=False).all()
            for message in unread_messages:
                message.read = True
            db.session.commit()
        except Exception as e:
            logging.error(f"Error marking messages as read: {str(e)}")
            db.session.rollback()
    
    @staticmethod
    def count_unread_messages(user_id):
        """Count the total number of unread messages for a user"""
        try:
            return Message.query.filter_by(recipient_id=user_id, read=False).count()
        except Exception as e:
            logging.error(f"Error counting unread messages: {str(e)}")
            return 0