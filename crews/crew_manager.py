import os
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

def create_crew_with_context(conversation_context: List[Dict] = None):
    """Create crew with conversation context"""
    
    context_prompt = ""
    if conversation_context:
        context_prompt = "\n\nPrevious conversation context:\n"
        for msg in conversation_context[-5:]:  # Use last 5 messages
            context_prompt += f"{msg['role']}: {msg['content'][:200]}...\n"
        context_prompt += "\nUse this context to provide more relevant and personalized responses.\n"
    
    researcher = Agent(
        role='Senior Research Analyst',
        goal='Conduct thorough research on {topic} considering previous conversation context',
        verbose=True,
        memory=True,
        backstory=f"""You are a senior research analyst with expertise in gathering 
        and analyzing information. You maintain conversation continuity and build upon 
        previous discussions.{context_prompt}""",
        max_iter=3,
        allow_delegation=False
    )
    
    writer = Agent(
        role='Content Writer',
        goal='Write compelling content about {topic} that builds on previous conversation',
        verbose=True,
        memory=True,
        backstory=f"""You are an experienced content writer who creates engaging content 
        while maintaining conversation continuity and referencing previous discussions 
        when relevant.{context_prompt}""",
        max_iter=3,
        allow_delegation=False
    )
    
    research_task = Task(
        description=f"""
        Research the topic: {{topic}}
        
        {context_prompt}
        
        Your research should include:
        1. Key concepts and definitions
        2. Current trends and developments  
        3. Connection to previous conversation topics (if any)
        4. Pros and cons
        5. Real-world applications
        """,
        expected_output="A detailed research report with conversation continuity",
        agent=researcher
    )
    
    write_task = Task(
        description=f"""
        Write an engaging article about {{topic}} that maintains conversation continuity.
        
        {context_prompt}
        
        Requirements:
        1. Reference previous conversation when relevant
        2. Build upon earlier discussions
        3. Provide new insights while connecting to past topics
        4. Maintain consistent tone and style
        """,
        expected_output="A well-structured article with conversation continuity",
        agent=writer,
        context=[research_task]
    )
    
    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, write_task],
        process=Process.sequential,
        verbose=True,
        memory=True,
        cache=True
    )
    
    return crew

def kickoff_crew_with_context(inputs: dict, conversation_context: List[Dict] = None):
    """Execute crew with conversation context"""
    try:
        crew = create_crew_with_context(conversation_context)
        result = crew.kickoff(inputs=inputs)
        
        return {
            "status": "success",
            "result": str(result),
            "message": "Crew execution completed successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Error during crew execution: {str(e)}"
        }

# Backward compatibility
def kickoff_crew(inputs: dict):
    return kickoff_crew_with_context(inputs, None)