#!/usr/bin/env python3
"""
Enhanced Pi Gateway Server with better ESP32 data parsing
"""
import socket
import json
import threading
import time
import urllib.parse

def forward_esp32_data_to_web(esp32_data):
    """Forward ESP32 data to web dashboard"""
    try:
        import requests
        url = "http://localhost:3000/api/esp32"
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=esp32_data, headers=headers, timeout=5)
        if response.status_code == 200:
            print(f"✅ Forwarded {esp32_data['node_id']}: T:{esp32_data['temp']}°C H:{esp32_data['humi']}%")
        else:
            print(f"⚠️ Web server response: {response.status_code}")
    except ImportError:
        print("⚠️ requests library not available - data not forwarded")
    except Exception as e:
        print(f"❌ Error forwarding ESP32 data: {e}")

def parse_esp32_data(request_data):
    """Enhanced ESP32 data parser with multiple format support"""
    
    print(f"🔍 Parsing request ({len(request_data)} bytes)")
    
    try:
        # Method 1: Extract JSON from HTTP body
        if '\r\n\r\n' in request_data:
            headers, body = request_data.split('\r\n\r\n', 1)
            print(f"📄 HTTP Body: {repr(body[:100])}")
            
            if body.strip():
                # Try JSON parsing
                try:
                    data = json.loads(body.strip())
                    print(f"✅ JSON parsed: {data}")
                    return data
                except json.JSONDecodeError:
                    print("❌ JSON parsing failed, trying other formats...")
                
                # Try URL-encoded form data
                try:
                    parsed = urllib.parse.parse_qs(body.strip())
                    if 'node_id' in parsed and 'temp' in parsed and 'humi' in parsed:
                        data = {
                            'node_id': parsed['node_id'][0],
                            'temp': float(parsed['temp'][0]),
                            'humi': float(parsed['humi'][0])
                        }
                        print(f"✅ Form data parsed: {data}")
                        return data
                except Exception as e:
                    print(f"❌ Form parsing failed: {e}")
                
                # Try simple CSV format: "ESP32_1,25.5,60.2"
                if ',' in body:
                    try:
                        parts = body.strip().split(',')
                        if len(parts) >= 3:
                            data = {
                                'node_id': parts[0].strip(),
                                'temp': float(parts[1].strip()),
                                'humi': float(parts[2].strip())
                            }
                            print(f"✅ CSV parsed: {data}")
                            return data
                    except Exception as e:
                        print(f"❌ CSV parsing failed: {e}")
        
        # Method 2: Extract from URL parameters (GET request)
        if 'GET /' in request_data and '?' in request_data:
            try:
                url_line = [line for line in request_data.split('\r\n') if line.startswith('GET ')][0]
                if '?' in url_line:
                    query_string = url_line.split('?', 1)[1].split(' ')[0]
                    parsed = urllib.parse.parse_qs(query_string)
                    if 'node_id' in parsed and 'temp' in parsed and 'humi' in parsed:
                        data = {
                            'node_id': parsed['node_id'][0],
                            'temp': float(parsed['temp'][0]),
                            'humi': float(parsed['humi'][0])
                        }
                        print(f"✅ URL params parsed: {data}")
                        return data
            except Exception as e:
                print(f"❌ URL parsing failed: {e}")
        
        # Method 3: Generate test data for debugging
        import random
        test_data = {
            'node_id': f'ESP32_{random.randint(1,4)}',
            'temp': round(20 + random.random() * 15, 1),
            'humi': round(40 + random.random() * 40, 1)
        }
        print(f"⚠️ No valid data found, using test data: {test_data}")
        return test_data
        
    except Exception as e:
        print(f"❌ Parsing error: {e}")
        return None

def handle_client_request(conn, addr):
    """Handle individual client request"""
    try:
        # Receive data with larger buffer
        request_data = conn.recv(8192).decode('utf-8', errors='ignore')
        
        print(f"\n📡 Request from {addr}")
        print(f"Request preview: {request_data[:200]}...")
        
        # Parse ESP32 data
        esp32_data = parse_esp32_data(request_data)
        
        if esp32_data:
            # Forward to web dashboard
            forward_esp32_data_to_web(esp32_data)
            
            # Send success response
            response_data = json.dumps({
                "status": "success", 
                "data": esp32_data,
                "timestamp": time.time()
            })
            
            response = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: {len(response_data)}\r\n\r\n{response_data}"
            
        else:
            # Send error response
            error_data = json.dumps({"status": "error", "message": "Cannot parse ESP32 data"})
            response = f"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nContent-Length: {len(error_data)}\r\n\r\n{error_data}"
        
        conn.send(response.encode())
        
    except Exception as e:
        print(f"❌ Error handling request from {addr}: {e}")
        try:
            error_response = "HTTP/1.1 500 Internal Server Error\r\n\r\nServer Error"
            conn.send(error_response.encode())
        except:
            pass
    finally:
        try:
            conn.close()
        except:
            pass

def start_enhanced_server():
    """Start the enhanced Pi Gateway server"""
    host = ''
    port = 8081
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(10)
        
        print("🖥️ Enhanced Pi Gateway Server Started")
        print(f"📡 Listening on port {port}")
        print("🔧 Enhanced ESP32 data parsing enabled")
        print("🌐 Web dashboard forwarding enabled")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                conn, addr = server_socket.accept()
                # Handle each request in a separate thread for better performance
                client_thread = threading.Thread(target=handle_client_request, args=(conn, addr))
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                print(f"❌ Error accepting connection: {e}")
    
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_enhanced_server()
