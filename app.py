#!/usr/bin/env python3
"""
BLE Data Collector with Network Simulation - Linux
Full-screen dashboard with Raspberry Pi Gateway + 4 ESP32 nodes simulation
"""

import asyncio
import bleak
from bleak import BleakClient, BleakScanner
import time
import sys
import os
import subprocess
import json
import math
import random
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.patches as patches
import networkx as nx
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import threading
from datetime import datetime
import json
import csv
from collections import deque, defaultdict
import os
import subprocess
import random
import math
import requests  # Added for Raspberry Pi server communication
import platform
import re

# Flask imports for ESP32 data handling
try:
    from flask import request, jsonify
except ImportError:
    print("Flask not installed - ESP32 web server features disabled")
    request = None
    jsonify = lambda x: x

def handle_esp_data():
    if request is None:
        return {"status": "Flask not available"}
    data = request.data.decode('utf-8')
    print("Received from ESP:", data)
    return jsonify({"status": "success", "temp": 25, "humi": 60})
# Network simulation parameters
MAX_NODES = 5  # 1 Pi Gateway + 4 ESP32 nodes
SIMULATION_AREA = (800, 600)  # Width x Height
TRANSMISSION_RANGE = 200
UPDATE_INTERVAL = 3  # seconds

# Real device configuration for ESP32 Gateway
TARGET_DEVICE = "CC:DB:A7:48:62:CC"  # Update this to your ESP32's MAC address
DEVICE_NAME = "ESP4_Gateway"

# ESP32 BLE Service and Characteristic UUIDs
TEMPERATURE_SERVICE_UUID = "180C"  # Environmental Sensing Service
TEMPERATURE_CHAR_UUID = "2A56"    # Digital characteristic for sensor data
CHARACTERISTIC_UUID = "abcdefab-1234-1234-1234-abcdefabcdef"  # New characteristic UUID

def check_bluetooth_permissions():
    """Check if Bluetooth permissions are properly configured on Linux"""
    try:
        import os
        import subprocess
        
        # On Windows, return True as BLE works differently
        if os.name == 'nt':
            return True, "Windows system - BLE permissions OK"
            
        # Check if running as root or with proper permissions
        if os.geteuid() == 0:
            return True, "Running as root - Bluetooth access granted"
        
        # Check if user is in bluetooth group
        groups = subprocess.check_output(['groups'], text=True).strip()
        if 'bluetooth' in groups:
            return True, "User in bluetooth group - permissions OK"
        
        return False, "Need root privileges or add user to bluetooth group: sudo usermod -a -G bluetooth $USER"
    except Exception as e:
        return False, f"Permission check failed: {e}"

def setup_linux_display():
    """Setup display for Linux systems"""
    try:
        import os
        # Ensure DISPLAY is set for GUI
        if 'DISPLAY' not in os.environ and os.name != 'nt':
            os.environ['DISPLAY'] = ':0'
        
        # Set matplotlib backend for Linux
        import matplotlib
        matplotlib.use('TkAgg')
        
        return True, "Display configured successfully"
    except Exception as e:
        return False, f"Display setup failed: {e}"
    except Exception as e:
        return False, f"Display setup failed: {e}"

class NetworkNode:
    """Network Node implementation for Pi Gateway + ESP32 simulation"""
    def __init__(self, node_id, x, y, node_type="ESP32"):
        self.node_id = node_id
        self.x = x
        self.y = y
        self.node_type = node_type  # "Pi_Gateway" or "ESP32"
        self.is_active = True
        self.is_real_device = (node_id == "real_device")
        self.last_update = datetime.now()
        
        # Neighbors within transmission range
        self.neighbors = set()
        
        # Individual data collection for each node
        self.sensor_data = deque(maxlen=100)  # Store last 100 readings
        self.timestamps = deque(maxlen=100)   # Corresponding timestamps
        self.button_events = deque(maxlen=50) # Button events
        
        # Current sensor values - different ranges for Pi vs ESP32
        if node_type == "Pi_Gateway":
            self.temperature = random.uniform(30.0, 45.0) if not self.is_real_device else None
            self.humidity = random.uniform(35.0, 65.0) if not self.is_real_device else None
            self.cpu_usage = random.uniform(10.0, 80.0) if not self.is_real_device else None
            self.memory_usage = random.uniform(20.0, 90.0) if not self.is_real_device else None
        else:  # ESP32
            self.temperature = random.uniform(18.0, 35.0) if not self.is_real_device else None
            self.humidity = random.uniform(40.0, 85.0) if not self.is_real_device else None
            self.sensor_value = random.randint(10, 100) if not self.is_real_device else None
            self.light_level = random.randint(0, 1023) if not self.is_real_device else None
        
        self.battery_level = random.randint(70, 100) if not self.is_real_device else 100
        
        # Data collection statistics
        self.total_readings = 0
        self.data_start_time = datetime.now()
        
    def add_sensor_reading(self, **kwargs):
        """Add a sensor reading to this specific node"""
        timestamp = datetime.now()
        
        # Update values based on what's provided
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        
        # Store the reading based on node type
        if self.node_type == "Pi_Gateway":
            reading = {
                'temperature': self.temperature,
                'humidity': self.humidity,
                'cpu_usage': self.cpu_usage,
                'memory_usage': self.memory_usage,
                'battery_level': self.battery_level
            }
        else:  # ESP32
            reading = {
                'temperature': self.temperature,
                'humidity': self.humidity,
                'sensor_value': self.sensor_value,
                'light_level': self.light_level,
                'battery_level': self.battery_level
            }
        
        self.sensor_data.append(reading)
        self.timestamps.append(timestamp)
        self.total_readings += 1
        self.last_update = timestamp
        
    def add_button_event(self, pressed):
        """Add a button event to this specific node"""
        timestamp = datetime.now()
        event = {
            'timestamp': timestamp,
            'state': 'PRESSED' if pressed else 'RELEASED'
        }
        self.button_events.append(event)
        self.last_update = timestamp
        
    def get_latest_data(self):
        """Get the latest sensor data for this node"""
        if not self.sensor_data:
            return None
        return {
            'node_id': self.node_id,
            'timestamp': self.timestamps[-1],
            'data': self.sensor_data[-1]
        }
        
    def get_node_statistics(self):
        """Get statistics for this node"""
        uptime = datetime.now() - self.data_start_time
        return {
            'node_id': self.node_id,
            'node_type': self.node_type,
            'is_active': self.is_active,
            'is_real_device': self.is_real_device,
            'total_readings': self.total_readings,
            'button_events': len(self.button_events),
            'uptime_seconds': uptime.total_seconds(),
            'neighbors_count': len(self.neighbors),
            'battery_level': self.battery_level,
            'last_update': self.last_update
        }
        
    def update_real_data(self, sensor_data):
        """Update node with real ESP32 data"""
        if self.is_real_device and isinstance(sensor_data, dict):
            # Update with real sensor values
            for key, value in sensor_data.items():
                if hasattr(self, key) and value is not None:
                    setattr(self, key, value)
            
            # Add real sensor reading
            self.add_sensor_reading(**sensor_data)
        
    def update_position(self, x, y):
        """Update node position"""
        self.x = x
        self.y = y
        self.last_update = datetime.now()
        
    def distance_to(self, other_node):
        """Calculate Euclidean distance to another node"""
        return math.sqrt((self.x - other_node.x)**2 + (self.y - other_node.y)**2)
        
    def is_neighbor(self, other_node):
        """Check if another node is within transmission range"""
        return self.distance_to(other_node) <= TRANSMISSION_RANGE
        
    def update_neighbors(self, all_nodes):
        """Update neighbor list based on current positions"""
        self.neighbors.clear()
        for node in all_nodes.values():
            if node.node_id != self.node_id and node.is_active:
                if self.is_neighbor(node):
                    self.neighbors.add(node.node_id)

