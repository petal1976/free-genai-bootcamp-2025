import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import sqlite3
from app import create_app
from flask import g

@pytest.fixture
def app():
    """Create and configure a test Flask application instance"""
    test_config = {
        'TESTING': True,
        'DATABASE': 'words_test.db',  # Use test database
        'DEBUG': True,
    }
    
    # Delete test database if it exists
    if os.path.exists('words_test.db'):
        os.remove('words_test.db')
    
    app = create_app(test_config)
    
    # Push an application context
    ctx = app.app_context()
    ctx.push()
    
    # Create test database and tables
    app.db = sqlite3.connect('words_test.db', check_same_thread=False)
    app.db.row_factory = sqlite3.Row
    
    # Create required tables
    cursor = app.db.cursor()
    
    # Enable foreign keys
    cursor.execute('PRAGMA foreign_keys = ON;')
    
    # Create tables
    cursor.executescript('''
        DROP TABLE IF EXISTS word_review_items;
        DROP TABLE IF EXISTS word_reviews;
        DROP TABLE IF EXISTS study_sessions;
        DROP TABLE IF EXISTS words;
        DROP TABLE IF EXISTS groups;
        DROP TABLE IF EXISTS study_activities;
        
        CREATE TABLE groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
        
        CREATE TABLE study_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
        
        CREATE TABLE study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            study_activity_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (study_activity_id) REFERENCES study_activities(id)
        );
        
        CREATE TABLE words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kanji TEXT NOT NULL,
            romaji TEXT NOT NULL,
            english TEXT NOT NULL
        );
        
        CREATE TABLE word_review_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            study_session_id INTEGER NOT NULL,
            word_id INTEGER NOT NULL,
            correct BOOLEAN NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (study_session_id) REFERENCES study_sessions(id),
            FOREIGN KEY (word_id) REFERENCES words(id)
        );
        
        CREATE TABLE word_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id INTEGER NOT NULL UNIQUE,
            correct_count INTEGER DEFAULT 0,
            wrong_count INTEGER DEFAULT 0,
            last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (word_id) REFERENCES words(id)
        );
    ''')
    
    # Insert test data
    cursor.executescript('''
        INSERT INTO groups (name) VALUES ('Test Group');
        INSERT INTO study_activities (name) VALUES ('Test Activity');
        INSERT INTO words (kanji, romaji, english) 
        VALUES ('漢字', 'kanji', 'chinese characters');
    ''')
    
    app.db.commit()
    
    yield app
    
    # Cleanup
    app.db.close()
    ctx.pop()
    
    # Delete test database after tests
    if os.path.exists('words_test.db'):
        os.remove('words_test.db')

@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client() 