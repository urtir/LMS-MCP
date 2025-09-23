#!/usr/bin/env python3
"""
Test specific AI output format to identify the corrupted output source
"""

import sys
import asyncio
import traceback
from pathlib import Path
from datetime import datetime, timedelta

print("🔧 TESTING AI OUTPUT FORMAT")
print("=" * 50)

async def test_ai_output():
    try:
        # Add project paths
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(project_root / 'src'))
        sys.path.insert(0, str(project_root / 'src' / 'telegram'))
        
        from telegram_report_generator import SecurityReportGenerator
        
        print("✅ SecurityReportGenerator imported")
        
        generator = SecurityReportGenerator()
        await generator.initialize()
        print("✅ Generator initialized")
        
        # Test 3-day report specifically
        print("\n📈 Testing 3-day report generation...")
        try:
            three_day_report = await generator.generate_three_daily_report()
            
            if 'error' in three_day_report:
                print(f"❌ 3-day report error: {three_day_report['error']}")
            else:
                print("✅ 3-day report generated successfully!")
                
                # Check AI analysis format specifically
                ai_analysis = three_day_report.get('ai_analysis', {})
                ai_text = ai_analysis.get('ai_analysis', '')
                
                print(f"\n🤖 AI ANALYSIS CHECK:")
                print(f"   Length: {len(ai_text)} characters")
                print(f"   Has <think> tags: {'<think>' in ai_text}")
                print(f"   First 500 chars:")
                print("-" * 60)
                print(ai_text[:500])
                print("-" * 60)
                
                # Check priority actions
                priority_actions = ai_analysis.get('priority_actions', [])
                print(f"\n🚨 PRIORITY ACTIONS CHECK:")
                print(f"   Count: {len(priority_actions)}")
                for i, action in enumerate(priority_actions[:3], 1):
                    print(f"   {i}. {action}")
                
        except Exception as e:
            print(f"❌ 3-day report failed: {e}")
            traceback.print_exc()
        
        print("\n🎯 AI output format test completed!")
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_output())