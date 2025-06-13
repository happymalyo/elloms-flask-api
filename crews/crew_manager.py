import os
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv
from typing import List, Dict, Optional
from crewai_tools import DallETool

load_dotenv()


def create_crew_with_context(
    conversation_context: List[Dict] = None,
    topic: str = None,
    additional_context: Optional[str] = None,
    platform: Optional[str] = None,
):
    """Create crew with conversation context"""

    context_prompt = ""
    if conversation_context:
        context_prompt = "\n\nPrevious conversation context:\n"
        for msg in conversation_context[-5:]:  # Use last 5 messages
            context_prompt += f"{msg['role']}: {msg['content'][:200]}...\n"
        context_prompt += (
            "\nUse this context to provide more relevant and personalized responses.\n"
        )

    content_creator = Agent(
        role="Social Media Content Creator",
        goal="""Create engaging and professional social media posts 
        based on given topic in the same language as the provided 
        topic and context (e.g., if the topic is in French, the post must be in French).
        """,
        verbose=True,
        memory=True,
        backstory=f"""You're an experienced social media content creator with expertise in crafting 
        compelling posts for LinkedIn and Facebook. You understand the different tones 
        and styles appropriate for each platform and know how to maximize engagement 
        while maintaining professionalism. Your posts consistently achieve high 
        engagement rates and effectively communicate the intended message.""",
        max_iter=3,
        allow_delegation=False,
    )

    if platform:
        task_description = f"""
        Create an engaging social media post based on the provided topic.
        {f"Use the following topic: {topic}" if topic else "Follow the default content creation guidelines."}
        Target platform: {platform}
        {f"For post Tone : Use {additional_context}" if additional_context else "Follow the default content creation guidelines." }
        Generate one post tailored specifically for {platform}.
        Use a tone and style appropriate for {platform}.
        Include relevant hashtags and a call-to-action where appropriate.
        {context_prompt}
        """
        expected_output = f"A single formatted social media post for {platform}, with appropriate tone, style, and hashtags."
    else:
        task_description = f"""
        Create engaging social media posts based on the provided topic.
        {f"Use the following topic: {topic}" if topic else "Follow the default content creation guidelines."}
        {f"For post Tone : Use {additional_context}" if additional_context else "Follow the default content creation guidelines." }
        Generate two versions:
        1. A professional LinkedIn post that maintains business etiquette
        2. A more casual Facebook post that remains appropriate for business
        Format the output clearly with headers for each platform.
        Include relevant hashtags and call-to-actions where appropriate.
        {context_prompt}
        """
        expected_output = "Two formatted social media posts (LinkedIn and Facebook versions) based on the input topic, with appropriate tone, style, and hashtags for each platform."

    content_creator_task = Task(
        description=task_description,
        expected_output=expected_output,
        agent=content_creator,
        context=[],
    )

    crew = Crew(
        agents=[content_creator],
        tasks=[content_creator_task],
        process=Process.sequential,
        verbose=True,
        memory=True,
        cache=True,
    )

    return crew


def create_crew_for_image(
    topic: str = None,
    additional_context: Optional[str] = None,
    platform: Optional[str] = None,
):
    """Create crew to generate image"""

    image_generator = Agent(
        role="Social Media Image Generator",
        goal="Generate appropriate and engaging images tailored for the social media platform and topic.",
        verbose=True,
        memory=False,
        backstory="""You're a visual content expert with deep knowledge of social media trends. 
        You know how to create eye-catching, contextually appropriate images for different platforms. 
        You always tailor the visuals to match the tone and audience expectations for LinkedIn and Facebook.""",
        tools=[DallETool()],
        allow_delegation=False,
    )

    if platform == "LinkedIn":
        image_prompt = "A professional photo of a human or a group of professionals in a business setting"
    elif platform == "Facebook":
        # Use topic and additional_context if available
        image_prompt = f"Create an image that reflects the topic: '{topic}'"
        if additional_context:
            image_prompt += f" with the context: {additional_context}"
    else:
        image_prompt = f"A relevant and engaging image based on the topic: '{topic}'"

    image_task = Task(
        description=f"""Generate 2 relevant, medium-sized images for a {platform} post.
        Use this prompt:
        {image_prompt}
        Use realistic and engaging imagery that matches the platform's tone and audience.
        Return only the direct image links in a Python array, like:
        ["https://image1.com", "https://image2.com"]
        No additional text or explanation.""",
        expected_output="A Python array with two direct image URLs, like: ['link1', 'link2']",
        agent=image_generator,
    )

    crew = Crew(
        agents=[image_generator],
        tasks=[image_task],
        process=Process.sequential,
        verbose=True,
        memory=True,
        cache=True,
    )

    return crew


def kickoff_crew_with_context(inputs: dict, conversation_context: List[Dict] = None):
    """Execute crew with conversation context"""
    try:
        topic = inputs.get("topic")
        platform = inputs.get("platform")
        additional_context = inputs.get("additional_context")

        crew = create_crew_with_context(
            conversation_context, topic, additional_context, platform
        )
        result = crew.kickoff(inputs=inputs)

        return {
            "status": "success",
            "result": str(result),
            "message": "Crew execution completed successfully",
        }
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Error during crew execution: {str(e)}",
        }


def kickoff_crew_for_image(inputs: dict):
    """Execute crew for image"""
    try:
        topic = inputs.get("topic")
        platform = inputs.get("platform")
        additional_context = inputs.get("additional_context")

        image_crew = create_crew_for_image(topic, additional_context, platform)
        result = image_crew.kickoff(inputs=inputs)

        return result

    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Error during crew image execution: {str(e)}",
        }


# Backward compatibility
def kickoff_crew(inputs: dict):
    return kickoff_crew_with_context(inputs, None)
