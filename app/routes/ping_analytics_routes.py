from flask import Blueprint, jsonify, request
from app.utils.multi_ping_service import get_multi_ping_service
from datetime import datetime
from collections import defaultdict
from flask_cors import cross_origin

ping_analytics_bp = Blueprint('ping_analytics', __name__)

@ping_analytics_bp.route('/ping/timeout/analytics/chart', methods=['GET'])
@cross_origin()
def get_timeout_analytics_chart():
    """
    Get timeout analytics data for line chart
    Query parameters:
    - hours: time range in hours (default: 24, max: 168 for 7 days)
    - interval: data point interval in minutes (default: 15, use 0 for all/raw data)
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        interval = request.args.get('interval', 15, type=int)
        
        # Limit maximum hours to 7 days
        hours = min(hours, 168)
        
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
        
        if not service.timeout_tracker:
            return jsonify({
                'success': False,
                'error': 'Timeout tracking is disabled'
            }), 503
        
        # Get analytics data
        analytics_data = service.timeout_tracker.analytics.get_analytics_data(hours=hours)
        
        if not analytics_data:
            return jsonify({
                'success': True,
                'data': {
                    'chart_data': [],
                    'summary': {
                        'total_records': 0,
                        'time_range_hours': hours,
                        'message': 'No analytics data available yet'
                    }
                }
            })
        
        # If interval <= 0, return all raw data as chart_data
        if not interval or interval <= 0:
            grouped_data = [
                {
                    'timestamp': record['timestamp'],
                    # 'time_label': datetime.fromisoformat(record['timestamp']).strftime('%Y-%m-%d %H:%M'),
                    'timeout_count': record['total_timeout_devices'],
                }
                for record in analytics_data
            ]
        else:
            # Group data points by interval
            grouped_data = []
            current_group = []
            current_interval_start = None
            
            for record in analytics_data:
                record_time = datetime.fromisoformat(record['timestamp'])
                
                if current_interval_start is None:
                    current_interval_start = record_time
                
                # Check if we need to start a new interval group
                time_diff = (record_time - current_interval_start).total_seconds() / 60
                
                if time_diff >= interval:
                    # Process current group
                    if current_group:
                        avg_timeouts = sum(r['total_timeout_devices'] for r in current_group) / len(current_group)
                        # Use .get for backward compatibility
                        avg_critical = sum(r.get('critical_devices_count', 0) for r in current_group) / len(current_group)
                        grouped_data.append({
                            'timestamp': current_interval_start.isoformat(),
                            'time_label': current_interval_start.strftime('%H:%M'),
                            'timeout_count': round(avg_timeouts, 1),
                            'critical_count': round(avg_critical, 1)
                        })
                    
                    # Start new group
                    current_group = [record]
                    current_interval_start = record_time
                else:
                    current_group.append(record)
            
            # Process last group
            if current_group:
                avg_timeouts = sum(r['total_timeout_devices'] for r in current_group) / len(current_group)
                avg_critical = sum(r.get('critical_devices_count', 0) for r in current_group) / len(current_group)
                grouped_data.append({
                    'timestamp': current_interval_start.isoformat(),
                    'time_label': current_interval_start.strftime('%H:%M'),
                    'timeout_count': round(avg_timeouts, 1),
                    'critical_count': round(avg_critical, 1)
                })
        
        # Get summary statistics
        summary = service.timeout_tracker.analytics.get_analytics_summary(hours=hours)
        
        return jsonify({
            'success': True,
            'data': {
                'chart_data': grouped_data,
                'summary': summary,
                'config': {
                    'hours': hours,
                    'interval_minutes': interval,
                    'total_data_points': len(grouped_data)
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_analytics_bp.route('/ping/timeout/analytics/multi-day', methods=['GET'])
@cross_origin()
def get_timeout_analytics_multi_day():
    """
    Get timeout analytics data for multiple days
    Query parameters:
    - days: number of days (default: 7, max: 30)
    """
    try:
        days = request.args.get('days', 7, type=int)
        days = min(days, 30)  # Limit to 30 days
        
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
        
        if not service.timeout_tracker:
            return jsonify({
                'success': False,
                'error': 'Timeout tracking is disabled'
            }), 503
        
        # Get multi-day analytics data
        analytics_data = service.timeout_tracker.analytics.get_multi_day_analytics(days=days)
        
        if not analytics_data:
            return jsonify({
                'success': True,
                'data': {
                    'chart_data': [],
                    'summary': {
                        'total_records': 0,
                        'days': days,
                        'message': 'No analytics data available'
                    }
                }
            })
        
        # Group by hour for multi-day view
        hourly_data = defaultdict(list)
        
        for record in analytics_data:
            record_time = datetime.fromisoformat(record['timestamp'])
            hour_key = record_time.strftime('%Y-%m-%d %H:00')
            hourly_data[hour_key].append(record)
        
        # Calculate hourly averages
        chart_data = []
        for hour_key in sorted(hourly_data.keys()):
            records = hourly_data[hour_key]
            avg_timeouts = sum(r['total_timeout_devices'] for r in records) / len(records)
            avg_critical = sum(r['critical_devices_count'] for r in records) / len(records)
            
            hour_time = datetime.strptime(hour_key, '%Y-%m-%d %H:%M')
            chart_data.append({
                'timestamp': hour_time.isoformat(),
                'date_label': hour_time.strftime('%m/%d'),
                'time_label': hour_time.strftime('%H:%M'),
                'timeout_count': round(avg_timeouts, 1),
                'critical_count': round(avg_critical, 1)
            })
        
        return jsonify({
            'success': True,
            'data': {
                'chart_data': chart_data,
                'summary': {
                    'total_records': len(analytics_data),
                    'days': days,
                    'hourly_points': len(chart_data),
                    'first_record': analytics_data[0]['timestamp'] if analytics_data else None,
                    'last_record': analytics_data[-1]['timestamp'] if analytics_data else None
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_analytics_bp.route('/ping/timeout/analytics/summary', methods=['GET'])
@cross_origin()
def get_timeout_analytics_summary():
    """
    Get timeout analytics summary statistics
    Query parameters:
    - hours: time range in hours (default: 24)
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
        
        if not service.timeout_tracker:
            return jsonify({
                'success': False,
                'error': 'Timeout tracking is disabled'
            }), 503
        
        summary = service.timeout_tracker.analytics.get_analytics_summary(hours=hours)
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

