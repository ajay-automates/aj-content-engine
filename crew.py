"""AJ Content Engine — Crew Orchestration. 6 agents: Research -> Write -> Repurpose -> Visual -> Publish -> Analytics"""
from crewai import Crew, Process
import time
from agents import (create_research_agent, create_writer_agent, create_repurposer_agent,
    create_visual_agent, create_publisher_agent, create_analytics_agent)
from tasks import (create_research_task, create_writer_task, create_repurposer_task,
    create_visual_task, create_publisher_task, create_analytics_task)

class ContentEngineCrew:
    """Orchestrates the 6-agent content production pipeline."""
    def __init__(self):
        self.research_agent = create_research_agent()
        self.writer_agent = create_writer_agent()
        self.repurposer_agent = create_repurposer_agent()
        self.visual_agent = create_visual_agent()
        self.publisher_agent = create_publisher_agent()
        self.analytics_agent = create_analytics_agent()

    def run_content_pipeline(self, topic, publish=False):
        """Full pipeline: Research -> Write -> Repurpose -> Visual -> (Publish)"""
        start = time.time()
        tasks_list = [
            create_research_task(self.research_agent, topic),
            create_writer_task(self.writer_agent, topic),
            create_repurposer_task(self.repurposer_agent, topic),
            create_visual_task(self.visual_agent, topic),
        ]
        agents_list = [self.research_agent, self.writer_agent, self.repurposer_agent, self.visual_agent]
        if publish:
            tasks_list.append(create_publisher_task(self.publisher_agent, topic))
            agents_list.append(self.publisher_agent)
        crew = Crew(agents=agents_list, tasks=tasks_list, process=Process.sequential, verbose=True)
        result = crew.kickoff()
        return {
            "topic": topic, "published": publish, "final_output": str(result),
            "task_outputs": [{"agent": t.agent.role if t.agent else "?", "output": str(t.output) if t.output else "N/A"} for t in tasks_list],
            "metrics": {"total_agents": len(agents_list), "total_tasks": len(tasks_list), "process": "sequential", "latency_seconds": round(time.time() - start, 2)},
        }

    def run_content_only(self, topic):
        """Research + Write + Repurpose (no visuals, no publishing)."""
        start = time.time()
        t1 = create_research_task(self.research_agent, topic)
        t2 = create_writer_task(self.writer_agent, topic)
        t3 = create_repurposer_task(self.repurposer_agent, topic)
        crew = Crew(agents=[self.research_agent, self.writer_agent, self.repurposer_agent], tasks=[t1, t2, t3], process=Process.sequential, verbose=True)
        result = crew.kickoff()
        return {
            "topic": topic, "content": str(result),
            "task_outputs": [{"agent": "Research", "output": str(t1.output) if t1.output else "N/A"},
                {"agent": "Writer", "output": str(t2.output) if t2.output else "N/A"},
                {"agent": "Repurposer", "output": str(t3.output) if t3.output else "N/A"}],
            "metrics": {"total_agents": 3, "total_tasks": 3, "latency_seconds": round(time.time() - start, 2)},
        }

    def run_research_only(self, topic):
        t = create_research_task(self.research_agent, topic)
        crew = Crew(agents=[self.research_agent], tasks=[t], process=Process.sequential, verbose=True)
        result = crew.kickoff()
        return {"topic": topic, "research": str(result)}

if __name__ == "__main__":
    import sys
    topic = " ".join(sys.argv[1:]) or "AI agents replacing traditional SaaS"
    print(f"\nAJ CONTENT ENGINE — Starting: {topic}\n")
    engine = ContentEngineCrew()
    result = engine.run_content_only(topic)
    print(result["content"])
