import os
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_crew():
    """Create and return a crew with researcher and writer agents"""
    
    # Define agents
    researcher = Agent(
        role='Senior Research Analyst',
        goal='Conduct thorough research on {topic} and provide comprehensive insights',
        verbose=True,
        memory=True,
        backstory="""You are a senior research analyst with expertise in gathering 
        and analyzing information from various sources. You have a keen eye for detail 
        and can identify key trends, opportunities, and challenges in any given topic.""",
        max_iter=3,
        allow_delegation=False
    )
    
    writer = Agent(
        role='Content Writer',
        goal='Write a compelling and informative article about {topic}',
        verbose=True,
        memory=True,
        backstory="""You are an experienced content writer who specializes in 
        transforming complex research into engaging, easy-to-understand articles. 
        You have a talent for storytelling and making technical topics accessible 
        to a broad audience.""",
        max_iter=3,
        allow_delegation=False
    )
    
    # Define tasks
    research_task = Task(
        description="""
        Research the topic: {topic}
        
        Your research should include:
        1. Key concepts and definitions
        2. Current trends and developments
        3. Pros and cons
        4. Real-world applications or examples
        5. Future outlook
        
        Gather information from reliable sources and provide citations where possible.
        """,
        expected_output="""A detailed research report with:
        - Executive summary
        - Key findings (minimum 5 points)
        - Pros and cons analysis
        - Current trends
        - Future predictions
        - Sources and references""",
        agent=researcher,
        output_file="research_report.md"
    )
    
    write_task = Task(
        description="""
        Based on the research provided, write an engaging article about {topic}.
        
        The article should:
        1. Have a compelling headline
        2. Include an engaging introduction
        3. Cover the main points from the research
        4. Be well-structured with clear sections
        5. Include practical insights or takeaways
        6. Have a strong conclusion
        
        Target length: 500-800 words
        Format: Markdown
        Tone: Professional but accessible
        """,
        expected_output="""A well-structured article in markdown format with:
        - Compelling headline
        - Introduction (2-3 paragraphs)
        - Main body with clear sections
        - Practical insights or examples
        - Conclusion with key takeaways
        - Word count between 500-800 words""",
        agent=writer,
        context=[research_task],
        output_file="final_article.md"
    )
    
    # Create crew
    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, write_task],
        process=Process.sequential,
        verbose=True,
        memory=True,
        cache=True,
        max_rpm=10,
        share_crew=False
    )
    
    return crew

def kickoff_crew(inputs: dict):
    """Initialize crew and start the workflow"""
    try:
        crew = create_crew()
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

def get_crew_status():
    """Get current crew configuration"""
    return {
        "agents": ["Senior Research Analyst", "Content Writer"],
        "tasks": ["Research Task", "Writing Task"],
        "process": "Sequential",
        "status": "Ready"
    }