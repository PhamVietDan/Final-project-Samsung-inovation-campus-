from flask import Flask, request, jsonify, render_template_string
import json
from datetime import datetime
from collections import deque

app = Flask(__name__)

# Lưu trữ data từ 4 ESP32 qua Pi Gateway
esp32_data = {
    'ESP32_1': {'temp': 0, 'humi': 0, 'timestamp': '', 'status': 'offline'},
    'ESP32_2': {'temp': 0, 'humi': 0, 'timestamp': '', 'status': 'offline'},
    'ESP32_3': {'temp': 0, 'humi': 0, 'timestamp': '', 'status': 'offline'},
    'ESP32_4': {'temp': 0, 'humi': 0, 'timestamp': '', 'status': 'offline'}
}
esp32_history = {
    'ESP32_1': deque(maxlen=50),
    'ESP32_2': deque(maxlen=50), 
    'ESP32_3': deque(maxlen=50),
    'ESP32_4': deque(maxlen=50)
}

@app.route('/')
def dashboard():
    """Dashboard hiển thị data từ 4 ESP32 với biểu đồ riêng"""
    global esp32_data, esp32_history
    
    # Prepare chart data cho từng ESP32
    chart_data = {}
    total_readings = 0
    
    for esp_id in ['ESP32_1', 'ESP32_2', 'ESP32_3', 'ESP32_4']:
        chart_data[esp_id] = {
            'timestamps': [],
            'temperature': [],
            'humidity': []
        }
        
        for entry in list(esp32_history[esp_id]):
            chart_data[esp_id]['timestamps'].append(entry['timestamp'])
            chart_data[esp_id]['temperature'].append(entry['temp'])
            chart_data[esp_id]['humidity'].append(entry['humi'])
        
        total_readings += len(esp32_history[esp_id])
    
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>🌐 ESP32 Network Dashboard - UET VNU</title>
    <meta http-equiv="refresh" content="5">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .header { 
            background: rgba(31, 78, 121, 0.9); 
            color: white; 
            padding: 20px; 
            text-align: center; 
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .container { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
            margin-bottom: 20px; 
        }
        .esp32-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .panel { 
            background: rgba(255, 255, 255, 0.1); 
            backdrop-filter: blur(10px);
            padding: 20px; 
            border-radius: 15px; 
            box-shadow: 0 8px 25px rgba(0,0,0,0.2); 
        }
        .chart-container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            color: #333;
        }
        .data-item { 
            margin: 10px 0; 
            padding: 10px; 
            background: rgba(255, 255, 255, 0.2); 
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
        }
        .value { 
            font-size: 1.3em; 
            font-weight: bold; 
            color: #4CAF50; 
        }
        .timestamp { 
            color: #ccc; 
            font-size: 0.8em; 
        }
        .status { 
            padding: 5px 10px; 
            border-radius: 15px; 
            color: white; 
            font-size: 0.8em; 
            display: inline-block;
        }
        .online { background: #4CAF50; }
        .offline { background: #f44336; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #4CAF50;
        }
        .stat-label {
            font-size: 0.8em;
            color: #ccc;
            margin-top: 5px;
        }
        footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌐 ESP32 Network Dashboard</h1>
        <p>🎓 University of Engineering and Technology - Vietnam National University</p>
        <p>Real-time Temperature & Humidity from 4 ESP32 Nodes</p>
    </div>
    
    <!-- ESP32 Current Data Grid -->
    <div class="esp32-grid">
        {% for esp_id in ['ESP32_1', 'ESP32_2', 'ESP32_3', 'ESP32_4'] %}
        <div class="panel">
            <h3>📡 {{ esp_id }}</h3>
            {% if esp32_data[esp_id]['status'] == 'online' %}
                <div class="data-item">
                    <div>🌡️ Temperature: <span class="value">{{ esp32_data[esp_id]['temp'] }}°C</span></div>
                </div>
                <div class="data-item">
                    <div>💧 Humidity: <span class="value">{{ esp32_data[esp_id]['humi'] }}%</span></div>
                </div>
                <div class="timestamp">🕒 Last Update: {{ esp32_data[esp_id]['timestamp'] }}</div>
                <span class="status online">🟢 Online</span>
            {% else %}
                <div class="data-item">
                    <span class="status offline">🔴 Offline</span>
                    <p>No data from {{ esp_id }}</p>
                </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <!-- Network Statistics -->
    <div class="panel">
        <h2>📊 Network Statistics</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ active_nodes }}</div>
                <div class="stat-label">Active Nodes</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ total_readings }}</div>
                <div class="stat-label">Total Readings</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">4</div>
                <div class="stat-label">Max Nodes</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">5s</div>
                <div class="stat-label">Update Rate</div>
            </div>
        </div>
    </div>

    <!-- Charts for each ESP32 -->
    {% for esp_id in ['ESP32_1', 'ESP32_2', 'ESP32_3', 'ESP32_4'] %}
        {% if chart_data[esp_id]['timestamps']|length > 0 %}
        <div class="chart-container">
            <h2>📈 {{ esp_id }} - Temperature & Humidity Trends</h2>
            <canvas id="chart_{{ esp_id }}" width="400" height="200"></canvas>
        </div>
        {% endif %}
    {% endfor %}

    {% if total_readings == 0 %}
    <div class="chart-container">
        <h2>📊 Waiting for ESP32 Data...</h2>
        <p>Make sure Pi Gateway is running and ESP32 nodes are sending data</p>
        <p>Expected data format: POST to /api/esp32 with node_id, temp, humi</p>
    </div>
    {% endif %}

    <footer>
        <p>© 2025 University of Engineering and Technology - Vietnam National University</p>
        <p>🌐 ESP32 IoT Network Monitoring System | Total readings: {{ total_readings }}</p>
    </footer>

    <script>
        // Chart data from Flask
        const chartData = {{ chart_data_json | safe }};
        
        // Create charts for each ESP32
        {% for esp_id in ['ESP32_1', 'ESP32_2', 'ESP32_3', 'ESP32_4'] %}
            {% if chart_data[esp_id]['timestamps']|length > 0 %}
            (function() {
                const ctx = document.getElementById('chart_{{ esp_id }}').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: chartData['{{ esp_id }}']['timestamps'],
                        datasets: [{
                            label: 'Temperature (°C)',
                            data: chartData['{{ esp_id }}']['temperature'],
                            borderColor: 'rgb(255, 99, 132)',
                            backgroundColor: 'rgba(255, 99, 132, 0.1)',
                            tension: 0.4
                        }, {
                            label: 'Humidity (%)',
                            data: chartData['{{ esp_id }}']['humidity'],
                            borderColor: 'rgb(54, 162, 235)',
                            backgroundColor: 'rgba(54, 162, 235, 0.1)',
                            tension: 0.4
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        },
                        plugins: {
                            legend: {
                                position: 'top',
                            },
                            title: {
                                display: true,
                                text: '{{ esp_id }} Sensor Data'
                            }
                        }
                    }
                });
            })();
            {% endif %}
        {% endfor %}
    </script>