class NetworkManager:
    """Real ESP32 Network Manager with Routing Visualization"""
    def __init__(self):
        self.nodes = {}
        self.routing_table = {}
        self.data_paths = deque(maxlen=100)  # Store recent data transmission paths
        self.network_graph = nx.Graph()
        self.is_running = False
        self.pi_gateway_node = None  # Reference to Pi gateway node
        
        # Real network statistics
        self.total_data_packets = 0
        self.total_routing_updates = 0
        self.total_heartbeats = 0
        self.network_uptime = 0
        
    def add_real_node(self, node_id, x, y, node_type="ESP32", is_gateway=False):
        """Add a real ESP32 node to the network"""
        node = NetworkNode(node_id, x, y, node_type)
        node.is_real_device = True
        self.nodes[node_id] = node
        
        if is_gateway:
            node.node_type = "Pi_Gateway"
            self.pi_gateway_node = node
            
        # Initialize routing table entry
        self.routing_table[node_id] = {
            'next_hop': None,
            'distance': 0 if is_gateway else float('inf'),
            'last_update': datetime.now()
        }
            
        return node
        
    def update_node_data(self, node_id, sensor_data):
        """Update real node with ESP32 data"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.update_real_data(sensor_data)
            
            # Record data transmission path
            self.record_data_path(node_id, sensor_data)
            self.total_data_packets += 1
            
    def record_data_path(self, source_node_id, data):
        """Record the path data took through the network"""
        timestamp = datetime.now()
        
        # Find routing path to gateway
        path = self.find_routing_path(source_node_id, "gateway")
        
        path_record = {
            'timestamp': timestamp,
            'source': source_node_id,
            'destination': 'gateway',
            'path': path,
            'data_size': len(str(data)),
            'hops': len(path) - 1 if path else 0
        }
        
        self.data_paths.append(path_record)
        
    def find_routing_path(self, source, destination):
        """Find routing path between nodes using shortest path"""
        try:
            if self.network_graph.has_node(source) and self.network_graph.has_node(destination):
                return nx.shortest_path(self.network_graph, source, destination)
        except nx.NetworkXNoPath:
            pass
        return [source]  # Fallback to source only
        
    def update_routing_table(self):
        """Update routing table based on current network topology"""
        if not self.nodes:
            return
            
        # Find gateway node
        gateway_id = None
        for node_id, node in self.nodes.items():
            if node.node_type == "Pi_Gateway":
                gateway_id = node_id
                break
                
        if not gateway_id:
            return
            
        # Calculate shortest paths to gateway using Dijkstra's algorithm
        for node_id in self.nodes:
            if node_id != gateway_id:
                try:
                    if self.network_graph.has_node(node_id) and self.network_graph.has_node(gateway_id):
                        path = nx.shortest_path(self.network_graph, node_id, gateway_id)
                        distance = nx.shortest_path_length(self.network_graph, node_id, gateway_id)
                        next_hop = path[1] if len(path) > 1 else gateway_id
                        
                        self.routing_table[node_id] = {
                            'next_hop': next_hop,
                            'distance': distance,
                            'last_update': datetime.now()
                        }
                except nx.NetworkXNoPath:
                    self.routing_table[node_id] = {
                        'next_hop': None,
                        'distance': float('inf'),
                        'last_update': datetime.now()
                    }
                    
        self.total_routing_updates += 1
        
    def update_network_topology(self):
        """Update network topology based on real node positions and connectivity"""
        # Clear and rebuild network graph
        self.network_graph.clear()
        
        # Add all active nodes
        for node in self.nodes.values():
            if node.is_active:
                self.network_graph.add_node(node.node_id, 
                                          pos=(node.x, node.y),
                                          node_type=node.node_type,
                                          is_real=True)
                
        # Add edges based on transmission range
        for node in self.nodes.values():
            if node.is_active:
                node.update_neighbors(self.nodes)
                for neighbor_id in node.neighbors:
                    if neighbor_id in self.nodes and self.nodes[neighbor_id].is_active:
                        self.network_graph.add_edge(node.node_id, neighbor_id)
                        
        # Update routing table
        self.update_routing_table()
        
    def get_routing_info(self):
        """Get current routing table information"""
        routing_info = {}
        for node_id, route_data in self.routing_table.items():
            if node_id in self.nodes:
                node = self.nodes[node_id]
                routing_info[node_id] = {
                    'node_type': node.node_type,
                    'next_hop': route_data['next_hop'],
                    'distance': route_data['distance'],
                    'last_update': route_data['last_update'],
                    'is_reachable': route_data['distance'] != float('inf')
                }
        return routing_info
        
    def get_recent_data_paths(self, limit=10):
        """Get recent data transmission paths"""
        return list(self.data_paths)[-limit:]
    
    def toggle_node(self, node_id):
        """Toggle node active/inactive state"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.is_active = not node.is_active
            print(f"Node {node_id} {'activated' if node.is_active else 'deactivated'}")
        
    def get_network_stats(self):
        """Get real network statistics"""
        active_nodes = sum(1 for node in self.nodes.values() if node.is_active)
        pi_nodes = sum(1 for node in self.nodes.values() if node.node_type == "Pi_Gateway")
        esp32_nodes = sum(1 for node in self.nodes.values() if node.node_type == "ESP32")
        reachable_nodes = sum(1 for route in self.routing_table.values() 
                            if route['distance'] != float('inf'))
        
        return {
            'active_nodes': active_nodes,
            'total_nodes': len(self.nodes),
            'pi_nodes': pi_nodes,
            'esp32_nodes': esp32_nodes,
            'reachable_nodes': reachable_nodes,
            'total_data_packets': self.total_data_packets,
            'total_heartbeats': self.total_heartbeats,
            'total_routing_updates': self.total_routing_updates,
            'network_uptime': self.network_uptime,
            'is_connected': nx.is_connected(self.network_graph) if self.network_graph.nodes() else False,
            'average_path_length': nx.average_shortest_path_length(self.network_graph) if nx.is_connected(self.network_graph) else 0
        }

