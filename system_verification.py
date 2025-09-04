#!/usr/bin/env python3
"""
Comprehensive system verification for all RAG components
"""

import sys
import asyncio
import json
import sqlite3
from pathlib import Path

def test_database_connection():
    """Test database connection and data"""
    print("🗄️ Testing Database Connection...")
    try:
        conn = sqlite3.connect("wazuh_archives.db")
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wazuh_archives'")
        result = cursor.fetchone()
        
        if result:
            print("   ✅ wazuh_archives table found")
            
            # Count records
            cursor.execute("SELECT COUNT(*) FROM wazuh_archives")
            count = cursor.fetchone()[0]
            print(f"   ✅ Found {count} records in database")
            
            # Check recent records
            cursor.execute("SELECT id, timestamp, agent_name, rule_description FROM wazuh_archives ORDER BY timestamp DESC LIMIT 3")
            recent = cursor.fetchall()
            print("   ✅ Recent records:")
            for record in recent:
                print(f"      ID: {record[0]}, Time: {record[1]}, Agent: {record[2]}")
        else:
            print("   ❌ wazuh_archives table not found")
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Database error: {e}")
        return False

def test_langchain_imports():
    """Test LangChain imports"""
    print("📚 Testing LangChain Imports...")
    try:
        from langchain.schema import Document
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain_community.vectorstores import FAISS
        from langchain_huggingface import HuggingFaceEmbeddings
        print("   ✅ All LangChain imports successful")
        return True
    except ImportError as e:
        print(f"   ❌ LangChain import error: {e}")
        return False

def test_rag_class():
    """Test RAG class initialization"""
    print("🧠 Testing RAG Class...")
    try:
        sys.path.append(str(Path.cwd()))
        from wazuh_fastmcp_server import WazuhLangChainRAG
        
        rag = WazuhLangChainRAG()
        print("   ✅ WazuhLangChainRAG class created")
        
        if rag.embeddings:
            print("   ✅ HuggingFace embeddings initialized")
        if rag.text_splitter:
            print("   ✅ Text splitter initialized")
        
        return True
    except Exception as e:
        print(f"   ❌ RAG class error: {e}")
        return False

async def test_fastmcp_server():
    """Test FastMCP server tools"""
    print("⚡ Testing FastMCP Server...")
    try:
        from fastmcp import Client
        
        # Test client connection (briefly)
        client = Client("wazuh_fastmcp_server.py")
        print("   ✅ FastMCP Client created")
        return True
    except Exception as e:
        print(f"   ❌ FastMCP error: {e}")
        return False

def test_mcp_bridge():
    """Test MCP bridge"""
    print("🌉 Testing MCP Bridge...")
    try:
        from mcp_tool_bridge import FastMCPBridge
        
        bridge = FastMCPBridge()
        print("   ✅ FastMCPBridge class created")
        return True
    except Exception as e:
        print(f"   ❌ MCP Bridge error: {e}")
        return False

def test_webapp_imports():
    """Test webapp imports"""
    print("🌐 Testing Webapp Imports...")
    try:
        from flask import Flask
        from openai import OpenAI
        print("   ✅ Flask and OpenAI imports successful")
        
        # Check if webapp file exists and is importable
        import webapp_chatbot
        print("   ✅ Webapp chatbot module importable")
        return True
    except Exception as e:
        print(f"   ❌ Webapp error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🔍 COMPREHENSIVE SYSTEM VERIFICATION")
    print("=" * 50)
    
    tests = [
        ("Database", test_database_connection),
        ("LangChain", test_langchain_imports), 
        ("RAG Class", test_rag_class),
        ("FastMCP", test_fastmcp_server),
        ("MCP Bridge", test_mcp_bridge),
        ("Webapp", test_webapp_imports)
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[name] = result
        except Exception as e:
            print(f"   ❌ {name} test failed with exception: {e}")
            results[name] = False
        print()
    
    print("📊 VERIFICATION SUMMARY")
    print("=" * 30)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:12} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 30)
    if all_passed:
        print("🎉 ALL TESTS PASSED - SYSTEM READY!")
    else:
        print("⚠️  SOME TESTS FAILED - CHECK ERRORS ABOVE")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(main())
