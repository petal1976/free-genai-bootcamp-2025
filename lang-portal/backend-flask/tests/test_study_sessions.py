import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import json
from datetime import datetime
from flask import Flask
import sqlite3

# Import the main application factory
from app import create_app

@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()

def test_create_study_session(client, app):
    """Test creating a new study session"""
    # First verify the test data exists
    cursor = app.db.cursor()
    
    # Check groups
    cursor.execute("SELECT * FROM groups")
    groups = cursor.fetchall()
    print("\nAvailable groups:", [dict(g) for g in groups])
    
    # Check study activities
    cursor.execute("SELECT * FROM study_activities")
    activities = cursor.fetchall()
    print("Available activities:", [dict(a) for a in activities])
    
    response = client.post('/api/study-sessions', 
        json={
            'group_id': 1,
            'study_activity_id': 1
        })
    
    # Print error response if status code is not 200
    if response.status_code != 200:
        print("\nError response:", response.get_json())
        print("Response status:", response.status_code)
        print("Response data:", response.data.decode())
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'session_id' in data
    assert data['message'] == 'Study session recorded successfully'

def test_create_study_session_missing_fields(client):
    """Test creating a study session with missing fields"""
    response = client.post('/api/study-sessions', 
        json={
            'group_id': 1
            # missing study_activity_id
        })
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Missing required fields'

def test_get_study_sessions(client):
    """Test getting list of study sessions"""
    # First create a session
    client.post('/api/study-sessions', 
        json={
            'group_id': 1,
            'study_activity_id': 1
        })
    
    response = client.get('/api/study-sessions')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'items' in data
    assert 'total' in data
    assert 'page' in data
    assert 'per_page' in data
    assert 'total_pages' in data
    
    assert len(data['items']) > 0
    session = data['items'][0]
    assert 'id' in session
    assert 'group_name' in session
    assert 'activity_name' in session
    assert 'start_time' in session
    assert 'review_items_count' in session

def test_get_study_session_by_id(client):
    """Test getting a specific study session"""
    # First create a session
    create_response = client.post('/api/study-sessions', 
        json={
            'group_id': 1,
            'study_activity_id': 1
        })
    session_id = json.loads(create_response.data)['session_id']
    
    response = client.get(f'/api/study-sessions/{session_id}')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'session' in data
    assert 'words' in data
    
    session = data['session']
    assert session['id'] == session_id
    assert session['group_name'] == 'Test Group'
    assert session['activity_name'] == 'Test Activity'

def test_get_nonexistent_study_session(client):
    """Test getting a study session that doesn't exist"""
    response = client.get('/api/study-sessions/999')
    assert response.status_code == 404

def test_post_session_review(client, app):
    """Test posting review results for a study session"""
    # First create a session
    create_response = client.post('/api/study-sessions', 
        json={
            'group_id': 1,
            'study_activity_id': 1
        })
    
    assert create_response.status_code == 200, f"Failed to create session: {create_response.get_json()}"
    session_id = json.loads(create_response.data)['session_id']
    
    # Verify the session was created
    cursor = app.db.cursor()
    cursor.execute('SELECT * FROM study_sessions WHERE id = ?', (session_id,))
    session = cursor.fetchone()
    assert session is not None, "Session was not created in database"
    
    # Post review results
    response = client.post(f'/api/study_sessions/{session_id}/review',
        json=[{
            'word_id': 1,
            'is_correct': True
        }])
    
    # Print error response if status code is not 200
    if response.status_code != 200:
        print("\nError response:", response.get_json())
        print("Response status:", response.status_code)
        print("Response data:", response.data.decode())
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'Reviews recorded successfully'
    assert data['session_id'] == session_id
    
    # Verify the review was recorded
    cursor.execute('''
        SELECT * FROM word_review_items 
        WHERE study_session_id = ? AND word_id = ?
    ''', (session_id, 1))
    review = cursor.fetchone()
    assert review is not None, "Review was not recorded in database"
    assert review['correct'] == 1, "Review correctness was not properly recorded"

def test_post_invalid_review_data(client):
    """Test posting invalid review data"""
    response = client.post('/api/study_sessions/1/review',
        json={'not_an_array': True})
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Request body must be an array of review results'

def test_reset_study_sessions(client):
    """Test resetting all study sessions"""
    # First create a session
    client.post('/api/study-sessions', 
        json={
            'group_id': 1,
            'study_activity_id': 1
        })
    
    # Then reset
    response = client.post('/api/study-sessions/reset')
    assert response.status_code == 200
    
    # Verify sessions are gone
    get_response = client.get('/api/study-sessions')
    data = json.loads(get_response.data)
    assert data['total'] == 0
    assert len(data['items']) == 0 