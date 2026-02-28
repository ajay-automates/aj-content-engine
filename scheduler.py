"""Campaign Scheduler — APScheduler cron for automated campaigns."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from crew import ContentEngineCrew
import logging

logger = logging.getLogger(__name__)

class CampaignScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.engine = ContentEngineCrew()
        self.jobs = []

    def add_daily(self, topic, hour=9, minute=0):
        jid = f"daily_{topic[:20].replace(' ', '_')}"
        self.scheduler.add_job(self._run, trigger=CronTrigger(hour=hour, minute=minute), args=[topic], id=jid, replace_existing=True)
        self.jobs.append({"topic": topic, "schedule": f"daily {hour}:{minute:02d}", "id": jid})

    def add_weekly(self, topic, day="mon", hour=9, minute=0):
        jid = f"weekly_{topic[:20].replace(' ', '_')}"
        self.scheduler.add_job(self._run, trigger=CronTrigger(day_of_week=day, hour=hour, minute=minute), args=[topic], id=jid, replace_existing=True)
        self.jobs.append({"topic": topic, "schedule": f"weekly {day} {hour}:{minute:02d}", "id": jid})

    def _run(self, topic):
        try:
            logger.info(f"Running: {topic}")
            return self.engine.run_content_pipeline(topic, publish=True)
        except Exception as e:
            logger.error(f"Failed: {topic} - {e}")

    def start(self): self.scheduler.start()
    def stop(self): self.scheduler.shutdown()
    def list_jobs(self): return self.jobs
