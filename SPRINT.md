Project Roadmap: Sprint 1
(Foundations)
Sprint Goal: Establish a baseline data connection and receive the first automated sleep report.
Week 1: Data Ingestion & Setup
● Day 1: Setup new Instagram/Threads accounts. Take "Baseline" sleep screenshots.
● Day 2: Install Python 3.12, PydanticAI, and setup a Telegram Bot via BotFather.
● Day 3: Configure Cronometer and Garmin to sync with Google Health Connect.
● Day 4: Write a Python script to verify Health Connect data is readable (Calories, Caffeine,
Sleep Score).
● Day 5: Order Govee WiFi Thermometer; finalize Pydantic data models for "DailyRecord".
Week 2: The Logic & First Feedback
● Day 8: Integrate Govee API to pull room temperature into the daily record.
● Day 9: Draft the "Analysis Prompt"—instructing the AI to look for correlations between
Temp, Caffeine, and Sleep.
● Day 11: Connect the Telegram Bot to the script. Set a 10:00 AM trigger for the "Morning
Briefing."
● Day 13: Record first piece of content: "Day 1 of building my sleep agent."
● Day 14: Sprint Review: Evaluate if the AI's suggestions match your actual feelings of
tiredness.
Success Metrics for Sprint 1
● Agent successfully identifies "Late Caffeine" as a disruptor at least once.
● Data from 3 different sources (Garmin, Cronometer, Govee) merges into a single JSON
object.
● Telegram message is received daily without manual script execution.