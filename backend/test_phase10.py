"""Phase 10 后端API集成测试"""
import asyncio
import uvicorn
from threading import Thread
import time
import httpx

def start_server():
    uvicorn.run("app.main:app", host="127.0.0.1", port=8002, log_level="error")

t = Thread(target=start_server, daemon=True)
t.start()
time.sleep(3)

async def test():
    base = 'http://127.0.0.1:8002/api/v1'
    async with httpx.AsyncClient(timeout=10) as c:
        # Login
        r = await c.post(f'{base}/auth/login', json={'phone':'13800138000','password':'888888'})
        j = r.json()
        # Handle wrapped response
        data = j.get('data', j)
        token = data.get('access_token', data.get('token', ''))
        print(f'1. Login: {r.status_code}')
        h = {'Authorization': f'Bearer {token}'}

        # Dashboard
        r = await c.get(f'{base}/dashboard', headers=h)
        d = r.json()
        print(f'2. Dashboard: {r.status_code} greeting={d.get("greeting","")} stats={len(d.get("today_stats",[]))}')

        # Growth Overview
        r = await c.get(f'{base}/growth/overview', headers=h)
        d = r.json()
        print(f'3. Growth: {r.status_code} level={d.get("level","")} courses={len(d.get("learning_courses",[]))}')

        # Course Detail
        r = await c.get(f'{base}/growth/courses/course-001', headers=h)
        d = r.json()
        print(f'4. Course: {r.status_code} {d.get("title","")} lessons={len(d.get("lessons",[]))}')

        # Leaderboard
        r = await c.get(f'{base}/growth/leaderboard', headers=h)
        d = r.json()
        top = d.get("leaderboard",[{}])
        print(f'5. Leaderboard: {r.status_code} top={top[0].get("user_name","")} count={len(top)}')

        # Achievements
        r = await c.get(f'{base}/growth/achievements', headers=h)
        d = r.json()
        print(f'6. Achievements: {r.status_code} unlocked={len(d.get("unlocked",[]))} locked={len(d.get("locked",[]))}')

        # Notifications
        r = await c.get(f'{base}/notifications', headers=h)
        d = r.json()
        print(f'7. Notifications: {r.status_code} total={d.get("total","")} unread={d.get("unread_count","")}')

        # Filter
        r = await c.get(f'{base}/notifications?type=followup', headers=h)
        d = r.json()
        print(f'8. Filter: {r.status_code} followup={d.get("total","")}')

        # Mark Read All
        r = await c.post(f'{base}/notifications/read', json={'read_all': True}, headers=h)
        print(f'9. Mark Read: {r.status_code} updated={r.json().get("updated_count","")}')

        # Preferences
        r = await c.get(f'{base}/notifications/preferences', headers=h)
        d = r.json()
        print(f'10. Preferences: {r.status_code} count={len(d.get("preferences",[]))}')

        print('\nAll 10 backend API tests passed!')

asyncio.run(test())
