# cfonline

For Telegram Bot
```python
python maain.py
```

For API
```python
python -m uvicorn app:app --port 8000 --host 0.0.0.0
```
Output: http://54.225.0.46:8000/docs

#### Some thing to add if ip not work
Navigate to EC2.
Edit Security Group:
Select the instance's Security Group.
Go to the Inbound rules tab.
Add a new rule:
Type: Custom TCP and all traffic
Protocol: TCP
Port Range: 8000
Source: 0.0.0.0/0 (to allow all traffic) or a specific IP range for restricted access.

**Configure Windows Firewall on the EC2 Instance**

By default, Windows Firewall may block incoming traffic on port 8000.

Open Windows Firewall Settings:

Press Win + R, type firewall.cpl, and hit Enter.
Add an Inbound Rule:

Click Advanced Settings.
Go to Inbound Rules and click New Rule.
Select Port and click Next.
Choose TCP, specify port 8000, and click Next.
Allow the connection and click Next.
Choose when the rule applies (Domain, Private, Public) and click Next.
Give the rule a name like "FastAPI Port 8000" and click Finish.

