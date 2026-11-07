import asyncio
import uuid
from app.database import create_database_engine, create_session_factory
from app.services.hindsight_service import HindsightMemoryService
from app.services.ai_service import GroqAIService, create_groq_client
from app.services.investigation_service import InvestigationService
from app.config import Settings

async def main():
    settings = Settings.load()
    engine = create_database_engine(settings.database_url)
    factory = create_session_factory(engine)
    session = factory()
    
    hindsight_client = None # In real app it's loaded from settings
    # We need a real client for live check.
    # But for now let's see if it crashes on init.
    try:
        ai_client = create_groq_client(settings)
        ai_service = GroqAIService(ai_client)
        hindsight_service = HindsightMemoryService(None, settings.hindsight_bank_id)
        investigation_service = InvestigationService(session, hindsight_service, ai_service)
        print("Services initialized successfully")
    except Exception as e:
        print(f"Init failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(main())