</body>
</html>
    ''', 
    esp32_data=esp32_data,
    chart_data=chart_data,
    chart_data_json=json.dumps(chart_data),
    total_readings=total_readings,
    active_nodes=sum(1 for data in esp32_data.values() if data['status'] == 'online'))

@app.route('/api/esp32', methods=['POST'])
def receive_esp32_data():
    """API endpoint để nhận data từ Pi Gateway cho 4 ESP32"""
    global esp32_data, esp32_history
    
    try:
        data = request.get_json() or {}
        
        # Expect data format: {"node_id": "ESP32_1", "temp": 25.5, "humi": 60.2}
        node_id = data.get('node_id', '')
        temp = data.get('temp', 0)
        humi = data.get('humi', 0)
        
        # Validate node_id
        if node_id not in esp32_data:
            return jsonify({'status': 'error', 'message': f'Invalid node_id: {node_id}. Expected: ESP32_1, ESP32_2, ESP32_3, ESP32_4'}), 400
        
        # Update current data
        esp32_data[node_id] = {
            'temp': temp,
            'humi': humi,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'status': 'online'
        }
        
        # Add to history for charts
        esp32_history[node_id].append({
            'temp': temp,
            'humi': humi,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
        print(f"📡 {node_id} Data: T:{temp}°C H:{humi}%")
        return jsonify({'status': 'success', 'message': f'Data received from {node_id}'})
        
    except Exception as e:
        print(f"❌ ESP32 Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/data')
def get_all_data():
    """API để lấy tất cả ESP32 data"""
    global esp32_data, esp32_history
    return jsonify({
        'esp32_nodes': esp32_data,
        'history_counts': {node: len(history) for node, history in esp32_history.items()},
        'total_readings': sum(len(history) for history in esp32_history.values())
    })

@app.route('/status')
def status():
    """Status page cho ESP32 network"""
    global esp32_data, esp32_history
    
    active_count = sum(1 for data in esp32_data.values() if data['status'] == 'online')
    total_readings = sum(len(history) for history in esp32_history.values())
    
    return f"""
    <html>
    <head><title>ESP32 Network Status</title></head>
    <body style="font-family: Arial; margin: 40px; background: #f5f5f5;">
        <h1>🌐 ESP32 Network Status</h1>
        <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h2>📊 Network Summary</h2>
            <p><strong>Active Nodes:</strong> {active_count}/4</p>
            <p><strong>Total Readings:</strong> {total_readings}</p>
        </div>
        
        <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h2>📡 Node Status</h2>
            {''.join([f'<p><strong>{node}:</strong> {"🟢 Online" if data["status"] == "online" else "🔴 Offline"} - Last: {data.get("timestamp", "Never")}</p>' for node, data in esp32_data.items()])}
        </div>
        
        <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h2>🔗 Quick Links</h2>
            <p><a href="/" style="color: #007bff; text-decoration: none; font-size: 18px;">📊 Main Dashboard</a></p>
            <p><a href="/api/data" style="color: #007bff; text-decoration: none;">📋 Raw Data API</a></p>
        </div>
        
        <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h2>🖥️ Current ESP32 Data</h2>
            <pre style="background: #f8f9fa; padding: 15px; border-radius: 5px;">{json.dumps(esp32_data, indent=2)}</pre>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    print("🌐 Starting ESP32 Network Dashboard Server...")
    print("📊 Dashboard: http://localhost:3000")
    print("📡 ESP32 API: POST http://localhost:3000/api/esp32")
    print("📋 Expected data: {'node_id': 'ESP32_1', 'temp': 25.5, 'humi': 60.2}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=3000, debug=True)
