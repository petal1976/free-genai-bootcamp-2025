from flask import request, jsonify, g
from flask_cors import cross_origin
from datetime import datetime
import sqlite3
import os
import math

def load(app):

  @app.route('/api/study-sessions', methods=['POST'])
  @cross_origin()
  def create_study_sessions():
    try:
      # Get JSON data from request
      data = request.get_json()
      print("\nReceived data:", data)  # Debug print
      
      # Validate required fields
      required_fields = ['group_id', 'study_activity_id']
      if not all(field in data for field in required_fields):
          return jsonify({'error': 'Missing required fields'}), 400
      
      # Connect to the database
      cursor = app.db.cursor()
      
      # Verify the group exists
      cursor.execute('SELECT id FROM groups WHERE id = ?', (data['group_id'],))
      if not cursor.fetchone():
          return jsonify({'error': f'Group with id {data["group_id"]} not found'}), 404
          
      # Verify the study activity exists
      cursor.execute('SELECT id FROM study_activities WHERE id = ?', (data['study_activity_id'],))
      if not cursor.fetchone():
          return jsonify({'error': f'Study activity with id {data["study_activity_id"]} not found'}), 404
      
      # Insert the study session
      try:
          cursor.execute('''
              INSERT INTO study_sessions 
              (group_id, study_activity_id, created_at) 
              VALUES (?, ?, datetime('now'))
          ''', (data['group_id'], data['study_activity_id']))
          
          app.db.commit()
          
          return jsonify({
              'message': 'Study session recorded successfully',
              'session_id': cursor.lastrowid
          }), 200
          
      except sqlite3.Error as e:
          print(f"\nSQLite error: {str(e)}")
          return jsonify({'error': f'Database error: {str(e)}'}), 500

    except Exception as e:
        import traceback
        print("\nError in create_study_sessions:")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

  @app.route('/api/study-sessions', methods=['GET'])
  @cross_origin()
  def get_study_sessions():
    try:
      cursor = app.db.cursor()
      
      # Get pagination parameters
      page = request.args.get('page', 1, type=int)
      per_page = request.args.get('per_page', 10, type=int)
      offset = (page - 1) * per_page

      # Get total count
      cursor.execute('''
        SELECT COUNT(*) as count 
        FROM study_sessions ss
        JOIN groups g ON g.id = ss.group_id
        JOIN study_activities sa ON sa.id = ss.study_activity_id
      ''')
      total_count = cursor.fetchone()['count']

      # Get paginated sessions
      cursor.execute('''
        SELECT 
          ss.id,
          ss.group_id,
          g.name as group_name,
          sa.id as activity_id,
          sa.name as activity_name,
          ss.created_at,
          COUNT(wri.id) as review_items_count
        FROM study_sessions ss
        JOIN groups g ON g.id = ss.group_id
        JOIN study_activities sa ON sa.id = ss.study_activity_id
        LEFT JOIN word_review_items wri ON wri.study_session_id = ss.id
        GROUP BY ss.id
        ORDER BY ss.created_at DESC
        LIMIT ? OFFSET ?
      ''', (per_page, offset))
      sessions = cursor.fetchall()

      return jsonify({
        'items': [{
          'id': session['id'],
          'group_id': session['group_id'],
          'group_name': session['group_name'],
          'activity_id': session['activity_id'],
          'activity_name': session['activity_name'],
          'start_time': session['created_at'],
          'end_time': session['created_at'],  # For now, just use the same time since we don't track end time
          'review_items_count': session['review_items_count']
        } for session in sessions],
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': math.ceil(total_count / per_page)
      })
    except Exception as e:
      return jsonify({"error": str(e)}), 500

  @app.route('/api/study-sessions/<id>', methods=['GET'])
  @cross_origin()
  def get_study_session(id):
    try:
      cursor = app.db.cursor()
      
      # Get session details
      cursor.execute('''
        SELECT 
          ss.id,
          ss.group_id,
          g.name as group_name,
          sa.id as activity_id,
          sa.name as activity_name,
          ss.created_at,
          COUNT(wri.id) as review_items_count
        FROM study_sessions ss
        JOIN groups g ON g.id = ss.group_id
        JOIN study_activities sa ON sa.id = ss.study_activity_id
        LEFT JOIN word_review_items wri ON wri.study_session_id = ss.id
        WHERE ss.id = ?
        GROUP BY ss.id
      ''', (id,))
      
      session = cursor.fetchone()
      if not session:
        return jsonify({"error": "Study session not found"}), 404

      # Get pagination parameters
      page = request.args.get('page', 1, type=int)
      per_page = request.args.get('per_page', 10, type=int)
      offset = (page - 1) * per_page

      # Get the words reviewed in this session with their review status
      cursor.execute('''
        SELECT 
          w.*,
          COALESCE(SUM(CASE WHEN wri.correct = 1 THEN 1 ELSE 0 END), 0) as session_correct_count,
          COALESCE(SUM(CASE WHEN wri.correct = 0 THEN 1 ELSE 0 END), 0) as session_wrong_count
        FROM words w
        JOIN word_review_items wri ON wri.word_id = w.id
        WHERE wri.study_session_id = ?
        GROUP BY w.id
        ORDER BY w.kanji
        LIMIT ? OFFSET ?
      ''', (id, per_page, offset))
      
      words = cursor.fetchall()

      # Get total count of words
      cursor.execute('''
        SELECT COUNT(DISTINCT w.id) as count
        FROM words w
        JOIN word_review_items wri ON wri.word_id = w.id
        WHERE wri.study_session_id = ?
      ''', (id,))
      
      total_count = cursor.fetchone()['count']

      return jsonify({
        'session': {
          'id': session['id'],
          'group_id': session['group_id'],
          'group_name': session['group_name'],
          'activity_id': session['activity_id'],
          'activity_name': session['activity_name'],
          'start_time': session['created_at'],
          'end_time': session['created_at'],  # For now, just use the same time
          'review_items_count': session['review_items_count']
        },
        'words': [{
          'id': word['id'],
          'kanji': word['kanji'],
          'romaji': word['romaji'],
          'english': word['english'],
          'correct_count': word['session_correct_count'],
          'wrong_count': word['session_wrong_count']
        } for word in words],
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': math.ceil(total_count / per_page)
      })
    except Exception as e:
      return jsonify({"error": str(e)}), 500

  @app.route('/api/study_sessions/<int:session_id>/review', methods=['POST', 'OPTIONS'])
  @cross_origin()
  def post_session_review(session_id):   
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not isinstance(data, list):
            return jsonify({'error': 'Request body must be an array of review results'}), 400
            
        # Validate each review item
        for idx, review in enumerate(data):
            # Check required fields
            if 'word_id' not in review:
                return jsonify({'error': f'Missing word_id in review at index {idx}'}), 400
            if 'is_correct' not in review:
                return jsonify({'error': f'Missing is_correct in review at index {idx}'}), 400
                
            # Validate types
            if not isinstance(review['word_id'], int):
                return jsonify({'error': f'word_id must be an integer at index {idx}'}), 400
            if not isinstance(review['is_correct'], bool):
                return jsonify({'error': f'is_correct must be a boolean at index {idx}'}), 400

        # Connect to the database
        cursor = app.db.cursor()
        
        # Check if session exists
        cursor.execute('SELECT id FROM study_sessions WHERE id = ?', (session_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Study session not found'}), 404

        # Begin transaction
        cursor.execute('BEGIN TRANSACTION')
        
        try:
            # Insert review results
            for review in data:
                cursor.execute('''
                    INSERT INTO word_review_items (
                        study_session_id,
                        word_id,
                        correct,
                        created_at
                    ) VALUES (?, ?, ?, datetime('now'))
                ''', (
                    session_id,
                    review['word_id'],
                    review['is_correct']
                ))
            
                # Update or insert into word_reviews
                cursor.execute('''
                    INSERT INTO word_reviews (
                        word_id,
                        correct_count,
                        wrong_count,
                        last_reviewed
                    ) 
                    VALUES (?, 
                        CASE WHEN ? THEN 1 ELSE 0 END,
                        CASE WHEN ? THEN 0 ELSE 1 END,
                        datetime('now')
                    )
                    ON CONFLICT(word_id) DO UPDATE SET
                        correct_count = correct_count + CASE WHEN ? THEN 1 ELSE 0 END,
                        wrong_count = wrong_count + CASE WHEN ? THEN 0 ELSE 1 END,
                        last_reviewed = datetime('now')
                ''', (
                    review['word_id'],
                    review['is_correct'],
                    review['is_correct'],
                    review['is_correct'],
                    review['is_correct']
                ))
            
            # Commit transaction
            app.db.commit()
            
            return jsonify({
                'message': 'Reviews recorded successfully',
                'session_id': session_id
            }), 200
            
        except Exception as e:
            cursor.execute('ROLLBACK')
            raise e

    except Exception as e:
        import traceback
        print("\nError in post_session_review:")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


  @app.route('/api/study-sessions/reset', methods=['POST'])
  @cross_origin()
  def reset_study_sessions():
    try:
      cursor = app.db.cursor()
      
      # First delete all word review items since they have foreign key constraints
      cursor.execute('DELETE FROM word_review_items')
      
      # Then delete all study sessions
      cursor.execute('DELETE FROM study_sessions')
      
      app.db.commit()
      
      return jsonify({"message": "Study history cleared successfully"}), 200
    except Exception as e:
      return jsonify({"error": str(e)}), 500