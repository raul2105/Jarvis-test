#!/usr/bin/env python3
"""
Simple HTTP server for health checking.
Uses only Python standard library to avoid installation issues.
"""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import threading
import time

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "service": "jarvis-test"
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "message": "Jarvis Test Service is running",
                "endpoints": {
                    "/health": "Health check endpoint",
                    "/": "This endpoint"
                }
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        # Override to reduce log noise
        pass

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, HealthHandler)
    print(f"Serving on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()