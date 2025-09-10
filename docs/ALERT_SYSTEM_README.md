# 🚨 Telegram Realtime Alert System

## Overview
Sistem alert realtime untuk monitoring critical security events dari Wazuh SIEM melalui Telegram bot. System ini akan mengirim notifikasi instant ketika terjadi event dengan rule level 7 ke atas (High/Critical severity).

## 🎯 Features

### ✅ Realtime Monitoring
- Monitoring rule level ≥ 7 (High severity)
- Monitoring rule level ≥ 8 (Critical severity)  
- Check interval: 30 seconds
- Auto-start/stop based on subscribers

### ✅ Smart Notifications
- Group alerts by severity level
- Show max 3 critical + 2 high events per alert
- Include agent name, rule ID, and description
- Timestamp dan action recommendations

### ✅ Subscriber Management
- Multiple users dapat subscribe
- Individual enable/disable per user
- Auto-cleanup untuk blocked users
- Status tracking per subscriber

## 📱 Commands

### Alert Management
```
/enable_alerts   - Enable realtime alerts
/disable_alerts  - Disable realtime alerts  
/alert_status    - Check alert system status
```

### Via Inline Keyboard
- 🚨 **Enable Alerts** button pada main menu
- 🔕 **Disable Alerts** button pada main menu

## 🔧 Technical Implementation

### Database Query
```sql
SELECT * FROM wazuh_archives 
WHERE rule_level >= 7 
AND timestamp > last_check_time 
ORDER BY timestamp DESC 
LIMIT 50
```

### Alert Monitoring Loop
```python
def alert_monitoring_loop(self):
    while self.alert_running:
        new_alerts = self.check_for_critical_events()
        if new_alerts:
            asyncio.create_task(self.send_alerts_to_subscribers(new_alerts))
        time.sleep(30)  # 30 second interval
```

### Alert Message Format
```
🚨 SECURITY ALERT 🚨
⏰ Time: DD/MM/YYYY HH:MM:SS

💥 CRITICAL Events: X
• Level 8 - Description...
  Agent: AgentName | Rule: 12345

⚠️ HIGH Events: X  
• Level 7 - Description...
  Agent: AgentName | Rule: 12345

🔍 Action Required:
• Review events dalam dashboard Wazuh
• Investigasi potential threats
• Update security measures jika diperlukan
```

## 🚀 Setup Instructions

### 1. Start Telegram Bot
```bash
cd /path/to/LMS-MCP
python telegram_security_bot.py
```

### 2. Enable Alerts
- Send `/start` to bot
- Click "🚨 Enable Alerts" button
- Or use `/enable_alerts` command

### 3. Verify Status
```
/alert_status
```

### 4. Test Alert System
```bash
python test_alert_system.py
```

## 📊 Alert Criteria

### Critical Events (Level 8+)
- Malware detection
- System compromise
- Data breach indicators
- Multiple failed authentication attempts

### High Events (Level 7)
- Web attacks (SQL injection, XSS)
- Firewall violations
- Suspicious network activity
- Configuration changes

## 🔍 Monitoring Dashboard

### System Status Information
- Alert monitoring: Active/Stopped
- Total subscribers: Number
- Last check time: Timestamp
- Database connection: Status

### User Status
- Subscription status: Subscribed/Not Subscribed
- Personal alert history
- Individual enable/disable control

## ⚙️ Configuration

### Alert Settings
- `rule_level >= 7`: Alert threshold
- `30 seconds`: Check interval
- `50 events`: Max events per check
- Auto-cleanup blocked users

### Database Configuration
```python
DATABASE_CONFIG = {
    'wazuh_db': 'wazuh_archives.db',
    'chat_db': 'chat_history.db'
}
```

## 🧪 Testing

### Create Test Events
```bash
python test_alert_system.py
```

### Test Scenarios
1. **Critical Event Test**: Create rule level 8+ events
2. **High Event Test**: Create rule level 7 events  
3. **Mixed Severity Test**: Create multiple severity levels
4. **Volume Test**: Create 10+ events at once

### Expected Results
- Alert notification within 30 seconds
- Proper event grouping by severity
- Action recommendations included
- Subscriber count tracking

## 🔧 Troubleshooting

### Common Issues

**1. No Alerts Received**
- Check `/alert_status` - verify subscription
- Verify bot is running
- Check database connection
- Look for errors in bot logs

**2. Alert Monitoring Not Starting**
- Check alert subscribers count
- Verify database file exists
- Check for permission issues

**3. Database Connection Errors**
- Verify `wazuh_archives.db` exists
- Check file permissions
- Ensure no file locks

### Debug Commands
```bash
# Check database events
sqlite3 wazuh_archives.db "SELECT COUNT(*) FROM wazuh_archives WHERE rule_level >= 7;"

# Check bot logs
tail -f wazuh_realtime.log

# Test database connection
python -c "import sqlite3; conn = sqlite3.connect('wazuh_archives.db'); print('DB OK')"
```

## 📈 Performance

### Resource Usage
- Memory: ~50MB for alert monitoring
- CPU: Minimal (30-second intervals)
- Network: Only when sending alerts
- Database: Read-only queries

### Scalability
- Support unlimited subscribers
- Efficient database indexing
- Async alert delivery
- Thread-safe operations

## 🛡️ Security Considerations

### Data Protection
- No sensitive data in alert messages
- Truncated log entries (max 50 chars)
- User authorization required
- Secure database access

### Privacy
- Individual subscription management
- No cross-user data sharing
- Optional alert disable
- Auto-cleanup blocked users

## 🔮 Future Enhancements

### Planned Features
- Custom rule level thresholds per user
- Alert scheduling (silence during maintenance)
- Alert categories filtering
- Historical alert statistics
- Email alert integration
- Webhook notifications

### Advanced Configuration
- User-specific alert criteria
- Geo-location based alerts
- Integration with SOAR platforms
- Custom alert templates
- Multi-language support

---

## 📞 Support

Untuk bantuan teknis atau bug reports:
- Check bot logs: `wazuh_realtime.log`
- Run test script: `test_alert_system.py`
- Contact system administrator

**Version:** 1.0  
**Last Updated:** September 4, 2025