class DataCollector:
    def __init__(self, network_manager=None):
        self.sensor_data = deque(maxlen=1000)  # Store last 1000 readings
        self.node_data = {}  # Store data for each ESP node
        self.timestamps = deque(maxlen=1000)
        self.is_collecting = False
        self.device = None
        self.collection_start_time = None
        self.network_manager = network_manager
        
        # Network data
        self.network_events = deque(maxlen=500)
        
    def add_sensor_data(self, payload):
        """Parse and store multi-node sensor data from ESP32"""
        timestamp = datetime.now()
        self.timestamps.append(timestamp)
        
        # Store raw payload
        self.sensor_data.append(payload)
        
        # Parse node data: "ESP1,24.5,55.2|ESP2,25.1,58.6|ESP3,26.3,60.1"
        try:
            nodes = payload.split('|')
            for node_str in nodes:
                if ',' in node_str:
                    parts = node_str.split(',')
                    if len(parts) >= 3:
                        node_id = parts[0].strip()
                        temperature = float(parts[1])
                        humidity = float(parts[2])
                        
                        # Additional sensor data if available
                        sensor_data = {
                            'temperature': temperature,
                            'humidity': humidity
                        }
                        
                        # Parse additional fields if present
                        if len(parts) > 3:
                            sensor_data['sensor_value'] = float(parts[3])
                        if len(parts) > 4:
                            sensor_data['light_level'] = int(parts[4])
                        if len(parts) > 5:
                            sensor_data['battery_level'] = int(parts[5])
                        
                        self.node_data[node_id] = {
                            **sensor_data,
                            'timestamp': timestamp
                        }
                        
                        # Update network manager if available
                        if self.network_manager and node_id in self.network_manager.nodes:
                            self.network_manager.update_node_data(node_id, sensor_data)
                        else:
                            # Auto-create node if it doesn't exist
                            if self.network_manager and node_id not in self.network_manager.nodes:
                                # Position new nodes in a grid pattern
                                node_count = len(self.network_manager.nodes)
                                x = 200 + (node_count % 3) * 200
                                y = 150 + (node_count // 3) * 200
                                self.network_manager.add_real_node(node_id, x, y, "ESP32")
                                self.network_manager.update_node_data(node_id, sensor_data)
                                
        except Exception as e:
            print(f"Error parsing node data: {e}")
            
        if self.collection_start_time is None:
            self.collection_start_time = timestamp
            
        # Add network event
        self.network_events.append({
            'timestamp': timestamp,
            'type': 'sensor_data',
            'node_id': 'gateway',
            'value': payload
        })
            
    def add_button_event(self, pressed, node_id="gateway"):
        """Add button event"""
        timestamp = datetime.now()
        
        # Update network manager if available
        if self.network_manager and node_id in self.network_manager.nodes:
            self.network_manager.nodes[node_id].add_button_event(pressed)
        
        # Add network event
        self.network_events.append({
            'timestamp': timestamp,
            'type': 'button_event',
            'node_id': node_id,
            'state': 'PRESSED' if pressed else 'RELEASED'
        })
        
    def get_all_nodes_data(self):
        """Get data from all nodes in the network"""
        if self.network_manager:
            all_data = {}
            for node_id, node in self.network_manager.nodes.items():
                all_data[node_id] = {
                    'latest_data': node.get_latest_data(),
                    'statistics': node.get_node_statistics(),
                    'recent_readings': list(node.sensor_data)[-10:],
                    'recent_events': list(node.button_events)[-5:]
                }
            return all_data
        return {}
        
    def get_node_data(self, node_id):
        """Get data for a specific node"""
        if self.network_manager and node_id in self.network_manager.nodes:
            node = self.network_manager.nodes[node_id]
            return {
                'latest_data': node.get_latest_data(),
                'statistics': node.get_node_statistics(),
                'recent_readings': list(node.sensor_data)[-10:],
                'recent_events': list(node.button_events)[-5:]
            }
        return None
        
    def export_to_csv(self, filename):
        """Export collected data to CSV file"""
        try:
            # Prepare sensor data with node information
            sensor_records = []
            for i, (timestamp, payload) in enumerate(zip(self.timestamps, self.sensor_data)):
                # Parse payload for individual nodes
                try:
                    nodes = payload.split('|')
                    for node_str in nodes:
                        if ',' in node_str:
                            parts = node_str.split(',')
                            if len(parts) >= 3:
                                sensor_records.append({
                                    'timestamp': timestamp,
                                    'node_id': parts[0],
                                    'temperature': float(parts[1]),
                                    'humidity': float(parts[2]),
                                    'raw_payload': payload
                                })
                except:
                    # Fallback for unparseable data
                    sensor_records.append({
                        'timestamp': timestamp,
                        'node_id': 'Unknown',
                        'temperature': 0,
                        'humidity': 0,
                        'raw_payload': payload
                    })
            
            sensor_df = pd.DataFrame(sensor_records)
            
            # Network events
            network_df = pd.DataFrame(self.network_events)
            
            # Individual node data
            node_data_records = []
            if self.network_manager:
                all_nodes_data = self.get_all_nodes_data()
                for node_id, node_info in all_nodes_data.items():
                    node = self.network_manager.nodes[node_id]
                    for i, (timestamp, reading) in enumerate(zip(node.timestamps, node.sensor_data)):
                        record = {
                            'node_id': node_id,
                            'node_type': node.node_type,
                            'timestamp': timestamp,
                            'is_real_device': node.is_real_device,
                            'position_x': node.x,
                            'position_y': node.y,
                            **reading  # Unpack all sensor readings
                        }
                        node_data_records.append(record)
            
            node_data_df = pd.DataFrame(node_data_records)
            
            # Save files
            sensor_filename = f"{filename}_esp32_sensor_data.csv"
            network_filename = f"{filename}_network_events.csv"
            nodes_filename = f"{filename}_individual_nodes.csv"
            
            sensor_df.to_csv(sensor_filename, index=False)
            if not network_df.empty:
                network_df.to_csv(network_filename, index=False)
            if not node_data_df.empty:
                node_data_df.to_csv(nodes_filename, index=False)
                
            return sensor_filename, network_filename, nodes_filename
        except Exception as e:
            raise Exception(f"Error exporting data: {e}")
            
    def export_to_json(self, filename):
        """Export collected data to JSON file"""
        try:
            # Get all nodes data
            all_nodes_data = self.get_all_nodes_data() if self.network_manager else {}
            
            data = {
                'collection_info': {
                    'device_name': DEVICE_NAME,
                    'device_address': TARGET_DEVICE,
                    'start_time': self.collection_start_time.isoformat() if self.collection_start_time else None,
                    'end_time': datetime.now().isoformat(),
                    'total_sensor_readings': len(self.sensor_data),
                    'total_nodes': len(self.node_data),
                    'total_network_events': len(self.network_events),
                    'platform': 'Linux - Pi Gateway + ESP32 Network Simulation'
                },
                'sensor_data': [
                    {
                        'timestamp': ts.isoformat(),
                        'raw_payload': payload
                    }
                    for ts, payload in zip(self.timestamps, self.sensor_data)
                ],
                'node_data': {
                    node_id: {
                        'temperature': data['temperature'],
                        'humidity': data['humidity'],
                        'last_update': data['timestamp'].isoformat()
                    }
                    for node_id, data in self.node_data.items()
                },
                'network_events': [
                    {
                        'timestamp': event['timestamp'].isoformat(),
                        'type': event['type'],
                        'node_id': event['node_id'],
                        'data': event.get('value') or event.get('state')
                    }
                    for event in self.network_events
                ],
                'individual_nodes': {}
            }
            
            # Add individual node data
            for node_id, node_info in all_nodes_data.items():
                node = self.network_manager.nodes[node_id]
                data['individual_nodes'][node_id] = {
                    'node_type': node.node_type,
                    'statistics': node_info['statistics'],
                    'sensor_readings': [
                        {
                            'timestamp': ts.isoformat(),
                            'data': reading
                        }
                        for ts, reading in zip(node.timestamps, node.sensor_data)
                    ],
                    'button_events': [
                        {
                            'timestamp': event['timestamp'].isoformat(),
                            'state': event['state']
                        }
                        for event in node.button_events
                    ],
                    'position': {'x': node.x, 'y': node.y}
                }
            
            with open(f"{filename}.json", 'w') as f:
                json.dump(data, f, indent=2)
                
            return f"{filename}.json"
        except Exception as e:
            raise Exception(f"Error exporting to JSON: {e}")

class BLEManager:
    def __init__(self, data_collector, update_callback=None, network_manager=None):
        self.data_collector = data_collector
        self.update_callback = update_callback
        self.network_manager = network_manager
        self.connected_devices = {}  # Dictionary to track connected devices
        self.is_scanning = False
        self.scan_task = None
        self.log_file = "log_ble.csv"
        
        # Initialize log file
        try:
            with open(self.log_file, "w") as f:
                f.write("device_name,data,timestamp\n")
        except Exception as e:
            print(f"Error initializing log file: {e}")
        
    async def connect_and_listen(self, address, name):
        """Connect to a single ESP32 device and start listening"""
        if address in self.connected_devices:
            return  # Already connected

        client = BleakClient(address)
        try:
            await client.connect()
            if client.is_connected:
                print(f"✅ Connected to {name} ({address})")
                
                # List all services and characteristics
                services = client.services
                available_chars = []
                
                for service in services:
                    print(f"📋 Service: {service.uuid}")
                    for char in service.characteristics:
                        print(f"   ├─ Characteristic: {char.uuid} (Properties: {char.properties})")
                        available_chars.append(char.uuid)
                
                # Try to find a suitable characteristic for notifications
                target_char = None
                
                # Priority order: try our UUID first, then common UUIDs, then any notify-capable
                char_priority = [
                    CHARACTERISTIC_UUID,  # Our preferred UUID
                    "abcdefab-1234-1234-1234-abcdefabcdef",  # Alternative format
                    "0000ffe1-0000-1000-8000-00805f9b34fb",  # Common ESP32 UART UUID
                    "6e400003-b5a3-f393-e0a9-e50e24dcca9e",  # Nordic UART TX
                ]
                
                for char_uuid in char_priority:
                    try:
                        for service in services:
                            for char in service.characteristics:
                                if str(char.uuid).lower() == char_uuid.lower():
                                    if "notify" in char.properties:
                                        target_char = char.uuid
                                        print(f"🎯 Found target characteristic: {target_char}")
                                        break
                            if target_char:
                                break
                        if target_char:
                            break
                    except Exception as search_error:
                        print(f"Error searching for {char_uuid}: {search_error}")
                
                # If no specific UUID found, find any characteristic with notify capability
                if not target_char:
                    print("🔍 Looking for any notify-capable characteristic...")
                    for service in services:
                        for char in service.characteristics:
                            if "notify" in char.properties:
                                target_char = char.uuid
                                print(f"📡 Using characteristic: {target_char}")
                                break
                        if target_char:
                            break
                
                if not target_char:
                    print(f"❌ No suitable characteristic found for {name}")
                    if client.is_connected:
                        await client.disconnect()
                    return
                
                def notification_handler(sender, data):
                    try:
                        text = data.decode('utf-8')
                    except:
                        text = str(data)
                    
                    print(f"📡 [{name}] {text}")
                    
                    # Process the data through existing data collector
                    self.data_collector.add_sensor_data(f"{name},{text}")
                    
                    # Log to CSV file
                    try:
                        timestamp = datetime.now().isoformat()
                        with open(self.log_file, "a") as f:
                            f.write(f"{name},{text},{timestamp}\n")
                    except Exception as e:
                        print(f"Error logging data: {e}")
                    
                    # Update network manager if available
                    if self.network_manager:
                        # Auto-create node if it doesn't exist
                        if name not in self.network_manager.nodes:
                            node_count = len(self.network_manager.nodes)
                            x = 200 + (node_count % 4) * 150
                            y = 150 + (node_count // 4) * 150
                            self.network_manager.add_real_node(name, x, y, "ESP32")
                        
                        # Parse and update node data
                        try:
                            # Try to parse as "temp,humi,sensor,light,battery" format
                            parts = text.split(',')
                            if len(parts) >= 2:
                                sensor_data = {
                                    'temperature': float(parts[0]) if parts[0].replace('.','').isdigit() else None,
                                    'humidity': float(parts[1]) if len(parts) > 1 and parts[1].replace('.','').isdigit() else None
                                }
                                if len(parts) > 2:
                                    sensor_data['sensor_value'] = float(parts[2]) if parts[2].replace('.','').isdigit() else None
                                if len(parts) > 3:
                                    sensor_data['light_level'] = int(parts[3]) if parts[3].isdigit() else None
                                if len(parts) > 4:
                                    sensor_data['battery_level'] = int(parts[4]) if parts[4].isdigit() else None
                                
                                self.network_manager.update_node_data(name, sensor_data)
                        except Exception as parse_error:
                            print(f"Data parsing error for {name}: {parse_error}")
                    
                    # Trigger UI update
                    if self.update_callback:
                        try:
                            self.update_callback()
                        except Exception as callback_error:
                            print(f"Update callback error: {callback_error}")

                # Start notifications
                print(f"🔔 Starting notifications for {name} on {target_char}")
                await client.start_notify(target_char, notification_handler)
                self.connected_devices[address] = {
                    'client': client,
                    'name': name,
                    'connected_time': datetime.now(),
                    'characteristic': target_char
                }
                print(f"✅ Notifications enabled for {name}")
                
        except Exception as e:
            print(f"❌ Error connecting to {name}: {e}")
            # Show user-friendly error message
            if "characteristics" in str(e).lower():
                print(f"💡 Tip: ESP32 {name} may not have the expected BLE characteristics")
                print(f"   Make sure your ESP32 code includes BLE notifications on UUID: {CHARACTERISTIC_UUID}")
            try:
                if client.is_connected:
                    await client.disconnect()
            except:
                pass

    async def continuous_scan_and_connect(self):
        """Continuously scan for ESP32 devices and connect to them"""
        print("🔍 Starting continuous BLE scan for ESP32 devices...")
        self.is_scanning = True
        
        while self.is_scanning:
            try:
                # Scan for devices
                devices = await BleakScanner.discover(timeout=5.0)
                
                # Look for ESP32 devices
                esp_devices_found = 0
                for device in devices:
                    if device.name and device.name.startswith("ESP"):
                        esp_devices_found += 1
                        await self.connect_and_listen(device.address, device.name)
                
                if esp_devices_found > 0:
                    print(f"📡 Found {esp_devices_found} ESP32 devices, connected devices: {len(self.connected_devices)}")
                
                # Check connection status of existing devices
                disconnected_devices = []
                for address, device_info in self.connected_devices.items():
                    try:
                        if not device_info['client'].is_connected:
                            print(f"⚠️ Lost connection to {device_info['name']}")
                            disconnected_devices.append(address)
                    except Exception as e:
                        print(f"Error checking connection for {device_info['name']}: {e}")
                        disconnected_devices.append(address)
                
                # Remove disconnected devices
                for address in disconnected_devices:
                    del self.connected_devices[address]
                
                # Wait before next scan
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Error during scan: {e}")
                await asyncio.sleep(5)  # Wait longer on error
        
    def get_connected_devices_info(self):
        """Get information about currently connected devices"""
        devices_info = []
        for address, device_info in self.connected_devices.items():
            try:
                is_connected = device_info['client'].is_connected
                devices_info.append({
                    'name': device_info['name'],
                    'address': address,
                    'is_connected': is_connected,
                    'connected_time': device_info['connected_time'],
                    'characteristic': device_info.get('characteristic', 'Unknown')
                })
            except Exception as e:
                print(f"Error getting device info for {device_info['name']}: {e}")
        return devices_info
    
    async def start_scanning(self):
        """Start the continuous scanning process"""
        if not self.is_scanning:
            self.scan_task = asyncio.create_task(self.continuous_scan_and_connect())
            return True
        return False
    
    async def stop_scanning(self):
        """Stop scanning and disconnect all devices"""
        print("🛑 Stopping BLE scanning...")
        self.is_scanning = False
        
        if self.scan_task:
            self.scan_task.cancel()
            try:
                await self.scan_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all devices
        for address, device_info in self.connected_devices.items():
            try:
                if device_info['client'].is_connected:
                    await device_info['client'].disconnect()
                    print(f"✅ Disconnected from {device_info['name']}")
            except Exception as e:
                print(f"Error disconnecting from {device_info['name']}: {e}")
        
        self.connected_devices.clear()
    
    def get_connected_devices_info(self):
        """Get information about currently connected devices"""
        devices_info = []
        for address, device_info in self.connected_devices.items():
            devices_info.append({
                'name': device_info['name'],
                'address': address,
                'connected_time': device_info['connected_time'],
                'is_connected': device_info['client'].is_connected if device_info['client'] else False
            })
        return devices_info
    
    # Legacy methods for compatibility
    async def scan_and_connect(self):
        """Legacy method - now starts continuous scanning"""
        return await self.start_scanning()
    
    async def setup_characteristics(self):
        """Legacy method - characteristics are set up automatically in connect_and_listen"""
        return True
    
    async def disconnect(self):
        """Legacy method - now stops scanning and disconnects all"""
        await self.stop_scanning()

class RaspberryPiServerManager:
    """Manager for communicating with Raspberry Pi server"""
    def __init__(self, server_ip="192.168.137.174", server_port=8080):
        self.server_ip = server_ip
        self.server_port = server_port
        self.base_url = f"http://{server_ip}:{server_port}"
        self.is_connected = False
        self.last_pi_data = {}
        
    def test_connection(self):
        """Test connection to Raspberry Pi server"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            self.is_connected = True
            return True
        except Exception as e:
            print(f"❌ Cannot connect to Pi server at {self.base_url}: {e}")
            self.is_connected = False
            return False
            
    def get_pi_sensor_data(self):
        """Get sensor data from Raspberry Pi"""
        try:
            response = requests.post(f"{self.base_url}/update-from-esp", 
                                   data="REQUEST_DATA", 
                                   timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.last_pi_data = {
                    'temperature': data.get('temp', 0),
                    'humidity': data.get('humi', 0),
                    'light': data.get('light', 0),
                    'gas': data.get('gas', 0),
                    'timestamp': datetime.now()
                }
                return self.last_pi_data
        except Exception as e:
            print(f"❌ Error getting Pi data: {e}")
        return None

class BLEDataCollectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Pi Gateway + ESP32 Network Monitor - UET VNU Dashboard")
        
        # Set window icon if logo exists
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "logo-uet.jpg")
            if os.path.exists(logo_path):
                # For window icon, we need to convert to smaller size
                icon_image = Image.open(logo_path)
                icon_image.thumbnail((32, 32), Image.Resampling.LANCZOS)
                self.icon_photo = ImageTk.PhotoImage(icon_image)
                self.root.iconphoto(True, self.icon_photo)
        except Exception as e:
            print(f"Icon setting error: {e}")
        
        # Set full screen - cross-platform approach
        try:
            # Try Windows full screen first
            self.root.state('zoomed')
        except tk.TclError:
            try:
                # Try Linux full screen
                self.root.attributes('-zoomed', True)
            except tk.TclError:
                try:
                    # Try generic full screen
                    self.root.attributes("-fullscreen", True)
                except tk.TclError:
                    # Fallback to maximized window
                    self.root.geometry("1200x800")
                    print("⚠️ Full screen not supported, using large window")
        
        # Bind Escape key to exit full screen
        self.root.bind('<Escape>', self.toggle_fullscreen)
        self.root.bind('<F11>', self.toggle_fullscreen)
        
        # Check Linux-specific requirements
        self.check_system_requirements()
        
        # Initialize components
        self.network_manager = NetworkManager()
        self.data_collector = DataCollector(self.network_manager)
        self.ble_manager = BLEManager(self.data_collector, self.update_display, self.network_manager)
        self.pi_server_manager = RaspberryPiServerManager()  # Add Pi server communication
        self.ble_thread = None
        self.is_connected = False
        
        # Initialize chart data
        self.temperature_data = []
        self.humidity_data = []
        self.light_data = []
        
        # Add gateway node initially (will auto-discover other nodes from ESP32 data)
        self.setup_initial_network()
        
        # Selected node for individual view
        self.selected_node = "gateway"
        
        self.setup_full_screen_ui()
        self.update_display()
        
        # Start periodic network topology updates
        self.start_network_updates()
        
    def setup_initial_network(self):
        """Setup initial network with gateway node"""
        # Gateway node at center
        gateway_x = SIMULATION_AREA[0] // 2
        gateway_y = SIMULATION_AREA[1] // 2
        self.network_manager.add_real_node("gateway", gateway_x, gateway_y, "Pi_Gateway", True)
        
    def start_network_updates(self):
        """Start periodic network topology updates"""
        def update_loop():
            while True:
                if self.network_manager.nodes:
                    self.network_manager.update_network_topology()
                    self.network_manager.network_uptime += UPDATE_INTERVAL
                time.sleep(UPDATE_INTERVAL)
                
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
            
    def check_system_requirements(self):
        """Check if system meets requirements for Linux BLE"""
        perm_ok, perm_msg = check_bluetooth_permissions()
        if not perm_ok:
            messagebox.showwarning("Bluetooth Permissions", 
                                 f"Bluetooth permission issue:\n{perm_msg}")
        
        disp_ok, disp_msg = setup_linux_display()
        if not disp_ok:
            messagebox.showerror("Display Error", disp_msg)
        
    def setup_full_screen_ui(self):
        """Setup comprehensive full-screen dashboard"""
        # Main container with padding
        main_container = ttk.Frame(self.root, padding="5")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Top row - Control and status
        top_frame = ttk.Frame(main_container)
        top_frame.pack(fill=tk.X, pady=(0,5))
        
        # BLE Connection controls
        ble_frame = ttk.LabelFrame(top_frame, text="🔗 Multi-Device ESP32 Scanner", padding="5")
        ble_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        
        connection_row = ttk.Frame(ble_frame)
        connection_row.pack(fill=tk.X)
        
        ttk.Label(connection_row, text=f"Auto-discover ESP32 devices with characteristic: {CHARACTERISTIC_UUID[:8]}...").pack(side=tk.LEFT)
        
        self.connect_btn = ttk.Button(connection_row, text="Start Scanning", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.RIGHT, padx=5)
        
        self.status_label = ttk.Label(connection_row, text="Ready to scan", foreground="orange")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        control_row = ttk.Frame(ble_frame)
        control_row.pack(fill=tk.X, pady=(5,0))
        
        self.collect_btn = ttk.Button(control_row, text="Start Collection", command=self.toggle_collection, state="disabled")
        self.collect_btn.pack(side=tk.LEFT, padx=(0,5))
        
        ttk.Button(control_row, text="Clear Data", command=self.clear_data).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(control_row, text="System Info", command=self.show_system_info).pack(side=tk.LEFT, padx=(0,5))
        
        # Network controls
        network_ctrl_frame = ttk.LabelFrame(top_frame, text="🌐 Pi Gateway Network Control", padding="5")
        network_ctrl_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5,0))
        
        # Logo frame - top right corner of network controls
        logo_frame = ttk.Frame(network_ctrl_frame)
        logo_frame.pack(side=tk.RIGHT, padx=(10,0))
        
        # Load and display UET logo
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "logo-uet.jpg")
            if os.path.exists(logo_path):
                # Load and resize logo
                logo_image = Image.open(logo_path)
                # Resize logo to be bigger (max 100x100 pixels for this layout)
                logo_image.thumbnail((100, 100), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_image)
                
                # Create logo label
                logo_label = ttk.Label(logo_frame, image=self.logo_photo)
                logo_label.pack()
                
                # Add university name below logo
                uni_label = ttk.Label(logo_frame, text="UET - VNU", 
                                    font=('Arial', 9, 'bold'), foreground='#1f4e79')
                uni_label.pack()
            else:
                # Fallback text if logo not found
                ttk.Label(logo_frame, text="🎓 UET\nVNU", 
                         font=('Arial', 12, 'bold'), foreground='#1f4e79', justify='center').pack()
        except Exception as e:
            print(f"Logo loading error: {e}")
            # Fallback text if logo loading fails
            ttk.Label(logo_frame, text="🎓 UET\nVNU", 
                     font=('Arial', 12, 'bold'), foreground="#1f2d79", justify='center').pack()
        
        net_row1 = ttk.Frame(network_ctrl_frame)
        net_row1.pack(fill=tk.X)
        
        ttk.Button(net_row1, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(net_row1, text="Export JSON", command=self.export_json).pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(net_row1, text="Show Plot", command=self.show_plot).pack(side=tk.LEFT, padx=(0,5))
        
        net_row2 = ttk.Frame(network_ctrl_frame)
        net_row2.pack(fill=tk.X, pady=(5,0))
        
        ttk.Label(net_row2, text="Select Node:").pack(side=tk.LEFT, padx=(0,5))
        self.node_var = tk.StringVar(value="real_device")
        self.node_combo = ttk.Combobox(net_row2, textvariable=self.node_var, state="readonly", width=15)
        self.node_combo.pack(side=tk.LEFT, padx=(0,5))
        self.node_combo.bind('<<ComboboxSelected>>', self.on_node_selected)
        
        # Pi Server Controls
        net_row3 = ttk.Frame(network_ctrl_frame)
        net_row3.pack(fill=tk.X, pady=(5,0))
        
        ttk.Label(net_row3, text="Pi Server:").pack(side=tk.LEFT, padx=(0,5))
        ttk.Button(net_row3, text="Connect Pi", command=self.connect_pi_server).pack(side=tk.LEFT, padx=(0,5))
        
        self.pi_status_label = ttk.Label(net_row3, text="Pi: Disconnected", foreground="red")
        self.pi_status_label.pack(side=tk.RIGHT)
        
        # Middle row - Main content area
        middle_frame = ttk.Frame(main_container)
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=(0,5))
        
        # Left column - Network visualization
        left_column = ttk.Frame(middle_frame)
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))
        
        # Network topology visualization
        network_viz_frame = ttk.LabelFrame(left_column, text="🗺️ Pi Gateway + ESP32 Network Topology", padding="5")
        network_viz_frame.pack(fill=tk.BOTH, expand=True, pady=(0,5))
        
        # Canvas for network visualization
        self.canvas = tk.Canvas(network_viz_frame, bg='white', height=350)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bind click events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        
        # Draw legend
        self.draw_legend()
        
        # Network information
        network_info_frame = ttk.LabelFrame(left_column, text="📊 Network Information", padding="5")
        network_info_frame.pack(fill=tk.BOTH, expand=True)
        
        self.network_info_text = tk.Text(network_info_frame, height=8, font=('Courier', 9))
        net_info_scroll = ttk.Scrollbar(network_info_frame, orient="vertical", command=self.network_info_text.yview)
        self.network_info_text.configure(yscrollcommand=net_info_scroll.set)
        
        self.network_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        net_info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Middle column - Individual node data
        middle_column = ttk.Frame(middle_frame)
        middle_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,5))
        
        # Selected node info
        node_info_frame = ttk.LabelFrame(middle_column, text="📋 Selected Node Details", padding="5")
        node_info_frame.pack(fill=tk.BOTH, expand=True, pady=(0,5))
        
        self.node_info_text = tk.Text(node_info_frame, height=8, font=('Courier', 9))
        node_info_scroll = ttk.Scrollbar(node_info_frame, orient="vertical", command=self.node_info_text.yview)
        self.node_info_text.configure(yscrollcommand=node_info_scroll.set)
        
        self.node_info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        node_info_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Node sensor data
        node_data_frame = ttk.LabelFrame(middle_column, text="🔢 Node Sensor Data", padding="5")
        node_data_frame.pack(fill=tk.BOTH, expand=True)
        
        self.node_data_text = tk.Text(node_data_frame, height=8, font=('Courier', 9))
        node_data_scroll = ttk.Scrollbar(node_data_frame, orient="vertical", command=self.node_data_text.yview)
        self.node_data_text.configure(yscrollcommand=node_data_scroll.set)
        
        self.node_data_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        node_data_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right column - Statistics and data
        right_column = ttk.Frame(middle_frame)
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Network statistics
        stats_frame = ttk.LabelFrame(right_column, text="📈 Network Statistics", padding="5")
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=(0,5))
        
        self.network_stats_text = tk.Text(stats_frame, height=8, font=('Courier', 9))
        net_stats_scroll = ttk.Scrollbar(stats_frame, orient="vertical", command=self.network_stats_text.yview)
        self.network_stats_text.configure(yscrollcommand=net_stats_scroll.set)
        
        self.network_stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        net_stats_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Recent data and events
        recent_frame = ttk.LabelFrame(right_column, text="📝 Recent Data & Events", padding="5")
        recent_frame.pack(fill=tk.BOTH, expand=True)
        
        self.data_text = tk.Text(recent_frame, height=8, font=('Courier', 9))
        data_scrollbar = ttk.Scrollbar(recent_frame, orient="vertical", command=self.data_text.yview)
        self.data_text.configure(yscrollcommand=data_scrollbar.set)
        
        self.data_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        data_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bottom row - Summary statistics
        bottom_frame = ttk.Frame(main_container)
        bottom_frame.pack(fill=tk.X)
        
        # Quick stats labels
        stats_row = ttk.Frame(bottom_frame)
        stats_row.pack(fill=tk.X, pady=5)
        
        self.sensor_count_label = ttk.Label(stats_row, text="📊 Sensor readings: 0", font=('Arial', 10, 'bold'))
        self.sensor_count_label.pack(side=tk.LEFT, padx=(0,20))
        
        self.node_count_label = ttk.Label(stats_row, text="🔗 Active nodes: 0", font=('Arial', 10, 'bold'))
        self.node_count_label.pack(side=tk.LEFT, padx=(0,20))
        
        self.collection_time_label = ttk.Label(stats_row, text="⏱️ Collection time: 00:00:00", font=('Arial', 10, 'bold'))
        self.collection_time_label.pack(side=tk.LEFT, padx=(0,20))
        
        self.network_status_label = ttk.Label(stats_row, text="🌐 Network: Running", foreground="green", font=('Arial', 10, 'bold'))
        self.network_status_label.pack(side=tk.RIGHT)
        
        # UET Footer
        footer_frame = ttk.Frame(bottom_frame)
        footer_frame.pack(fill=tk.X, pady=(5,0))
        
        footer_label = ttk.Label(footer_frame, text="© 2025 University of Engineering and Technology - Vietnam National University", 
                               font=('Arial', 8), foreground='gray')
        footer_label.pack()
        
        # Initialize node list
        self.refresh_node_list()
        
    def toggle_fullscreen(self, event=None):
        """Toggle full screen mode"""
        try:
            current_state = self.root.attributes("-fullscreen")
            self.root.attributes("-fullscreen", not current_state)
        except tk.TclError:
            try:
                # Try alternative method
                if self.root.state() == 'zoomed':
                    self.root.state('normal')
                else:
                    self.root.state('zoomed')
            except tk.TclError:
                print("⚠️ Full screen toggle not supported on this system")
        
    def draw_legend(self):
        """Draw legend for the network visualization"""
        legend_x = 10
        legend_y = 10
        
        # Pi Gateway
        self.canvas.create_oval(legend_x, legend_y, legend_x+15, legend_y+15, 
                               fill='green', outline='black', width=2)
        self.canvas.create_text(legend_x+25, legend_y+7, text="Pi Gateway", anchor='w', font=('Arial', 8))
        
        # Real ESP32 device
        self.canvas.create_oval(legend_x, legend_y+20, legend_x+15, legend_y+35, 
                               fill='red', outline='black', width=2)
        self.canvas.create_text(legend_x+25, legend_y+27, text="Real ESP32", anchor='w', font=('Arial', 8))
        
        # Simulated ESP32 node
        self.canvas.create_oval(legend_x, legend_y+40, legend_x+15, legend_y+55, 
                               fill='lightblue', outline='black')
        self.canvas.create_text(legend_x+25, legend_y+47, text="Sim ESP32", anchor='w', font=('Arial', 8))
        
        # Inactive node
        self.canvas.create_oval(legend_x, legend_y+60, legend_x+15, legend_y+75, 
                               fill='gray', outline='black')
        self.canvas.create_text(legend_x+25, legend_y+67, text="Inactive", anchor='w', font=('Arial', 8))
        
        # Connection
        self.canvas.create_line(legend_x, legend_y+80, legend_x+15, legend_y+88, 
                               fill='green', width=2)
        self.canvas.create_text(legend_x+25, legend_y+84, text="Connection", anchor='w', font=('Arial', 8))
        
    def update_network_visualization(self):
        """Update the network visualization in the main window"""
        self.canvas.delete("network")  # Clear previous network drawings
        
        # Get canvas dimensions
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return  # Canvas not ready yet
        
        # Scale factor for fitting network in canvas
        scale_x = (canvas_width - 100) / SIMULATION_AREA[0]
        scale_y = (canvas_height - 100) / SIMULATION_AREA[1]
        scale = min(scale_x, scale_y)
        
        offset_x = 50
        offset_y = 50
        
        # Draw transmission ranges
        for node in self.network_manager.nodes.values():
            if node.is_active:
                x = node.x * scale + offset_x
                y = node.y * scale + offset_y
                range_radius = TRANSMISSION_RANGE * scale
                
                self.canvas.create_oval(
                    x - range_radius, y - range_radius,
                    x + range_radius, y + range_radius,
                    outline='lightblue', width=1, dash=(5,5), tags="network"
                )
        
        # Draw routing paths and connections
        routing_info = self.network_manager.get_routing_info()
        recent_paths = self.network_manager.get_recent_data_paths(5)
        
        # Highlight recent data paths first
        for path_record in recent_paths:
            path = path_record['path']
            for i in range(len(path) - 1):
                if path[i] in self.network_manager.nodes and path[i+1] in self.network_manager.nodes:
                    node1 = self.network_manager.nodes[path[i]]
                    node2 = self.network_manager.nodes[path[i+1]]
                    
                    x1 = node1.x * scale + offset_x
                    y1 = node1.y * scale + offset_y
                    x2 = node2.x * scale + offset_x
                    y2 = node2.y * scale + offset_y
                    
                    # Thick orange line for recent data paths
                    self.canvas.create_line(
                        x1, y1, x2, y2,
                        fill='orange', width=5, tags="network"
                    )
        
        # Draw regular connections
        for node in self.network_manager.nodes.values():
            if node.is_active:
                x1 = node.x * scale + offset_x
                y1 = node.y * scale + offset_y
                
                for neighbor_id in node.neighbors:
                    neighbor = self.network_manager.nodes.get(neighbor_id)
                    if neighbor and neighbor.is_active:
                        x2 = neighbor.x * scale + offset_x
                        y2 = neighbor.y * scale + offset_y
                        
                        # Check if this is a routing path
                        is_routing_path = False
                        if node.node_id in routing_info:
                            route = routing_info[node.node_id]
                            if route['next_hop'] == neighbor_id:
                                is_routing_path = True
                        
                        line_color = 'green' if is_routing_path else 'gray'
                        line_width = 3 if is_routing_path else 1
                        
                        self.canvas.create_line(
                            x1, y1, x2, y2,
                            fill=line_color, width=line_width, tags="network"
                        )
        
        # Draw nodes with real data
        for node in self.network_manager.nodes.values():
            x = node.x * scale + offset_x
            y = node.y * scale + offset_y
            
            # Determine node color and size
            if not node.is_active:
                color = 'gray'
                size = 12
            elif node.node_type == "Pi_Gateway":
                color = 'darkgreen'
                size = 20
            else:
                color = 'blue'
                size = 15
            
            outline_width = 3 if node.node_type == "Pi_Gateway" else 2
            
            # Highlight selected node
            if node.node_id == self.selected_node:
                outline_color = 'yellow'
                outline_width = 4
            else:
                outline_color = 'black'
            
            # Node circle
            self.canvas.create_oval(
                x - size, y - size, x + size, y + size,
                fill=color, outline=outline_color, width=outline_width, tags="network"
            )
            
            # Node ID
            self.canvas.create_text(
                x, y - size - 20, text=node.node_id,
                font=('Arial', 8, 'bold'), tags="network"
            )
            
            # Node data information
            if node.is_active and node.sensor_data:
                latest_data = node.sensor_data[-1] if node.sensor_data else {}
                if node.node_type == "Pi_Gateway":
                    info_text = f"Gateway\nPkts:{self.network_manager.total_data_packets}"
                else:
                    temp = latest_data.get('temperature', 0)
                    humidity = latest_data.get('humidity', 0)
                    info_text = f"T:{temp:.1f}°C\nH:{humidity:.1f}%"
                    
                    # Show routing distance
                    if node.node_id in routing_info:
                        route = routing_info[node.node_id]
                        if route['distance'] != float('inf'):
                            info_text += f"\nHops:{route['distance']}"
                
                self.canvas.create_text(
                    x, y + size + 25, text=info_text,
                    font=('Arial', 7), tags="network", justify='center'
                )
                outline_color = 'yellow'
                outline_width = 4
            else:
                outline_color = 'black'
            
            # Node circle
            self.canvas.create_oval(
                x - size, y - size, x + size, y + size,
                fill=color, outline=outline_color, width=outline_width, tags="network"
            )
            
            # Node ID
            self.canvas.create_text(
                x, y - size - 15, text=node.node_id,
                font=('Arial', 7, 'bold'), tags="network"
            )
            
            # Node info
            if node.is_active:
                if node.node_type == "Pi_Gateway":
                    info_text = f"CPU:{node.cpu_usage:.0f}%" if hasattr(node, 'cpu_usage') and node.cpu_usage else "Gateway"
                else:
                    info_text = f"T:{node.temperature:.1f}°C" if node.temperature else "ESP32"
                    if node.total_readings > 0:
                        info_text += f"\nR:{node.total_readings}"
                
                self.canvas.create_text(
                    x, y + size + 15, text=info_text,
                    font=('Arial', 6), tags="network"
                )
                
    def on_canvas_click(self, event):
        """Handle canvas click to select node"""
        # Get canvas dimensions and scale
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        scale_x = (canvas_width - 100) / SIMULATION_AREA[0]
        scale_y = (canvas_height - 100) / SIMULATION_AREA[1]
        scale = min(scale_x, scale_y)
        
        # Convert click coordinates to simulation coordinates
        sim_x = (event.x - 50) / scale
        sim_y = (event.y - 50) / scale
        
        # Check if click is near existing node (for selection)
        for node in self.network_manager.nodes.values():
            distance = math.sqrt((node.x - sim_x)**2 + (node.y - sim_y)**2)
            if distance < 30:  # 30 unit tolerance
                self.selected_node = node.node_id
                self.node_var.set(node.node_id)
                self.update_node_display(node.node_id)
                return
            
    def on_canvas_right_click(self, event):
        """Handle right click to toggle node (except Pi Gateway)"""
        # Get canvas dimensions and scale
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        scale_x = (canvas_width - 100) / SIMULATION_AREA[0]
        scale_y = (canvas_height - 100) / SIMULATION_AREA[1]
        scale = min(scale_x, scale_y)
        
        # Convert click coordinates to simulation coordinates
        sim_x = (event.x - 50) / scale
        sim_y = (event.y - 50) / scale
        
        # Find closest node
        closest_node = None
        min_distance = float('inf')
        
        for node in self.network_manager.nodes.values():
            distance = math.sqrt((node.x - sim_x)**2 + (node.y - sim_y)**2)
            if distance < min_distance and distance < 30:  # 30 unit tolerance
                min_distance = distance
                closest_node = node
                
        if closest_node and closest_node.node_id != "pi_gateway":
            self.network_manager.toggle_node(closest_node.node_id)
        
    def refresh_node_list(self):
        """Refresh the list of available nodes"""
        nodes = list(self.network_manager.nodes.keys())
        self.node_combo['values'] = nodes
        if nodes and not self.node_var.get():
            self.node_var.set(nodes[0])
            self.on_node_selected()
            
    def on_node_selected(self, event=None):
        """Handle node selection"""
        selected_node = self.node_var.get()
        if selected_node:
            self.selected_node = selected_node
            self.update_node_display(selected_node)
            
    def update_node_display(self, node_id):
        """Update the display for a specific node"""
        node_data = self.data_collector.get_node_data(node_id)
        if not node_data:
            return
            
        # Update node info
        stats = node_data['statistics']
        node_type = stats['node_type']
        status = "Active" if stats['is_active'] else "Inactive"
        device_marker = " (Real Device)" if stats['is_real_device'] else ""
        
        info_text = f"""NODE: {node_id}{device_marker}
{'='*40}
Type: {node_type}
Status: {status}
Total Readings: {stats['total_readings']}
Uptime: {stats['uptime_seconds']:.1f}s
Battery: {stats['battery_level']}%
Neighbors: {stats['neighbors_count']}
Last Update: {stats['last_update'].strftime('%H:%M:%S')}
"""
        
        self.node_info_text.delete(1.0, tk.END)
        self.node_info_text.insert(1.0, info_text)
        
        # Update node data
        data_text = f"SENSOR DATA - {node_id}\n{'='*35}\n\n"
        
        recent_readings = node_data['recent_readings'][-5:] if node_data['recent_readings'] else []
        
        for i, reading in enumerate(recent_readings):
            data_text += f"Reading {len(recent_readings)-i}:\n"
            if reading.get('temperature') is not None:
                data_text += f"  Temp: {reading['temperature']:.1f}°C\n"
            if reading.get('humidity') is not None:
                data_text += f"  Hum:  {reading['humidity']:.1f}%\n"
            if reading.get('cpu_usage') is not None:
                data_text += f"  CPU:  {reading['cpu_usage']:.1f}%\n"
            if reading.get('memory_usage') is not None:
                data_text += f"  Mem:  {reading['memory_usage']:.1f}%\n"
            if reading.get('sensor_value') is not None:
                data_text += f"  Sens: {reading['sensor_value']}\n"
            if reading.get('light_level') is not None:
                data_text += f"  Light: {reading['light_level']}\n"
            data_text += f"  Batt: {reading['battery_level']}%\n\n"
            
        if node_data['recent_events']:
            data_text += "\nBUTTON EVENTS:\n"
            data_text += "-" * 20 + "\n"
            for event in node_data['recent_events'][-3:]:
                time_str = event['timestamp'].strftime('%H:%M:%S')
                data_text += f"{time_str}: {event['state']}\n"
                
        self.node_data_text.delete(1.0, tk.END)
        self.node_data_text.insert(1.0, data_text)
        
    def show_system_info(self):
        try:
            import platform
            info = f"""Linux System Information:
            
OS: {platform.system()} {platform.release()}
Python: {platform.python_version()}
Architecture: {platform.machine()}

Bluetooth Status:
{subprocess.check_output(['systemctl', 'is-active', 'bluetooth'], text=True).strip()}

User Groups:
{subprocess.check_output(['groups'], text=True).strip()}

Bleak Version: {bleak.__version__}

Network Configuration:
Pi Gateway + 4 ESP32 Nodes
Transmission Range: {TRANSMISSION_RANGE}m
Update Interval: {UPDATE_INTERVAL}s
"""
            messagebox.showinfo("System Information", info)
        except Exception as e:
            messagebox.showerror("System Info Error", f"Cannot get system info: {e}")
        
    async def ble_worker_async(self):
        """Updated BLE worker for continuous multi-device scanning"""
        try:
            print("🔄 Starting multi-device BLE scanning...")
            
            # Start continuous scanning
            if await self.ble_manager.start_scanning():
                self.is_connected = True
                self.root.after(0, self.update_connection_status)
                print("🔗 Multi-device BLE scanning started successfully")
                
                # Keep scanning until user disconnects
                while self.is_connected:
                    try:
                        await asyncio.sleep(2)
                        
                        # Check if we have any connected devices
                        connected_devices = self.ble_manager.get_connected_devices_info()
                        if not connected_devices:
                            print("⚠️ No ESP32 devices connected")
                        else:
                            # Periodically log connected devices status
                            if not hasattr(self, '_last_device_log') or (datetime.now() - self._last_device_log).seconds >= 30:
                                print(f"� Connected to {len(connected_devices)} ESP32 devices:")
                                for device in connected_devices:
                                    status = "✅" if device['is_connected'] else "❌"
                                    connection_time = (datetime.now() - device['connected_time']).seconds
                                    print(f"  {status} {device['name']} ({device['address']}) - {connection_time}s")
                                self._last_device_log = datetime.now()
                        
                    except asyncio.CancelledError:
                        print("🔌 BLE scanning cancelled by user")
                        break
                    except Exception as e:
                        print(f"Connection monitoring error: {e}")
                        await asyncio.sleep(5)  # Wait longer on errors
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "Unable to start BLE scanning"))
                
        except Exception as e:
            print(f"❌ BLE Error: {e}")
            # Use the new error handler
            self.root.after(0, lambda: self.handle_ble_error(str(e)))
        finally:
            # Stop scanning and disconnect all devices
            try:
                if self.ble_manager:
                    print("🔌 Stopping BLE scanning and disconnecting devices...")
                    await self.ble_manager.stop_scanning()
            except Exception as disconnect_error:
                print(f"Disconnect error: {disconnect_error}")
            
            self.is_connected = False
            self.root.after(0, self.update_connection_status)
            print("❌ BLE scanning stopped")
            
    def ble_worker(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.ble_worker_async())
        finally:
            loop.close()
            
    def toggle_connection(self):
        if not self.is_connected:
            print("🔄 Initiating multi-device BLE scanning...")
            self.connect_btn.config(text="Starting Scan...", state="disabled")
            
            # Check BLE permissions first
            permissions_ok, permission_msg = check_bluetooth_permissions()
            if not permissions_ok:
                messagebox.showerror("BLE Permission Error", 
                    f"Bluetooth permissions required:\n\n{permission_msg}\n\n"
                    "Please fix permissions and restart the application.")
                self.connect_btn.config(text="Start Scanning", state="normal")
                return
                
            self.ble_thread = threading.Thread(target=self.ble_worker, daemon=True)
            self.ble_thread.start()
        else:
            print("🔌 Stopping BLE scanning...")
            self.is_connected = False
            self.connect_btn.config(text="Stopping...", state="disabled")
    
    def handle_ble_error(self, error_msg):
        """Handle BLE errors and show user-friendly messages"""
        print(f"🚨 BLE Error: {error_msg}")
        
        # Reset connection state
        self.is_connected = False
        self.connect_btn.config(text="Start Scanning", state="normal")
        self.status_label.config(text="Error", foreground="red")
        
        # Show user-friendly error message
        if "characteristics" in error_msg.lower():
            messagebox.showerror("ESP32 Connection Error", 
                f"Failed to setup ESP32 characteristics.\n\n"
                f"Common solutions:\n"
                f"• Make sure ESP32 is broadcasting with name starting with 'ESP'\n"
                f"• Verify ESP32 BLE code includes characteristic: {CHARACTERISTIC_UUID}\n"
                f"• Check ESP32 is properly programmed and running\n"
                f"• Try restarting ESP32 device\n\n"
                f"Technical details: {error_msg}")
        elif "permission" in error_msg.lower():
            messagebox.showerror("BLE Permission Error",
                f"Bluetooth permission denied.\n\n"
                f"Solutions:\n"
                f"• Run as administrator (Windows)\n"
                f"• Add user to bluetooth group (Linux)\n"
                f"• Check Bluetooth adapter is enabled\n\n"
                f"Details: {error_msg}")
        else:
            messagebox.showerror("BLE Connection Error", 
                f"Bluetooth connection failed.\n\n"
                f"Please check:\n"
                f"• Bluetooth adapter is working\n"
                f"• ESP32 device is powered on\n"
                f"• Device is in range\n\n"
                f"Error: {error_msg}")
            
    def toggle_collection(self):
        self.data_collector.is_collecting = not self.data_collector.is_collecting
        if self.data_collector.is_collecting:
            self.data_collector.collection_start_time = datetime.now()
            self.collect_btn.config(text="Stop Collection")
        else:
            self.collect_btn.config(text="Start Collection")
            
    def clear_data(self):
        self.data_collector.sensor_data.clear()
        self.data_collector.node_data.clear()
        self.data_collector.timestamps.clear()
        self.data_collector.network_events.clear()
        self.data_collector.collection_start_time = None
        self.data_text.delete(1.0, tk.END)
        self.update_display()
        
    def update_connection_status(self):
        if self.is_connected:
            # Get connected devices info
            connected_devices = self.ble_manager.get_connected_devices_info()
            device_count = len(connected_devices)
            
            if device_count > 0:
                self.status_label.config(text=f"Scanning ({device_count} devices)", foreground="green")
                print(f"✅ BLE scanning active with {device_count} ESP32 devices connected")
            else:
                self.status_label.config(text="Scanning (no devices)", foreground="orange")
                print("🔍 BLE scanning active but no ESP32 devices found yet")
            
            self.connect_btn.config(text="Stop Scan", state="normal")
            self.collect_btn.config(state="normal")
        else:
            self.status_label.config(text="Disconnected", foreground="red")
            self.connect_btn.config(text="Start Scan", state="normal")
            self.collect_btn.config(state="disabled")
            if hasattr(self, 'ble_thread') and self.ble_thread:
                print("❌ BLE scanning stopped")
            
    def update_display(self):
        """Update the full-screen display with current data"""
        try:
            # Update BLE statistics
            sensor_count = len(self.data_collector.sensor_data)
            node_count = len(self.data_collector.node_data)
            
            self.sensor_count_label.config(text=f"📊 Sensor readings: {sensor_count}")
            
            # Safely count active nodes
            try:
                active_count = len([n for n in self.network_manager.nodes.values() if n.is_active])
                self.node_count_label.config(text=f"🔗 Active nodes: {active_count}")
            except Exception as node_error:
                print(f"Node count error: {node_error}")
                self.node_count_label.config(text="🔗 Active nodes: N/A")
            
            # Update collection time
            if self.data_collector.collection_start_time:
                try:
                    elapsed = datetime.now() - self.data_collector.collection_start_time
                    hours = int(elapsed.total_seconds() // 3600)
                    minutes = int((elapsed.total_seconds() % 3600) // 60)
                    seconds = int(elapsed.total_seconds() % 60)
                    self.collection_time_label.config(text=f"⏱️ Collection time: {hours:02d}:{minutes:02d}:{seconds:02d}")
                except Exception as time_error:
                    print(f"Time calculation error: {time_error}")
            
            # Update network status
            try:
                network_status = "Running" if self.network_manager.is_running else "Stopped"
                color = "green" if self.network_manager.is_running else "red"
                self.network_status_label.config(text=f"🌐 Network: {network_status}", foreground=color)
            except Exception as status_error:
                print(f"Network status error: {status_error}")
            
            # Update network visualization
            try:
                self.update_network_visualization()
            except Exception as viz_error:
                print(f"Network visualization error: {viz_error}")
            
            # Update network information
            try:
                self.update_network_info_display()
            except Exception as info_error:
                print(f"Network info error: {info_error}")
            
            # Update network statistics
            try:
                self.update_network_stats_display()
            except Exception as stats_error:
                print(f"Network stats error: {stats_error}")
            
            # Update recent data display
            try:
                self.update_recent_data_display()
            except Exception as data_error:
                print(f"Recent data error: {data_error}")
            
            # Update node list if changed
            try:
                current_nodes = list(self.network_manager.nodes.keys())
                if current_nodes != list(self.node_combo['values']):
                    self.refresh_node_list()
            except Exception as combo_error:
                print(f"Node combo error: {combo_error}")
                
            # Update current node display if one is selected
            try:
                if self.selected_node and self.selected_node in self.network_manager.nodes:
                    self.update_node_display(self.selected_node)
            except Exception as node_display_error:
                print(f"Node display error: {node_display_error}")
            
            # Update charts with Pi server data if available
            try:
                if self.pi_server_manager.is_connected and self.pi_server_manager.last_pi_data:
                    pi_data = self.pi_server_manager.last_pi_data
                    # Add Pi data to visualization
                    node_label = "Pi_Server"
                    if node_label not in self.network_manager.nodes:
                        # Add Pi server as a node in the network visualization
                        pi_x = SIMULATION_AREA[0] - 100  # Position on the right
                        pi_y = 100
                        self.network_manager.add_real_node(node_label, pi_x, pi_y, "Pi_Server", True)
                    
                    # Update node data
                    if node_label in self.network_manager.nodes:
                        node = self.network_manager.nodes[node_label]
                        node.add_data({
                            'temperature': pi_data['temperature'],
                            'humidity': pi_data['humidity'],
                            'light': pi_data['light'],
                            'gas': pi_data['gas']
                        })
                    
                    # Update chart data
                    self.temperature_data.append(pi_data['temperature'])
                    self.humidity_data.append(pi_data['humidity'])
                    self.light_data.append(pi_data['light'])
                    
                    # Keep only last 20 points
                    if len(self.temperature_data) > 20:
                        self.temperature_data.pop(0)
                        self.humidity_data.pop(0)
                        self.light_data.pop(0)
                    
                    # Update charts if they exist
                    self.update_charts()
                        
                # Add ESP32 data to charts if available
                elif self.data_collector.sensor_data:
                    latest_sensor = self.data_collector.sensor_data[-1]
                    # Add ESP32 data to charts (assuming it's temperature)
                    self.temperature_data.append(latest_sensor)
                    self.humidity_data.append(latest_sensor * 0.8)  # Simulated humidity
                    self.light_data.append(latest_sensor * 10)     # Simulated light
                    
                    # Keep only last 20 points
                    if len(self.temperature_data) > 20:
                        self.temperature_data.pop(0)
                        self.humidity_data.pop(0)
                        self.light_data.pop(0)
                    
                    self.update_charts()
            except Exception as chart_error:
                print(f"Chart update error: {chart_error}")
            
        except Exception as e:
            print(f"Display update error: {e}")
            
        # Schedule next update
        try:
            self.root.after(1000, self.update_display)
        except Exception as schedule_error:
            print(f"Schedule error: {schedule_error}")
    
    def update_charts(self):
        """Update chart displays with current data"""
        try:
            # This is a placeholder for chart updating
            # You can implement actual chart libraries like matplotlib here
            # For now, we'll just print the latest data
            if self.temperature_data:
                latest_temp = self.temperature_data[-1]
                latest_humidity = self.humidity_data[-1] if self.humidity_data else 0
                latest_light = self.light_data[-1] if self.light_data else 0
                print(f"📊 Chart Update - Temp: {latest_temp:.1f}°C, Humidity: {latest_humidity:.1f}%, Light: {latest_light:.0f}")
        except Exception as e:
            print(f"Chart update error: {e}")
        
    def update_network_info_display(self):
        """Update network information display"""
        try:
            network_info = f"""NETWORK TOPOLOGY
{'='*30}
Architecture: Pi Gateway + ESP32 Nodes
Transmission Range: {TRANSMISSION_RANGE}m
Update Interval: {UPDATE_INTERVAL}s

NODE STATUS
{'='*20}
"""
            for node_id, node in self.network_manager.nodes.items():
                status = "🟢" if node.is_active else "🔴"
                device_type = "🖥️ Pi" if node.node_type == "Pi_Gateway" else "📡 ESP32"
                real_marker = " (Real)" if node.is_real_device else ""
                network_info += f"{status} {device_type} {node_id}{real_marker}\n"
                if node.is_active:
                    network_info += f"   Neighbors: {len(node.neighbors)}\n"
                    network_info += f"   Readings: {node.total_readings}\n"
                    network_info += f"   Battery: {node.battery_level}%\n"
                network_info += "\n"
            
            self.network_info_text.delete(1.0, tk.END)
            self.network_info_text.insert(1.0, network_info)
            
        except Exception as e:
            print(f"Network info update error: {e}")
            
    def update_network_stats_display(self):
        """Update network statistics display"""
        try:
            stats = self.network_manager.get_network_stats()
            
            network_stats = f"""NETWORK STATISTICS
{'='*25}
Total Nodes: {stats['total_nodes']}
Active Nodes: {stats['active_nodes']}
Pi Gateways: {stats['pi_nodes']}
ESP32 Nodes: {stats['esp32_nodes']}

COMMUNICATION
{'='*20}
Data Packets: {stats['total_data_packets']}
Heartbeats: {stats['total_heartbeats']}
Network Uptime: {stats['network_uptime']:.0f}s
Connected: {'Yes' if stats['is_connected'] else 'No'}

PERFORMANCE
{'='*15}
Packet Rate: {stats['total_data_packets'] / max(1, stats['network_uptime'] / 60):.1f}/min
Avg Load/Node: {stats['total_heartbeats'] / max(1, stats['active_nodes']):.1f}
"""
            
            self.network_stats_text.delete(1.0, tk.END)
            self.network_stats_text.insert(1.0, network_stats)
            
        except Exception as e:
            print(f"Network stats update error: {e}")
            
    def update_recent_data_display(self):
        """Update recent data and events display"""
        try:
            self.data_text.delete(1.0, tk.END)
            
            # Pi Server status and data
            if self.pi_server_manager.is_connected and self.pi_server_manager.last_pi_data:
                pi_data = self.pi_server_manager.last_pi_data
                self.data_text.insert(tk.END, "PI SERVER DATA\n" + "="*25 + "\n")
                self.data_text.insert(tk.END, f"🖥️ Temperature: {pi_data['temperature']}°C\n")
                self.data_text.insert(tk.END, f"🖥️ Humidity: {pi_data['humidity']}%\n")
                self.data_text.insert(tk.END, f"🖥️ Light: {pi_data['light']}\n")
                self.data_text.insert(tk.END, f"🖥️ Gas: {pi_data['gas']}\n")
                last_update = pi_data['timestamp'].strftime("%H:%M:%S")
                self.data_text.insert(tk.END, f"🖥️ Updated: {last_update}\n\n")
            
            # Recent sensor data from real device
            if self.data_collector.sensor_data:
                recent_sensor = list(zip(self.data_collector.timestamps, self.data_collector.sensor_data))[-5:]
                self.data_text.insert(tk.END, "ESP32 BLE DATA\n" + "="*25 + "\n")
                for ts, value in recent_sensor:
                    time_str = ts.strftime("%H:%M:%S")
                    self.data_text.insert(tk.END, f"{time_str}: {value}\n")
                self.data_text.insert(tk.END, "\n")
            
            # Network events summary
            active_nodes = [node for node in self.network_manager.nodes.values() if node.is_active]
            self.data_text.insert(tk.END, "NETWORK SUMMARY\n" + "="*20 + "\n")
            
            # Pi Gateway summary
            if self.network_manager.pi_gateway_node and self.network_manager.pi_gateway_node.is_active:
                pi_node = self.network_manager.pi_gateway_node
                latest = pi_node.get_latest_data()
                if latest and latest['data']:
                    data = latest['data']
                    self.data_text.insert(tk.END, f"🖥️ Pi Gateway: ")
                    if data.get('cpu_usage'):
                        self.data_text.insert(tk.END, f"CPU:{data['cpu_usage']:.1f}% ")
                    if data.get('memory_usage'):
                        self.data_text.insert(tk.END, f"Mem:{data['memory_usage']:.1f}%")
                    self.data_text.insert(tk.END, "\n")
            
            # ESP32 nodes summary
            esp32_nodes = [node for node in active_nodes if node.node_type == "ESP32"][:4]
            for node in esp32_nodes:
                latest = node.get_latest_data()
                if latest and latest['data']:
                    data = latest['data']
                    marker = "📡🔴" if node.is_real_device else "📡🔵"
                    self.data_text.insert(tk.END, f"{marker} {node.node_id}: ")
                    if data.get('temperature'):
                        self.data_text.insert(tk.END, f"T:{data['temperature']:.1f}°C ")
                    if data.get('sensor_value'):
                        self.data_text.insert(tk.END, f"S:{data['sensor_value']} ")
                    self.data_text.insert(tk.END, f"B:{data['battery_level']}%\n")
                    
            self.data_text.see(tk.END)
            
        except Exception as e:
            print(f"Recent data update error: {e}")
    def export_csv(self):
        if not self.data_collector.sensor_data and not self.data_collector.network_events:
            messagebox.showwarning("No Data", "No data to export")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save data as CSV"
        )
        
        if filename:
            try:
                base_filename = filename.replace('.csv', '')
                files = self.data_collector.export_to_csv(base_filename)
                file_list = [f for f in files if f]  # Filter out None values
                messagebox.showinfo("Export Complete", 
                                  f"ESP32 data exported to:\n" + "\n".join(file_list))
            except Exception as e:
                messagebox.showerror("Export Error", str(e))
                
    def export_json(self):
        if not self.data_collector.sensor_data and not self.data_collector.network_events:
            messagebox.showwarning("No Data", "No data to export")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save data as JSON"
        )
        if filename:
            try:
                base_filename = filename.replace('.json', '')
                json_file = self.data_collector.export_to_json(base_filename)
                messagebox.showinfo("Export Complete", f"ESP32 data exported to:\n{json_file}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))
                
    def show_plot(self):
        if not self.data_collector.node_data and not self.network_manager.nodes:
            messagebox.showwarning("No Data", "No ESP32 node data to plot")
            return
            
        try:
            # Create plots for network overview
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Pi Gateway + ESP32 Network Overview')
            
            # Temperature comparison
            temps = {}
            hums = {}
            for node_id, node in self.network_manager.nodes.items():
                if node.is_active and node.sensor_data:
                    latest = node.sensor_data[-1] if node.sensor_data else {}
                    if latest.get('temperature'):
                        temps[node_id] = latest['temperature']
                    if latest.get('humidity'):
                        hums[node_id] = latest['humidity']
            
            if temps:
                nodes = list(temps.keys())
                values = list(temps.values())
                colors = ['green' if 'pi_gateway' in n else 'red' if 'real' in n else 'lightblue' for n in nodes]
                ax1.bar(nodes, values, color=colors, alpha=0.7)
                ax1.set_title('Current Temperature by Node')
                ax1.set_ylabel('Temperature (°C)')
                ax1.tick_params(axis='x', rotation=45)
            
            if hums:
                nodes = list(hums.keys())
                values = list(hums.values())
                colors = ['green' if 'pi_gateway' in n else 'red' if 'real' in n else 'lightblue' for n in nodes]
                ax2.bar(nodes, values, color=colors, alpha=0.7)
                ax2.set_title('Current Humidity by Node')
                ax2.set_ylabel('Humidity (%)')
                ax2.tick_params(axis='x', rotation=45)
            
            # Node activity over time
            if self.data_collector.timestamps:
                time_range = [(ts - self.data_collector.timestamps[0]).total_seconds() / 60 
                             for ts in self.data_collector.timestamps]
                sensor_values = list(self.data_collector.sensor_data)
                
                # Handle both string and numeric sensor data
                numeric_values = []
                for val in sensor_values:
                    if isinstance(val, str):
                        # Try to extract first numeric value from string
                        try:
                            import re
                            numbers = re.findall(r'\d+\.?\d*', val)
                            if numbers:
                                numeric_values.append(float(numbers[1]) if len(numbers) > 1 else float(numbers[0]))
                            else:
                                numeric_values.append(0)
                        except:
                            numeric_values.append(0)
                    else:
                        numeric_values.append(float(val) if val is not None else 0)
                
                ax3.plot(time_range, numeric_values, 'b-', linewidth=1)
                ax3.set_title('Real Device Sensor Data Over Time')
                ax3.set_xlabel('Time (minutes)')
                ax3.set_ylabel('Sensor Value')
                ax3.grid(True)
            
            # Network connectivity
            stats = self.network_manager.get_network_stats()
            categories = ['Total Nodes', 'Active Nodes', 'Pi Gateways', 'ESP32 Nodes']
            values = [stats['total_nodes'], stats['active_nodes'], stats['pi_nodes'], stats['esp32_nodes']]
            colors = ['lightgray', 'lightgreen', 'green', 'lightblue']
            
            ax4.bar(categories, values, color=colors, alpha=0.7)
            ax4.set_title('Network Node Summary')
            ax4.set_ylabel('Count')
            ax4.tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            plt.show()
            
        except Exception as e:
            messagebox.showerror("Plot Error", str(e))
    
    def connect_pi_server(self):
        """Connect to Raspberry Pi server"""
        try:
            if self.pi_server_manager.test_connection():
                self.pi_status_label.config(text="Pi: Connected", foreground="green")
                print("✅ Connected to Raspberry Pi server")
                
                # Start periodic data collection from Pi
                self.start_pi_data_collection()
                
                messagebox.showinfo("Pi Server", "Successfully connected to Raspberry Pi server")
            else:
                self.pi_status_label.config(text="Pi: Failed", foreground="red")
                messagebox.showerror("Pi Server", "Failed to connect to Raspberry Pi server\nCheck if server is running on 192.168.137.174:8080")
        except Exception as e:
            self.pi_status_label.config(text="Pi: Error", foreground="red")
            messagebox.showerror("Pi Server Error", f"Error connecting to Pi server: {e}")
    
    def start_pi_data_collection(self):
        """Start periodic collection of Pi sensor data"""
        def pi_data_loop():
            while self.pi_server_manager.is_connected:
                try:
                    pi_data = self.pi_server_manager.get_pi_sensor_data()
                    if pi_data:
                        # Update Pi gateway node with real data
                        if "gateway" in self.network_manager.nodes:
                            pi_node = self.network_manager.nodes["gateway"]
                            pi_node.add_sensor_reading(
                                temperature=pi_data['temperature'],
                                humidity=pi_data['humidity'],
                                cpu_usage=pi_data['light'],  # Use light as CPU proxy
                                memory_usage=pi_data['gas']   # Use gas as memory proxy
                            )
                            print(f"📊 Pi Data: T:{pi_data['temperature']}°C H:{pi_data['humidity']}% L:{pi_data['light']} G:{pi_data['gas']}")
                except Exception as e:
                    print(f"Pi data collection error: {e}")
                
                time.sleep(5)  # Collect Pi data every 5 seconds
        
        if self.pi_server_manager.is_connected:
            pi_thread = threading.Thread(target=pi_data_loop, daemon=True)
            pi_thread.start()

def main():
    """Main function to start the Pi Gateway + ESP32 Network Dashboard"""
    import platform
    print("=" * 70)
    print("🌐 Pi Gateway + ESP32 Network Dashboard Initializing...")
    print("=" * 70)
    print("📊 Network Configuration:")
    print(f"  • 1 Pi Gateway (node_pi_gateway)")
    print(f"  • 4 ESP32 Nodes (node_esp32_1-4)")
    print(f"  • Transmission Range: {TRANSMISSION_RANGE}m")
    print(f"  • Update Interval: {UPDATE_INTERVAL}s")
    print("=" * 70)
    
    try:
        import asyncio
        if platform.system() != 'Linux':
            print("⚠️ Warning: This application is designed for Linux systems")
            print("Some system functions may not work properly")
            
        # Check Bluetooth service
        try:
            status = subprocess.check_output(['systemctl', 'is-active', 'bluetooth'], text=True).strip()
            if status == 'active':
                print("🔵 Bluetooth service is running")
            else:
                print(f"⚠️ Bluetooth service status: {status}")
                print("   Try: sudo systemctl start bluetooth")
        except:
            print("❓ Could not check Bluetooth service status")
        
        print(f"🔍 Looking for ESP32 Gateway: {DEVICE_NAME}")
        print(f"📡 Service UUID: {TEMPERATURE_SERVICE_UUID}")
        print(f"📊 Characteristic UUID: {TEMPERATURE_CHAR_UUID}")
        print("📋 Make sure your ESP32 Gateway is advertising")
        print("=" * 70)
        
        print("🖥️ Starting Tkinter GUI...")
        root = tk.Tk()
        app = BLEDataCollectorGUI(root)
        
        def on_closing():
            if app.is_connected:
                app.is_connected = False
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        print(" Pi Gateway + ESP32 Network Dashboard ready!")
        print(" Use 'Connect' button to connect to real ESP32 gateway")
        print(" Network simulation runs automatically")
        print("=" * 70)
        
        root.mainloop()
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("Please install required packages:")
        print("pip install -r requirements_linux.txt")
    except PermissionError:
        print("❌ Permission Error: Please run with appropriate BLE permissions")
        print("Try: sudo usermod -a -G bluetooth $USER")
        print("Then logout and login again")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Check Bluetooth adapter is available and enabled")

if __name__ == "__main__":
    # Check system requirements
    perm_ok, perm_msg = check_bluetooth_permissions()
    if not perm_ok:
        print(f"⚠️ Bluetooth permission issue: {perm_msg}")
        
    disp_ok, disp_msg = setup_linux_display()
    if not disp_ok:
        print(f"❌ Display setup error: {disp_msg}")
        sys.exit(1)
    
    # Start the application
    root = tk.Tk()
    app = BLEDataCollectorGUI(root)
    
    def on_closing():
        if app.is_connected:
            app.is_connected = False
        if hasattr(app, 'network_manager'):
            app.network_manager.is_running = False
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    print("🚀 Starting Real ESP32 Network Data Collector...")
    print("📡 Connect your ESP32 devices and click 'Connect' to start collecting data")
    print("🔧 Use F11 or ESC to toggle full screen mode")
    root.mainloop()
