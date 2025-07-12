#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple MongoDB connection test script
בדיקה פשוטה לחיבור MongoDB
"""

import os
import sys
from pymongo import MongoClient

def test_mongodb_connection():
    """Test MongoDB connection with SSL settings"""
    print("🔍 Testing MongoDB connection...")
    
    mongo_uri = os.getenv('MONGO_URI')
    if not mongo_uri:
        print("❌ MONGO_URI environment variable not set!")
        print("💡 Please set your MongoDB connection string:")
        print("export MONGO_URI='your_mongodb_connection_string'")
        return False
    
    try:
        print("🔄 Attempting connection with SSL settings...")
        
        # Method 1: With SSL settings
        client = MongoClient(
            mongo_uri,
            ssl=True,
            ssl_cert_reqs='CERT_NONE',
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            maxPoolSize=10,
            retryWrites=True,
            retryReads=True,
            tlsAllowInvalidCertificates=True,
            tlsAllowInvalidHostnames=True
        )
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful with SSL settings!")
        
        # Test basic operations
        db = client['test_db']
        collection = db['test_collection']
        
        # Insert test document
        result = collection.insert_one({'test': 'connection', 'timestamp': '2024'})
        print(f"✅ Insert test successful: {result.inserted_id}")
        
        # Find test document
        doc = collection.find_one({'test': 'connection'})
        if doc:
            print("✅ Find test successful")
        
        # Clean up
        collection.delete_one({'test': 'connection'})
        print("✅ Cleanup successful")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔄 Trying alternative connection method...")
        
        try:
            # Method 2: Without explicit SSL settings
            client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                maxPoolSize=10,
                retryWrites=True,
                retryReads=True
            )
            
            client.admin.command('ping')
            print("✅ MongoDB connection successful with alternative method!")
            client.close()
            return True
            
        except Exception as e2:
            print(f"❌ Alternative method also failed: {e2}")
            return False

if __name__ == "__main__":
    success = test_mongodb_connection()
    if success:
        print("\n🎉 MongoDB connection test passed!")
        sys.exit(0)
    else:
        print("\n💥 MongoDB connection test failed!")
        sys.exit(1)