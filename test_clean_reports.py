#!/usr/bin/env python3
"""
Final test untuk full report generation - dengan <think> tags dihapus
"""

import sys
import asyncio
import traceback
from pathlib import Path
from datetime import datetime, timedelta

print("🎯 FINAL TEST - CLEAN REPORT GENERATION")
print("=" * 50)

async def test_full_reports():
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
        
        # Test 3-day report (yang sebelumnya bermasalah)
        print("\n📈 Testing FULL 3-day report generation...")
        try:
            three_day_report = await generator.generate_three_daily_report()
            
            if 'error' in three_day_report:
                print(f"❌ 3-day report error: {three_day_report['error']}")
            else:
                print("✅ 3-day report generated successfully!")
                print(f"   Report type: {three_day_report.get('report_type')}")
                print(f"   Events found: {len(three_day_report.get('security_events', []))}")
                print(f"   Statistics: {three_day_report.get('statistics', {}).get('summary', {}).get('total_events', 0)} total events")
                
                # Check AI analysis
                ai_analysis = three_day_report.get('ai_analysis', {})
                ai_text = ai_analysis.get('ai_analysis', '')
                priority_actions = ai_analysis.get('priority_actions', [])
                
                print(f"   Has AI analysis: {'ai_analysis' in three_day_report}")
                print(f"   AI text length: {len(ai_text)} chars")
                print(f"   Has <think> tags: {'<think>' in ai_text}")
                print(f"   Priority actions count: {len(priority_actions)}")
                
                print(f"\n📋 PRIORITY ACTIONS PREVIEW:")
                for i, action in enumerate(priority_actions[:3], 1):
                    print(f"   {i}. {action[:100]}...")
                
                print(f"\n🤖 AI ANALYSIS PREVIEW (first 300 chars):")
                print("-" * 60)
                print(ai_text[:300])
                print("-" * 60)
                
        except Exception as e:
            print(f"❌ 3-day report failed: {e}")
            traceback.print_exc()
        
        print("\n🎉 CLEAN REPORT TESTS COMPLETED!")
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_reports())