from flask import Blueprint, render_template, request, jsonify, session, abort, url_for
from app.extensions import db, csrf
from app.models import Comparison
from app.services.bike_service import get_bikes_by_uuids
from app.services.ai_service import create_ai_prompt, generate_comparison_with_ai_from_bikes
import os
import json

bp = Blueprint('compare', __name__)

@bp.route('/api/compare_list')
def api_compare_list():
    return jsonify({'compare_list': session.get('compare_list', [])})

def get_compare_list():
    try:
        return session.get('compare_list', [])
    except Exception as e:
        print(f"Error getting compare list from session: {e}")
        return []

def save_compare_list(compare_list):
    try:
        session['compare_list'] = compare_list
        session.modified = True  # Ensure session is marked as modified
    except Exception as e:
        print(f"Error saving compare list to session: {e}")

@bp.route('/add_to_compare', methods=['POST'])
@csrf.exempt
def add_to_compare():
    try:
        # Get bike_id from request data instead of URL path
        bike_id = request.json.get('bike_id') if request.is_json else request.form.get('bike_id')
        
        # Check if bike_id is valid
        if not bike_id or bike_id.strip() == '':
            return jsonify({'success': False, 'error': 'Invalid bike ID'}), 400
        
        # Store the bike_id in its original form (no encoding needed since we're using JSON body)
        normalized_bike_id = bike_id
        
        print(f"Adding bike to compare - Bike ID: {bike_id}")
        
        compare_list = get_compare_list()
        if normalized_bike_id not in compare_list:
            if len(compare_list) < 4:
                compare_list.append(normalized_bike_id)
                save_compare_list(compare_list)

                # ✅ Increment popularity count in database
                try:
                    from scripts.data.migrate_compare_counts import update_compare_count
                    update_compare_count(normalized_bike_id)
                    print(f"Updated compare count for bike {normalized_bike_id}")
                except Exception as e:
                    print("Error updating compare counts:", e)

                return jsonify({'success': True, 'compare_list': compare_list})
            else:
                return jsonify({'success': False, 'error': 'You can compare up to 4 bikes only.'}), 400
        return jsonify({'success': True, 'compare_list': compare_list})
    except Exception as e:
        print(f"Error in add_to_compare: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@bp.route('/remove_from_compare', methods=['POST'])
@csrf.exempt
def remove_from_compare():
    try:
        # Get bike_id from request data instead of URL path
        bike_id = request.json.get('bike_id') if request.is_json else request.form.get('bike_id')
        
        # Check if bike_id is valid
        if not bike_id or bike_id.strip() == '':
            return jsonify({'success': False, 'error': 'Invalid bike ID'}), 400
        
        # Store the bike_id in its original form (no encoding needed since we're using JSON body)
        normalized_bike_id = bike_id
        
        print(f"Removing bike from compare - Bike ID: {bike_id}")
        
        compare_list = get_compare_list()
        if normalized_bike_id in compare_list:
            compare_list.remove(normalized_bike_id)
            save_compare_list(compare_list)
        return jsonify({'success': True, 'compare_list': compare_list})
    except Exception as e:
        print(f"Error in remove_from_compare: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@bp.route('/compare_bikes')
def compare_bikes():
    compare_list = get_compare_list()
    
    # Optimized: Only load bikes that are being compared (not all bikes!)
    bikes_to_compare = get_bikes_by_uuids(compare_list) if compare_list else []

    # Key fields to always show
    always_show = ["firm", "model", "price", "year", "motor", "battery"]

    # Disc_price: show if at least one bike has it non-empty
    show_disc_price = any(
        bike.get("disc_price") not in [None, '', 'N/A', '#N/A']
        for bike in bikes_to_compare
    )
    if show_disc_price:
        always_show.append("disc_price")

    # Get all unique fields from all bikes
    all_fields = set()
    for bike in bikes_to_compare:
        all_fields.update(bike.keys())

    # Remove fields you don't want to show
    exclude_fields = {'id', 'slug', 'image_url', 'product_url'}
    candidate_fields = [f for f in all_fields if f not in exclude_fields and f not in always_show]

    # Only keep fields that are present and non-empty in ALL bikes
    fields_to_show = []
    for field in candidate_fields:
        if all(
            field in bike and bike[field] not in [None, '', 'N/A', '#N/A']
            for bike in bikes_to_compare
        ):
            fields_to_show.append(field)

    # Final order: always_show first, then the rest (sorted)
    fields_to_show = always_show + sorted(fields_to_show)

    return render_template(
        'compare_bikes.html',
        bikes=bikes_to_compare,
        fields_to_show=fields_to_show,
    )

@bp.route('/comparison/<path:slug>')
def view_comparison(slug):
    """View a specific comparison by slug"""
    try:
        # Check if slug is a number (old ID format)
        if slug.isdigit():
            comparison = db.session.query(Comparison).filter_by(id=int(slug)).first()
        else:
            # New slug format
            comparison = db.session.query(Comparison).filter_by(slug=slug).first()

        if not comparison:
            abort(404)

        # Get bike IDs and load bike details
        import json
        bike_ids = json.loads(comparison.bike_ids) if comparison.bike_ids else []
        bikes_to_compare = get_bikes_by_uuids(bike_ids)
        
        # Get comparison data
        comparison_data = json.loads(comparison.comparison_data) if comparison.comparison_data else {}

        # Create a shareable URL for this comparison (prefer slug over ID)
        if comparison.slug:
            share_url = request.host_url.rstrip('/') + url_for('compare.view_comparison', slug=comparison.slug)
        else:
            share_url = request.host_url.rstrip('/') + url_for('compare.view_comparison', comparison_id=comparison.id)

        return render_template('shared_comparison.html',
                             comparison=comparison,
                             bikes=bikes_to_compare,
                             comparison_data=comparison_data,
                             share_url=share_url)

    except Exception as e:
        print(f"Error viewing comparison {slug}: {e}")
        abort(500)

@bp.route('/clear_compare', methods=['POST'])
def clear_compare():
    session['compare_list'] = []
    return jsonify({'success': True})

@bp.route('/api/compare_ai_from_session', methods=['GET'])
def compare_ai_from_session():
    try:
        compare_list = get_compare_list()
        
        if len(compare_list) < 2:
            return jsonify({"error": "צריך לבחור לפחות שני דגמים להשוואה."}), 400

        # Optimized: Only load bikes that are being compared (not all bikes!)
        bikes_to_compare = get_bikes_by_uuids(compare_list)
        
        if len(bikes_to_compare) < 2:
            return jsonify({"error": "לא נמצאו מספיק דגמים להשוואה. נסה לבחור דגמים אחרים."}), 400
        
        # Build AI result using async web research + Responses API
        # We no longer pass a plain prompt; instead we send the bikes list.
        # Kept create_ai_prompt import for backward compatibility if needed elsewhere.
    except Exception as e:
        return jsonify({"error": "שגיאה בטעינת נתוני האופניים", "details": str(e)}), 500

    try:
        print(f"Starting AI comparison for {len(bikes_to_compare)} bikes")
        # Generate comparison using AI (async web research + Responses)
        comparison_result = generate_comparison_with_ai_from_bikes(bikes_to_compare)
        
        # Check if AI generation failed
        if "error" in comparison_result:
            print(f"AI comparison failed: {comparison_result['error']}")
            return jsonify({"error": comparison_result["error"]}), 500
        
        print(f"AI comparison successful, got keys: {list(comparison_result.keys())}")
        
        # Save to database
        try:
            # Create new comparison record
            comparison = Comparison()
            comparison.bike_ids = json.dumps(compare_list)  # Store as JSON string
            comparison.comparison_data = json.dumps(comparison_result)  # Store as JSON string
            
            # Generate slug (need to update method signature to not need session)
            # For now, use a simple slug based on bike IDs
            comparison.slug = '-vs-'.join(compare_list[:4])  # Limit to 4 bikes for URL
            
            db.session.add(comparison)
            db.session.commit()
            
            # Create share URL - handle both development and production
            try:
                # Try to get the full URL
                share_url = request.host_url.rstrip('/') + url_for('compare.view_comparison', slug=comparison.slug)
                print(f"Method 1 - Generated share URL: {share_url}")
            except Exception as e:
                print(f"Error generating share URL: {e}")
                # Fallback: use relative URL
                share_url = url_for('compare.view_comparison', slug=comparison.slug, _external=True)
            
            print(f"Generated share URL: {share_url}")
            
            # Create response data
            response_data = {
                "success": True,
                "data": comparison_result,
                "comparison_id": comparison.id,
                "share_url": share_url
            }
            
            # Return the comparison data
            return jsonify(response_data)
            
        except Exception as e:
            db.session.rollback()
            print(f"Database error: {e}")
            return jsonify({"error": "שגיאה בשמירת ההשוואה", "details": str(e)}), 500
            
    except Exception as e:
        print(f"Error in compare_ai_from_session: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "שגיאה ביצירת ההשוואה", "details": str(e)}), 500
